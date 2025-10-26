import socket
from datetime import datetime
from variable import *
import subprocess
import json
import time
import psutil
import shutil
import GPUtil
_prev_net = psutil.net_io_counters()
_prev_net_time = time.time()
stats_item=None

def get_master_volume_waveout():
    p = subprocess.run(['vol.exe'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out_json = json.loads(p.stdout.strip())
    if out_json['mut'] == '1':
        out_json['vol'] = '-' + out_json['vol']
    try:
        return int(float(out_json['vol']))
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        return None

def fmt_speed_bounded(bps):
    if bps is None:
        return "-".rjust(W_NET)
    units = [("GB/s", 1024**3), ("MB/s", 1024**2), ("KB/s", 1024), ("B/s", 1)]
    for unit, threshold in units:
        if bps >= threshold:
            return f"{int(bps / threshold)}{unit}".rjust(W_NET)
    return f"{int(bps)}B/s".rjust(W_NET)

def get_network_data(prev_net, prev_net_time):
    now = time.time()
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
def get_layout():
    layout_result = subprocess.run(["python", "layout.py"], stdout=subprocess.PIPE, text=True)
    layout = layout_result.stdout.strip() if layout_result.returncode == 0 else ""
    return layout
        


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

def update_texts(canvas, w):
    global stats_items, prev_values

    # Инициализация текстовых элементов, если они не существуют
    if stats_items is None:
        keys = ["time", "cpu", "ram", "drive", "network", "volume", "layout", "gpu"]
        x_positions = [w - 682, w - 608, w - 520, w - 432, w - 272, w - 200, w - 145, w - 8]

        stats_items = {key: canvas.create_text(x, RECT_HEIGHT // 2, text="", anchor="e", fill="white", font=("Consolas", 11))
                       for key, x in zip(keys, x_positions)}

    # Проверка и обновление текста только для изменившихся значений
    # Текст для сети
    new_down_bps = down_bps
    new_up_bps = up_bps
    if new_down_bps != prev_values["network_down"] or new_up_bps != prev_values["network_up"]:
        new_down_text = fmt_speed_bounded(new_down_bps).ljust(W_NET)[:W_NET]
        new_up_text = fmt_speed_bounded(new_up_bps).ljust(W_NET)[:W_NET]
        new_network_text = f" ↓{new_down_text} ↑{new_up_text}"
        canvas.itemconfigure(stats_items["network"], text=new_network_text)
        prev_values["network_down"] = new_down_bps
        prev_values["network_up"] = new_up_bps

    # Текст для времени
    new_time_value = tim
    if new_time_value != prev_values["time"]:
        new_time_text = f" {new_time_value}".ljust(W_TIME)[:W_TIME]
        canvas.itemconfigure(stats_items["time"], text=new_time_text)
        prev_values["time"] = new_time_value

    # Текст для ЦП
    new_cpu_value = cpu
    if new_cpu_value != prev_values["cpu"]:
        new_cpu_text = f"CPU {new_cpu_value}%".ljust(W_CPU)[:W_CPU]
        canvas.itemconfigure(stats_items["cpu"], text=new_cpu_text)
        prev_values["cpu"] = new_cpu_value

    # Текст для ОЗУ
    new_ram_value = ram_free_gb
    if new_ram_value != prev_values["ram"]:
        new_ram_text = (f"RAM {new_ram_value} GB" if new_ram_value is not None else "RAM -").ljust(W_RAM)[:W_RAM]
        canvas.itemconfigure(stats_items["ram"], text=new_ram_text)
        prev_values["ram"] = new_ram_value

    # Текст для диска
    new_drive_value = c_free_gb
    if new_drive_value != prev_values["drive"]:
        new_drive_text = (f"C:\\ {new_drive_value} GB" if new_drive_value is not None else "C:\\ -").ljust(W_DRIVE)[:W_DRIVE]
        canvas.itemconfigure(stats_items["drive"], text=new_drive_text)
        prev_values["drive"] = new_drive_value

    # Текст для громкости
    new_volume_value = vol_pct
    if new_volume_value != prev_values["volume"]:
        new_volume_text = (f"VOL {new_volume_value}%" if new_volume_value is not None else "VOL -").ljust(W_VOL)[:W_VOL]
        canvas.itemconfigure(stats_items["volume"], text=new_volume_text)
        prev_values["volume"] = new_volume_value

    # Текст для макета
    new_layout_value = layout
    if new_layout_value != prev_values["layout"]:
        new_layout_text = (f" {new_layout_value.upper()} " if new_layout_value else "-").ljust(W_LAYOUT)[:W_LAYOUT]
        canvas.itemconfigure(stats_items["layout"], text=new_layout_text)
        prev_values["layout"] = new_layout_value

    # Текст для графического процессора
    new_gpu_value = gpu_pct
    new_gpu_temp = gpu_temp
    if new_gpu_value != prev_values["gpu"] or new_gpu_temp != prev_values["gpu_temp"]:
        new_gpu_text = (f"GPU {int(new_gpu_value)}% T {new_gpu_temp}°C" if new_gpu_value is not None else "GPU -").ljust(W_GPU + W_TEMP)[:(W_GPU + W_TEMP)]
        canvas.itemconfigure(stats_items["gpu"], text=new_gpu_text)
        prev_values["gpu"] = new_gpu_value
        prev_values["gpu_temp"] = new_gpu_temp
current_update = 0  
def reset_stats(canvas):
    global stats_items, prev_values
    
    # Если у нас есть stats_items, очищаем их
    if stats_items is not None:
        # Стираем текст с каждого элемента на канвасе
        for item_key in stats_items:
            canvas.itemconfigure(stats_items[item_key], text=" ")
            canvas.delete(stats_items[item_key])  # Удаление элемента с канваса, если это необходимо

    # Сбрасываем значения предыдущих статистик
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

    # Восстанавливаем stats_items в None, чтобы избежать несанкционированного доступа в дальнейшем
    stats_items = None

full_screen_prev = False
paused_for_fullscreen = False
fs=None
fool = False
def update_status(canvas, root, w):
    global stats_items, layout_time, time_time, volume_time, network_time 
    global cpu_time, ram_time, disk_time, gpu_time, tim, net, down_bps, up_bps 
    global cpu, ram_free_gb, c_free_gb, gpu_pct, gpu_temp, vol_pct, layout 
    global _prev_net, _prev_net_time, current_update, prev_values, fool
    global full_screen_prev, paused_for_fullscreen, fs
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect(('localhost', 65433))
        try:
            # Получаем данные
            fs = int(client_socket.recv(4).decode('utf-8', errors='replace'))
                # break

        except Exception as e:
            print(f"US An error occurred: {e}")
            # break
    if fs==1 and not full_screen_prev:
        full_screen_prev = True
        paused_for_fullscreen = True
        if stats_items:
            for k, item in list(stats_items.items()):
                try:
                    canvas.itemconfigure(item, state='hidden')
                except Exception:
                    try:
                        canvas.delete(item)
                        stats_items.pop(k, None)
                    except Exception:
                        pass
        root.after(100, lambda: update_status(canvas, root, w))
        return

    if fs==0 and full_screen_prev:
        full_screen_prev = False
        paused_for_fullscreen = False
        if stats_items:
            for item in list(stats_items.values()):
                try:
                    canvas.itemconfigure(item, state='normal')
                except Exception:
                    pass
        now_t = time.time()
        time_time = now_t
        volume_time = now_t
        network_time = now_t
        cpu_time = now_t
        ram_time = now_t
        disk_time = now_t
        gpu_time = now_t
        layout_time = now_t
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
        current_update = 0

    if paused_for_fullscreen:
        root.after(100, lambda: update_status(canvas, root, w))
        return

    if fool == False:
        fool = True
        time_time = time.time()
        volume_time = time.time()
        network_time = time.time()
        cpu_time = time.time()
        ram_time = time.time()
        disk_time = time.time()
        gpu_time = time.time()
        layout_time = time.time()

        tim = datetime.now().strftime("%H:%M")
        net, down_bps, up_bps, now = get_network_data(_prev_net, _prev_net_time)
        _prev_net, _prev_net_time = net, now
        cpu = get_cpu_usage()
        ram_free_gb = get_ram_free()
        c_free_gb = get_disk_free()
        gpu_pct, gpu_temp = get_gpu_usage_and_temp()
        vol_pct = get_master_volume_waveout()
        layout = get_layout()

    t = time.time()

    if current_update == 0 or t - layout_time > UPDATE_LAYOUT_S:
        layout = get_layout()
        layout_time = t
    elif current_update == 1 and t - time_time > UPDATE_TIME_S:
        tim = datetime.now().strftime("%H:%M")
        time_time = t
    elif current_update == 2 and t - network_time > UPDATE_NETWORK_S:
        net, down_bps, up_bps, now = get_network_data(_prev_net, _prev_net_time)
        _prev_net, _prev_net_time = net, now
        network_time = t
    elif current_update == 3 or t - cpu_time > UPDATE_CPU_S:
        cpu = get_cpu_usage()
        cpu_time = t
    elif current_update == 4 and t - ram_time > UPDATE_RAM_S:
        ram_free_gb = get_ram_free()
        ram_time = t
    elif current_update == 5 and t - disk_time > UPDATE_DISK_S:
        c_free_gb = get_disk_free()
    elif current_update == 6 and t - gpu_time > UPDATE_GPU_S:
        gpu_pct, gpu_temp = get_gpu_usage_and_temp()
        gpu_time = t
    elif current_update == 7 or t - volume_time > UPDATE_VOLUME_S:
        vol_pct = get_master_volume_waveout()
        volume_time = t

    update_texts(canvas, w)

    current_update = (current_update + 1) % 8
    root.after(100, lambda: update_status(canvas, root, w))
