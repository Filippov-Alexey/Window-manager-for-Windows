from numba import prange
from variable import *
import socket
import json


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

def subtract_segment(seg, cover):
    x1,y1,x2,y2 = seg
    cl,ct,cr,cb = cover
    if x1 == x2:
        x = x1
        if not (cl <= x <= cr):
            return [seg]
        a1, a2 = min(y1,y2), max(y1,y2)
        if ct <= a1 and cb >= a2:
            return []
        if cb <= a1 or ct >= a2:
            return [seg]
        parts = []
        if ct > a1:
            parts.append((x, a1, x, min(ct, a2)))
        if cb < a2:
            parts.append((x, max(cb, a1), x, a2))
        return parts
    y = y1
    if not (ct <= y <= cb):
        return [seg]
    a1, a2 = min(x1,x2), max(x1,x2)
    if cl <= a1 and cr >= a2:
        return []
    if cr <= a1 or cl >= a2:
        return [seg]
    parts = []
    if cl > a1:
        parts.append((a1, y, min(cl, a2), y))
    if cr < a2:
        parts.append((max(cr, a1), y, a2, y))
    return parts

def visible_border_segments(rect, higher_rects):
    l, t, r, b = rect
    segs = [(l, t, r, t), (l, b, r, b), (l, t, l, b), (r, t, r, b)]

    for cover in higher_rects:
        new_segs = [seg for s in segs for seg in subtract_segment(s, cover)]
        segs = new_segs
        if not segs:
            break
            
    return segs

def draw_gradient_line(canvas, x1, y1, x2, y2, color_start, color_end, line_width):
    steps = 10  
    r1, g1, b1 = hex_to_rgb(color_start)
    r2, g2, b2 = hex_to_rgb(color_end)

    for i in range(steps):
        ratio = i / (steps - 1)
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        color = rgb_to_hex((r, g, b))  
        intermediate_x = int(x1 + (x2 - x1) * (i / steps))
        intermediate_y = int(y1 + (y2 - y1) * (i / steps))
        next_x = int(x1 + (x2 - x1) * ((i + 1) / steps))
        next_y = int(y1 + (y2 - y1) * ((i + 1) / steps))
        tags = f"win_{x1}_{y1}_{x2}_{y2}"
        item_id=canvas.create_line(intermediate_x, intermediate_y, next_x, next_y,
                        fill=color, width=line_width, tags=tags)
        canvas.addtag_withtag("icon", item_id)  # Добавляем тег "icon" для управления

def update_grap(canvas, root):
    global points
    points = points or []  # Например, если points не инициализирован
    active_points = []
    
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('localhost', 65432))
        
        # Получаем данные
        data = client_socket.recv(2048)
        client_socket.close()
        if not data:  # проверяем, что данные не пустые
            print("No data received from server.")
            # return
        else:
            
            open_windows = data.decode('utf-8')
            
            if open_windows:  # проверяем, что строка не пустая
                tit = json.loads(open_windows)

                scale_left = scale_top = scale_right = scale_bottom = 0
                rects = [w[3] for w in tit] if tit else []
                
                for i in prange(len(rects) - 1, -1, -1):
                    normalized_path = os.path.normpath(tit[i][2])
                    if normalized_path in win_rect:
                        scale_left, scale_top, scale_right, scale_bottom = win_rect[normalized_path]
                        
                    rect = rects[i]
                    left, top, right, bottom = rect

                    new_left = left + (right - left) * (1 - scale_left) + 1
                    new_top = top + (bottom - top) * (1 - scale_top)
                    new_right = right - (right - left) * (1 - scale_right) + 1
                    new_bottom = bottom - (bottom - top) * (1 - scale_bottom)

                    higher = rects[:i]
                    segs = visible_border_segments((new_left, new_top, new_right, new_bottom), higher)

                    for s in segs:
                        x1, y1, x2, y2 = s
                        active_points.append((x1, y1, x2, y2))
                        
                        if (x1, y1, x2, y2) not in points:  
                            points.append((x1, y1, x2, y2))

                            if x1 == x2:  
                                draw_gradient_line(canvas, x1, y1, x2, y2, '#d80303', '#0a0094', line_width=5)
                            else: 
                                color = '#d80303' if y1 == new_top else '#0a0094'
                                draw_gradient_line(canvas, x1, y1, x2, y2, color, color, line_width=5)                

                a = list(set(points) - set(active_points))
                remove = []
                for item in points:
                    if item in a:
                        x1, y1, x2, y2 = item
                        tag = f"win_{x1}_{y1}_{x2}_{y2}"
                        canvas.delete(tag)
                        remove.append(item)

                points = [item for item in points if item not in remove]
        
    except (socket.error, json.JSONDecodeError) as e:
        print(f"Socket/JSON Error: {e}")
        
    except Exception as e:
        print(f"UG An error occurred: 0{e}")
    
    finally:
        if client_socket:
            client_socket.close()  
    root.after(UPDATE_GRAPMS, lambda: update_grap(canvas,root))
