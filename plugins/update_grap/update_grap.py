from numba import prange
from variable import *
from plugins.update_grap.variable import *
import os
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

    for i in prange(steps):
        ratio = i / (steps - 1)
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        color = rgb_to_hex((r, g, b))  
        intermediate_x = int(x1 + (x2 - x1) * (i / steps))
        intermediate_y = int(y1 + (y2 - y1) * (i / steps))
        next_x = int(x1 + (x2 - x1) * ((i + 1) / steps))
        next_y = int(y1 + (y2 - y1) * ((i + 1) / steps))
        tags = ["icon",f"win_{x1}_{y1}_{x2}_{y2}"]
        canvas.create_line(intermediate_x, intermediate_y, next_x, next_y,
                        fill=color, width=line_width, tags=tags)

_itemconfig = None
title_id = None

def update_title(canvas, tit, RECT_HEIGHT):
    global active_title, index, title_id, full_string, _itemconfig
    # log.info(tit)
    
    raw_text = tit[0]['title']
    display_text = None
    
    if _itemconfig is None:
        _itemconfig = canvas.itemconfigure

    # 1. Логика бегущей строки
    if rec:
        if active_title != raw_text:
            active_title = raw_text
            index = 0
            # Подготовка строки: отступы + текст
            clean_text = raw_text
            base_string = (" " * visible_length) + clean_text + "   "
            full_string = base_string * 2 

        s_len = len(full_string) // 2
        pos = index % s_len
        display_text = full_string[pos : pos + visible_length]
        index += 1
    else:
        # 2. Обычный статический режим
        if active_title != raw_text:
            active_title = raw_text
            display_text = (raw_text[:visible_length-3] + "...") if len(raw_text) > visible_length else raw_text

    # 3. Отрисовка
    if title_id is None:
        title_id = canvas.create_text(
            1000, RECT_HEIGHT // 2, 
            text=display_text if display_text else "", 
            anchor="e", 
            fill="white", 
            font=("Consolas", 11), 
            tags="icon"
        )
    elif display_text is not None:
        _itemconfig(title_id, text=display_text)  

ac=[]
d=None
tit=None
aw=None
points=[]
d1=None
import queue

from manager import win_manager  

class update_grap:
    def __init__(self, canvas, root, RECT_HEIGHT, w):
        self.canvas = canvas
        self.root = root
        self.RECT_HEIGHT = RECT_HEIGHT
        self.w = w
        self.data_queue = queue.Queue(maxsize=1) 
        self.current_raw_data = None  
        self.drawn_segments = set() 
        
        # 1. Сначала подписываемся на менеджер (получаем уже готовый список)
        win_manager.subscribe(self.on_window_update)

        # 2. Если данные в кэше уже есть — обрабатываем сразу при старте
        if win_manager.last_data:
            self.current_raw_data = win_manager.last_data
            self.graph_logic(win_manager.last_data)

        # 3. Запускаем цикл проверки очереди
        self.run()

    def on_window_update(self, data):
        """Метод вызывается менеджером при получении новых данных"""
        try:
            # Фильтруем дубликаты сразу, чтобы не нагружать очередь
            if data != self.current_raw_data:
                if self.data_queue.full():
                    self.data_queue.get_nowait()
                self.data_queue.put_nowait(data)
        except Exception as e:
            log.error(f"Grap Queue Error: {e}")

    def run(self):
        global points, tit
        
        new_data = None
        # Берем только самое свежее состояние из очереди
        while not self.data_queue.empty():
            new_data = self.data_queue.get_nowait()
            
        try:
            if new_data:
                self.current_raw_data = new_data
                self.graph_logic(new_data)
                
            if tit is not None:
                update_title(self.canvas, tit, self.RECT_HEIGHT)
        except Exception as e:
            log.error(f"Grap Run Error: {e}")    
            
        self.root.after(UPDATE_GRAPMS, self.run)

    def graph_logic(self, data_list):
        global tit, rects
        
        tit = data_list
        
        rects = [w['rect'] for w in tit] if tit else []
        # log.info(rects)
        new_active_segments = set() 
        for i in range(len(rects) - 1, -1, -1):
            normalized_path = os.path.normpath(tit[i]['path'])
            scale_left = scale_top = scale_right = scale_bottom = 0
            if normalized_path in win_rect:
                scale_left, scale_top, scale_right, scale_bottom = win_rect[normalized_path]
                
            rect = rects[i]
            left, top, right, bottom = rect

            coords = (
                left + (right - left) + scale_left,
                top + (bottom - top) + scale_top,
                right - (right - left) - scale_right,
                bottom - (bottom - top) - scale_bottom
            )

            higher = rects[:i]
            segs = visible_border_segments(coords, higher)
            
            for s in segs:
                new_active_segments.add(tuple(s))

        to_delete = self.drawn_segments - new_active_segments
        for s in to_delete:
            tag = f"win_{s[0]}_{s[1]}_{s[2]}_{s[3]}"
            self.canvas.delete(tag)
        
        to_add = new_active_segments - self.drawn_segments
        for s in to_add:
            x1, y1, x2, y2 = s
            
            if orientation:
                is_gradient = (x1 == x2)
                color_start = colorUP if (is_gradient or y1 == coords[1]) else colorDOWN
                color_end = colorDOWN if (is_gradient or y1 != coords[1]) else colorUP
            else:
                is_gradient = (y1 == y2)
                color_start = colorUP if (is_gradient or x1 == coords[0]) else colorDOWN
                color_end = colorDOWN if (is_gradient or x1 != coords[0]) else colorUP

            draw_gradient_line(self.canvas, x1, y1, x2, y2, color_start, color_end, line_width=5)

        self.drawn_segments = new_active_segments