from socket_client import BaseSocketClient
from plugins.update_status.variable import *
from variable import *
import subprocess
import json
import time
import threading
import logger
log=logger.setup_logging()

layout=''
_stats_cache=stats_cache
_last_update = {k: 0 for k in _stats_cache}

def generic_listener(key_map, cmd):
    global _stats_cache, _last_update
    while True:
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1)
            for line in iter(proc.stdout.readline, ''):
                try:
                    data = json.loads(line.strip())
                    now = time.time()
                    
                    if now - _last_update["tim"] >= UPDATE_CFG["tim"]:
                        _stats_cache['tim'] = time.strftime(time_format)
                        _last_update["tim"] = now

                    if "vol" in data:
                        if now - _last_update["vol_pct"] >= UPDATE_CFG["vol_pct"]:
                            mut_sign = '-' if data.get('mut') == '1' else ' '
                            vol_val = int(float(data.get('vol', 0)))
                            _stats_cache["vol_pct"] = f"{mut_sign}{vol_val}"
                            _last_update["vol_pct"] = now

                    for k, v in key_map.items():
                        if k in data and v in UPDATE_CFG:
                            if now - _last_update[v] >= UPDATE_CFG[v]:
                                _stats_cache[v] = data[k]
                                _last_update[v] = now
                                
                except (json.JSONDecodeError, ValueError):
                    continue
            proc.wait()
        except Exception:
            pass


for mapping, cmd in listeners:
    threading.Thread(target=generic_listener, args=(mapping, cmd), daemon=True).start()

_itemconfig=None
stats_items=None
def update_texts(canvas, w, RECT): 
    global stats_items, prev_values, _itemconfig, _stats_cache
    
    if _itemconfig is None: _itemconfig = canvas.itemconfigure
    
    if stats_items is None:
        stats_items = {
            k: canvas.create_text(w - off[0], off[1], text="NON", anchor="e", 
                                  fill="white", font=("Consolas", 11), tags='icon')
            for k, off in zip(keys, pos)
        }
        prev_values = {k: None for k in keys + ["desk","network_down", "network_up", "gpu_temp"]}

    idx = getattr(update_texts, '_idx', 0)
    key, data_key, fmt_str, width = CONFIG_TEMPLATE[idx]
    
    val = _stats_cache.get(data_key)
    if val != prev_values[key]:
        txt = fmt_str.replace("{}", str(val)) if val is not None else "-"
        t=f"{txt:<{width}}"[:width]
        _itemconfig(stats_items[key], text=t)
        prev_values[key] = val
    
    update_texts._idx = (idx + 1) % len(CONFIG_TEMPLATE)

    d, u = _stats_cache['down_bps'], _stats_cache['up_bps']
    if d != prev_values["network_down"] or u != prev_values["network_up"]:
        snet = f" ↓{d:>{W_NET}}\n ↑{u:>{W_NET}}" if orientation else f" ↓{d.ljust(W_NET)[:W_NET]} ↑{u.ljust(W_NET)[:W_NET]}"
        _itemconfig(stats_items["network"], text=snet)
        prev_values["network_down"], prev_values["network_up"] = d, u

    gp, gt = _stats_cache['gpu_pct'], _stats_cache['gpu_temp']
    if gp != prev_values["gpu"] or gt != prev_values["gpu_temp"]:
        gpu_s = f"GPU {gp}%\n T {gt}°C" if orientation else f"GPU {gp}% T {gt}°C"
        _itemconfig(stats_items["gpu"], text=f"{gpu_s:<{W_GPU+W_TEMP}}"[:W_GPU+W_TEMP])
        prev_values["gpu"], prev_values["gpu_temp"] = gp, gt

class update_status:

    def __init__(self, canvas, root, RECT, w):
        self.canvas = canvas
        self.root = root
        self.w = w
        self.RECT = RECT
        self.lay = False
        self.current_hkl = 0
        self.init_layouts_ui()
        
        # 🟢 Инициализируем клиенты
        self.key_client = BaseSocketClient(ports['get_key'], "Status-Key")
        self.space_client = BaseSocketClient(ports['get_space'], "Status-Space", is_json=False)

        # Запускаем потоки
        threading.Thread(target=self.run_keyboard_listener, daemon=True).start()
        threading.Thread(target=self.run_space_listener, daemon=True).start()

    def run_space_listener(self):
        self.space_client.run_loop(handler=self._update_desk_cache)

    def _update_desk_cache(self, data):
        _stats_cache['desk'] = data.decode('utf-8', errors='replace')

    def run_keyboard_listener(self):
        self.key_client.run_loop(handler=self.handle_keyboard_logic)

    def handle_keyboard_logic(self, data):
        global layout
        
        op = data.get('option', '')
        keyname = data.get('key_name')
        status = data.get('status')
        key = data.get('layout')
        
        if key:
            layout = key['Name'][:2].upper()
            _stats_cache["layout"] = layout

        if 'left_win+space' in op:
            if status == 'Down':
                self.current_hkl = get_next_layout_hkl(key['HKL'])[0]
                self.lay = True
                self.draw_layouts(self.current_hkl)

        elif self.lay and keyname == 'left_win':
            self.lay = False
            self.canvas.itemconfig('lay_all', state='hidden')
    def init_layouts_ui(self):
        """Вызовите этот метод один раз при инициализации класса"""
        self.lay_elements = {}
        l = len(layouts)
        x1, x2 = scr_w - menu_width - padding, scr_w - padding
        y1, y2 = scr_h - (l * row_height) - padding, scr_h - padding
        
        # Создаем подложку
        self.lay_bg = self.canvas.create_rectangle(x1, y1, x2, y2, fill=color_bg_menu, state='hidden', tags='lay_all')
        # Создаем рамку выделения
        self.lay_sel = self.canvas.create_rectangle(x1, 0, x2, 0, fill=color_seletc_menu, state='hidden', tags='lay_all')
        
        for i, (hkl_hex, full_name) in enumerate(layouts):
            display_text = full_name.split('(')[-1].split(')')[0] if '(' in full_name else full_name
            curr_y = y1 + 5 + (i * row_height)
            # Создаем текст
            txt_id = self.canvas.create_text(x1 + 10, curr_y, anchor='nw', text=display_text, 
                                             fill='white', font=('Arial', 10, 'bold'), state='hidden', tags='lay_all')
            self.lay_elements[hkl_hex] = (txt_id, curr_y)

    def draw_layouts(self, current_id):
        try:
            """Обновляет положение селектора и показывает меню"""
            self.canvas.itemconfig('lay_all', state='normal')
            if current_id in self.lay_elements:
                _, curr_y = self.lay_elements[current_id]
                # Перемещаем рамку выделения под текущий ID
                self.canvas.coords(self.lay_sel, scr_w - menu_width - padding, curr_y - 2, scr_w - padding, curr_y + 22)
        except Exception as e:
            log.error(e)


    def run(self):
        update_texts(self.canvas, self.w, self.RECT)
        self.root.after(UPDATE_STATUS_MS, lambda: self.run())
