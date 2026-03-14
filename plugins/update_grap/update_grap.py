
# from numba import prange
from variable import *
from plugins.update_grap.variable import *
import os
import zlib
import socket
import json
import pygetwindow as gw
import logger
log=logger.setup_logging()
title=''
active_title=''
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
        tags = [f"win_{x1}_{y1}_{x2}_{y2}","icon"]
        canvas.create_line(intermediate_x, intermediate_y, next_x, next_y,
                        fill=color, width=line_width, tags=tags)

index=-visible_length
full_string=''
def update_title(canvas, tit, RECT_HEIGHT):
    global active_title, index, title, full_string
    
    raw_text = " ".join(tit[0][1].split()) 
    
    if len(raw_text) <= visible_length:
        s = raw_text
    else:
        s = raw_text[:visible_length - 3]
        last_space = s.rfind(" ")
        if last_space != -1:
            s = s[:last_space]
        s += "..."

    if active_title != s:
        active_title = s
        index = 0

        preamble = ' ' * visible_length
        full_string = preamble + s + preamble

    pos = index % len(full_string)
    d = (full_string + full_string)[pos : pos + visible_length]

    while d.isspace():
        index += 1
        d = full_string[index % len(full_string):index % len(full_string) + visible_length]

    if not title:
        title = canvas.create_text(1000, RECT_HEIGHT // 2, text=d, 
                                  anchor="e", fill="white", font=("Consolas", 11), tags="icon")
    else:
        canvas.itemconfigure(title, text=d)
    index += 1



ac=[]
d=None
tit=None
aw=None
points=None
d1=None
class update_grap:
    def __init__(self, canvas, root, RECT_HEIGHT,w):
         self.canvas=canvas
         self.root=root
         self.RECT_HEIGHT=RECT_HEIGHT
         self.aw=None
    def graph(self):  
        global d,points,ac,tit, d1
        active_points = []
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:

            client_socket.connect(('localhost', ports['get_win']))
            m = client_socket.recv(4).decode('utf-8', errors='replace')
            data = client_socket.recv(int(m))
            
 
            if data != d1:
                d1=data
                d=zlib.decompress(data)
                open_windows = d.decode('utf-8')
                
                tit = json.loads(open_windows)

                scale_left = scale_top = scale_right = scale_bottom = 0
                rects = [w[3] for w in tit] if tit else []
                for i in range(len(rects) - 1, -1, -1):
                    normalized_path = os.path.normpath(tit[i][2])
                    if normalized_path in win_rect:
                        scale_left, scale_top, scale_right, scale_bottom = win_rect[normalized_path]
                        
                    rect = rects[i]
                    left, top, right, bottom = rect

                    new_left = left + (right - left) + scale_left
                    new_top = top + (bottom - top) + scale_top
                    new_right = right - (right - left) - scale_right
                    new_bottom = bottom - (bottom - top) - scale_bottom

                    higher = rects[:i]
                    segs = visible_border_segments((new_left, new_top, new_right, new_bottom), higher)

                    for s in segs:
                        x1, y1, x2, y2 = s
                        active_points.append((x1, y1, x2, y2))
                        
                        if (x1, y1, x2, y2) not in points:  
                            points.append((x1, y1, x2, y2))
                        if orientation:
                            is_gradient = (x1 == x2)
                            color_start = colorUP if (is_gradient or y1 == new_top) else colorDOWN
                            color_end = colorDOWN if (is_gradient or y1 != new_top) else colorUP
                        else:
                            is_gradient = (y1 == y2)
                            color_start = colorUP if (is_gradient or x1 == new_left) else colorDOWN
                            color_end = colorDOWN if (is_gradient or x1 != new_left) else colorUP

                        draw_gradient_line(self.canvas, x1, y1, x2, y2, color_start, color_end, line_width=5)

                a = list(set(points) - set(active_points))
                if ac!=a:
                    ac=a
                    remove = []
                    for item in points:
                        if item in a:
                            x1, y1, x2, y2 = item
                            tag = f"win_{x1}_{y1}_{x2}_{y2}"
                            self.canvas.delete(tag)
                            remove.append(item)

                    points = [item for item in points if item not in remove]

    def run(self):
        global points,aw
        points = points or []
        try:
            if not tit is None:
                update_title(self.canvas, tit, self.RECT_HEIGHT)
            acw=f'{gw.getActiveWindow()}'
            if acw!=aw:
                aw=acw
                self.graph()
            
        except Exception as e:
            log.error(f"UG An error occurred: 0{e}")
        
        self.root.after(UPDATE_GRAPMS, lambda: self.run())
