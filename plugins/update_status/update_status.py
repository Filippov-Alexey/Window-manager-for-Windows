import socket
from datetime import datetime
from plugins.update_status.variable import *
from variable import *
import subprocess
import json
import time
import psutil
import shutil
import GPUtil
import threading
import logger
log=logger.setup_logging()

_prev_net = psutil.net_io_counters()
_prev_net_time = time.time()
stats_item=None

def fmt_speed_bounded(bps):
    if bps is None:
        return "-".rjust(W_NET)
    units = [("GB/s", 1024**3), ("MB/s", 1024**2), ("KB/s", 1024), ("B/s", 1)]
    for unit, threshold in units:
        if bps >= threshold:
            return f"{int(bps / threshold)}{unit}".rjust(W_NET)
    return f"{int(bps)}B/s".rjust(W_NET)

def get_network_data(now, prev_net, prev_net_time):
    interval = max(1e-6, now - prev_net_time)
    net = psutil.net_io_counters()
    down_bps = int((net.bytes_recv - prev_net.bytes_recv) / interval)
    up_bps = int((net.bytes_sent - prev_net.bytes_sent) / interval) 
    return net, down_bps, up_bps, now

def get_cpu_usage():
    return int(psutil.cpu_percent(interval=None)) 

def get_ram_free():
    vm = psutil.virtual_memory()
    return int(vm.available / (1024**3)) 

def get_disk_free():
    try:
        du = shutil.disk_usage("C:\\")
        return int(du.free / (1024**3))  
    except Exception:
        return None

def get_gpu_usage_and_temp():
    gpu_pct = gpu_temp = None
    if GPUtil:
        gpus = GPUtil.getGPUs()
        if gpus:
            gpu_pct = int(gpus[0].load * 100.0)
            gpu_temp = gpus[0].temperature 
    return gpu_pct, gpu_temp

# def get_layout():
#     layout_result = subprocess.run(["python", "layout.py"], stdout=subprocess.PIPE, text=True)
#     layout = layout_result.stdout.strip() if layout_result.returncode == 0 else ""
#     return layout
def get_master_volume_waveout():
    try:
        raw_out = subprocess.check_output(['vol.exe'], text=True)
        data = json.loads(raw_out)
        
        vol_val = int(float(data['vol']))
        prefix = '-' if data.get('mut') == '1' else ' '
        
        return f"{prefix}{vol_val}"
    except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError, ValueError) as e:
        log.error(f"Ошибка получения громкости: {e}")
        return None
stats_items = None
prev_values = {
    "time": None,
    "cpu": None,
    "ram": None,
    "drive": None,
    "network_up": None,
    "network_down": None,
    "volume": None,
    "layout": None,
    "gpu": None
}
def update_texts(canvas, w, RECT):
    global stats_items, prev_values
    
    if stats_items is None:
        stats_items = {
            k: canvas.create_text(w - off[0], off[1], text="", anchor="e", 
                                  fill="white", font=("Consolas", 11))
            for k, off in zip(keys, pos)
        }
        prev_values = {k: None for k in keys + ["network_down", "network_up", "gpu_temp"]}

    g = globals()

    config = [
        ("layout", g.get('layout'), f" {str(g.get('layout'))} " if g.get('layout') else "-", W_LAYOUT),
        ("volume", g.get('vol_pct'), f"VOL{g.get('vol_pct')}%" if g.get('vol_pct') is not None else "VOL -", W_VOL),
        ("ram",    g.get('ram_free_gb'), f"RAM {g.get('ram_free_gb')} GB" if g.get('ram_free_gb') else "RAM -", W_RAM),
        ("drive",  g.get('c_free_gb'), f"C:\\ {g.get('c_free_gb')} GB" if g.get('c_free_gb') else "C:\\ -", W_DRIVE),
        ("time",   g.get('tim'),   f" {g.get('tim')}", W_TIME),
        ("cpu",    g.get('cpu'),   f"CPU {g.get('cpu')}%", W_CPU),
    ]

    for key, val, raw_text, width in config:
        if val != prev_values[key]:
            canvas.itemconfigure(stats_items[key], text=f"{raw_text:<{width}}"[:width])
            prev_values[key] = val
            break

    d, u = g.get('down_bps', 0), g.get('up_bps', 0)
    if d != prev_values["network_down"] or u != prev_values["network_up"]:
        d_txt = fmt_speed_bounded(d).ljust(W_NET)[:W_NET]
        u_txt = fmt_speed_bounded(u).ljust(W_NET)[:W_NET]
        if orientation:
            snet=f" ↓{d_txt}\n ↑{u_txt}"
        else:
            snet=f" ↓{d_txt} ↑{u_txt}"
            
        canvas.itemconfigure(stats_items["network"], text=snet)
        prev_values["network_down"], prev_values["network_up"] = d, u

    gp, gt = g.get('gpu_pct'), g.get('gpu_temp')
    if gp != prev_values["gpu"] or gt != prev_values["gpu_temp"]:
        if orientation:
            gpu=f"GPU {int(gp)}%\n T {int(gt)}°C"
        else:
            gpu=f"GPU {int(gp)}% T {int(gt)}°C"
        gpu_text = gpu if gp is not None else "GPU -"
        limit = W_GPU + W_TEMP
        canvas.itemconfigure(stats_items["gpu"], text=f"{gpu_text:<{limit}}"[:limit])
        prev_values["gpu"], prev_values["gpu_temp"] = gp, gt

current_update = 0  

full_screen_prev = False
paused_for_fullscreen = False
fs=None
fool = False
layout=''
timers = {
    "layout": 0, "time": 0, "network": 0, "cpu": 0,
    "ram": 0, "disk": 0, "gpu": 0, "volume": 0
}
class update_status:
    def __init__(self, canvas, root, RECT, w):
         self.canvas=canvas
         self.root=root
         self.w=w
         self.RECT=RECT
         self.lay= False
         self.current_hkl=0
         threading.Thread(target=self.listen_keyboard, daemon=True).start()

    def draw_layouts(self, current_id):
        self.canvas.delete('lay_item', 'lay')
        l = len(layouts)
        x1 = scr_w - menu_width - padding
        y1 = scr_h - (l * row_height) - padding
        x2 = scr_w - padding
        y2 = scr_h - padding

        self.canvas.create_rectangle(x1, y1, x2, y2, fill=color_bg_menu, tags='lay')

        current_y = y1 + 5
        
        for hkl_hex, full_name in layouts:
            display_text = full_name.split('(')[-1].split(')')[0] if '(' in full_name else full_name
            
            if hkl_hex == current_id:
                self.canvas.create_rectangle(x1, current_y - 2, x2, current_y + 22, 
                                             fill=color_seletc_menu, tags='lay_item')
            
            self.canvas.create_text(x1 + 10, current_y, anchor='nw', 
                                    text=display_text, fill='white', 
                                    font=('Arial', 10, 'bold'), tags='lay_item')
            
            current_y += row_height
    def listen_keyboard(self):
        global layout
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', ports['get_key']))
            while True:
                try:
                    m = s.recv(4).decode('utf-8', errors='replace')
                    buffer=s.recv(int(m)).decode('utf-8', errors='replace').strip()
                    data = json.loads(buffer)
                    op=data.get('option')
                    keyname=data.get('key_name')
                    key = data.get('layout')
                    status=data.get('status')
                    layout=key['Name'][:2].upper()
                    if 'left_win+space' in op:
                        if status == 'Down':
                            self.current_hkl = get_next_layout_hkl(key['ID'])[0]
                            
                            if not self.lay:
                                self.lay = True
                            
                            self.draw_layouts(self.current_hkl)

                    elif self.lay and keyname == 'left_win':
                        self.lay = False
                        self.canvas.delete('lay')
                        self.canvas.delete('lay_item')
                except Exception as e:
                    log.error(f'US-{e}')

    def update_status(self):
        global full_screen_prev, paused_for_fullscreen, current_update, _prev_net, _prev_net_time, tasks
        global stats_items, prev_values, net, down_bps, up_bps

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('localhost', ports['is_full_win']))
                fs = int(s.recv(4).decode('utf-8', errors='ignore'))
        except Exception as e:
            fs = 0 # Значение по умолчанию при ошибке

        if fs == 1:
            if not full_screen_prev:
                full_screen_prev, paused_for_fullscreen = True, True
                if stats_items:
                    for item in stats_items.values():
                        self.canvas.itemconfigure(item, state='hidden')
            self.root.after(100, lambda: self.run())
            # root.after(100, lambda: update_status(canvas, root, w))
            return

        elif fs == 0 and full_screen_prev:
            full_screen_prev, paused_for_fullscreen = False, False
            if stats_items:
                for item in stats_items.values():
                    self.canvas.itemconfigure(item, state='normal')
            
            now = time.time()
            for k in timers: timers[k] = now
            prev_values = {k: None for k in prev_values}
            current_update = 0
        elif fs==0:
            t = time.time()
            
            tasks = [
                # (0, UPDATE_LAYOUT_S, lambda: globals().update(layout=get_layout())),
                (1, UPDATE_TIME_S,   lambda: globals().update(tim=datetime.now().strftime("%H:%M"))),
                (2, UPDATE_NETWORK_S, lambda: update_net_data(t)), 
                (3, UPDATE_CPU_S,    lambda: globals().update(cpu=get_cpu_usage())),
                (4, UPDATE_RAM_S,    lambda: globals().update(ram_free_gb=get_ram_free())),
                (5, UPDATE_DISK_S,   lambda: globals().update(c_free_gb=get_disk_free())),
                (6, UPDATE_GPU_S,    lambda: globals().update(gpu_pct=get_gpu_usage_and_temp()[0], gpu_temp=get_gpu_usage_and_temp()[1])),
                (7, UPDATE_VOLUME_S, lambda: globals().update(vol_pct=get_master_volume_waveout()))
            ]

            def update_net_data(t):
                global net, down_bps, up_bps, _prev_net, _prev_net_time
                net, down_bps, up_bps, now_n = get_network_data(t, _prev_net, _prev_net_time)
                _prev_net, _prev_net_time = net, now_n
            for i in tasks:

                idx, interval, func = i
                timer_key = list(timers.keys())[idx] 
                if t - timers[timer_key] > interval:
                    func()
                    timers[timer_key] = t

            update_texts(self.canvas, self.w, self.RECT)

    def run(self):
        self.update_status()
        self.root.after(UPDATE_STATUS_MS, lambda: self.run())
if __name__=='__main__':
    from panel import main
    main()
 