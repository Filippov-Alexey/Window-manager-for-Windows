import socket
from plugins.update_status.variable import *
from variable import *
import subprocess
import json
import time
import threading
import logger
log=logger.setup_logging()

current_update = 0  

full_screen_prev = False
paused_for_fullscreen = False
fs=None
fool = False
layout=''

CONFIG_TEMPLATE = (
    ("layout", "layout",      " {} ",       W_LAYOUT),
    ("volume", "vol_pct",     "VOL{}%",    W_VOL),
    ("ram",    "ram_free_gb", "RAM {} GB",  W_RAM),
    ("drive",  "c_free_gb",   "C:\\ {}GB", W_DRIVE),
    ("time",   "tim",         " {}",        W_TIME),
    ("cpu",    "cpu",         "CPU {}%",    W_CPU),
)
# Глобальное хранилище актуальных данных
_stats_cache = {
    "vol_pct": " 0", "cpu": 0, "ram_free_gb": 0, "c_free_gb": 0,
    "down_bps": "0b", "up_bps": "0b", "gpu_pct": 0, "gpu_temp": 0,
    "tim": "00:00", "layout": ""
}

# Интервалы обновления
UPDATE_CFG = {
    "vol_pct": UPDATE_VOLUME_S,
    "cpu": UPDATE_CPU_S,
    "ram_free_gb": UPDATE_RAM_S,
    "c_free_gb": UPDATE_DISK_S,
    "tim": UPDATE_TIME_S,
    "layout": UPDATE_LAYOUT_S,
    "gpu_pct": UPDATE_GPU_S,
    "gpu_temp": UPDATE_GPU_S,
    "down_bps": UPDATE_NETWORK_S,
    "up_bps": UPDATE_NETWORK_S,
}

# Храним время последнего обновления для каждого ключа
_last_update = {k: 0 for k in _stats_cache}

def generic_listener(key_map, cmd):
    global _stats_cache, _last_update
    while True:
        try:
            # bufsize=1 и универсальные переносы строк для скорости
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, bufsize=1)
            for line in iter(proc.stdout.readline, ''):
                try:
                    data = json.loads(line.strip())
                    now = time.time()
                    
                    # Специальная обработка громкости
                    if "vol" in data:
                        if now - _last_update["vol_pct"] >= UPDATE_CFG["vol_pct"]:
                            mut_sign = '-' if data.get('mut') == '1' else ' '
                            vol_val = int(float(data.get('vol', 0)))
                            _stats_cache["vol_pct"] = f"{mut_sign}{vol_val}"
                            _last_update["vol_pct"] = now

                    # Обработка остальных ключей
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
        time.sleep(1)

timers = {
    "layout": 0, "time": 0, "network": 0, "cpu": 0,
    "ram": 0, "disk": 0, "gpu": 0, "volume": 0
}
listeners = [
    ({"vol": "vol_pct", "mut": "vol_mut"}, [tools['vol']]),
    ({"cpu_load_pct": "cpu"},              [tools['cpu']]),
    ({"free_gb": "ram_free_gb"},           [tools['ram'], "gb"]),
    ({"free_gb": "c_free_gb"},             [tools['disk'], "C", "gb"]),
    ({"gpu_load_pct": "gpu_pct", "gpu_temp_c": "gpu_temp"}, [tools['gpu']]),
    ({"rx": "down_bps", "tx": "up_bps"},   [tools['net'], "/a", "all", "/min", "kb"]),
]

for mapping, cmd in listeners:
    threading.Thread(target=generic_listener, args=(mapping, cmd), daemon=True).start()

_itemconfig=None
stats_items=None
def update_texts(canvas, w, RECT): 
    global stats_items, prev_values, _itemconfig, _stats_cache
    
    if _itemconfig is None: _itemconfig = canvas.itemconfigure
    
    if stats_items is None:
        stats_items = {
            k: canvas.create_text(w - off[0], off[1], text="", anchor="e", 
                                  fill="white", font=("Consolas", 11), tags='icon')
            for k, off in zip(keys, pos)
        }
        prev_values = {k: None for k in keys + ["network_down", "network_up", "gpu_temp"]}

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
         self.canvas=canvas
         self.root=root
         self.w=w
         self.RECT=RECT
         self.lay= False
         self.current_hkl=0
         self.init_layouts_ui()
         threading.Thread(target=self.listen_keyboard, daemon=True).start()

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

    def listen_keyboard(self):
        global layout
        # Не забудьте вызвать self.init_layouts_ui() перед запуском этого цикла
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', ports['get_key']))
            while True:
                try:
                    m=int.from_bytes(s.recv(4), 'big')
                    data=s.recv(m).decode('utf-8', errors='replace')
                    data = json.loads(data)
                    
                    op = data.get('option', '')
                    keyname = data.get('key_name')
                    status = data.get('status')
                    key = data.get('layout')
                    
                    if key:
                        layout = key['Name'][:2].upper()
                        _stats_cache["layout"]=layout

                    if 'left_win+space' in op:
                        if status == 'Down':
                            self.current_hkl = get_next_layout_hkl(key['HKL'])[0]
                            self.lay = True
                            self.draw_layouts(self.current_hkl)

                    elif self.lay and keyname == 'left_win':
                        self.lay = False
                        self.canvas.itemconfig('lay_all', state='hidden')
                        
                except Exception as e:
                    log.error(f'US-{e}')

    def run(self):
        _stats_cache['tim']=time.strftime("%H:%M")
        update_texts(self.canvas, self.w, self.RECT)
        # self.update_status()
        self.root.after(UPDATE_STATUS_MS, lambda: self.run())
