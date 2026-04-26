from variable import *
W_CPU   = 7 
W_RAM   = 9
W_DRIVE = 9
W_NET   = 5
W_VOL   = 7 
W_GPU   = 8 
W_TEMP  = 7 
W_LAYOUT= 5
W_TIME  = 6
W_DESKTOP=1
UPDATE_DESKTOP_S=0.1
UPDATE_TIME_S = 60
UPDATE_VOLUME_S = 1
UPDATE_NETWORK_S = 1
UPDATE_CPU_S = 1
UPDATE_LAYOUT_S = 0.1
UPDATE_RAM_S = 1
UPDATE_GPU_S = 1
UPDATE_DISK_S = 60
UPDATE_STATUS_MS = 500
orientation=False

CONFIG_TEMPLATE = (
    ("layout", "layout",      " {} ",       W_LAYOUT),
    ("volume", "vol_pct",     "VOL{}%",    W_VOL),
    ("ram",    "ram_free_gb", "RAM {} GB",  W_RAM),
    ("drive",  "c_free_gb",   "C:\\ {}GB", W_DRIVE),
    ("time",   "tim",         " {}",        W_TIME),
    ("cpu",    "cpu",         "CPU {}%",    W_CPU),
    ("desk",    "desk",         "{}",    W_DESKTOP),
)
# Глобальное хранилище актуальных данных
stats_cache = {
    "vol_pct": " 0", "cpu": 0, "ram_free_gb": 0, "c_free_gb": 0,
    "down_bps": "0b", "up_bps": "0b", "gpu_pct": 0, "gpu_temp": 0,
    "tim": "00:00", "layout": "EN", "desk": "1"
}

# Интервалы обновления
UPDATE_CFG = {
    "vol_pct": UPDATE_VOLUME_S,
    "cpu": UPDATE_CPU_S,
    "desk": UPDATE_DESKTOP_S,
    "ram_free_gb": UPDATE_RAM_S,
    "c_free_gb": UPDATE_DISK_S,
    "tim": UPDATE_TIME_S,
    "layout": UPDATE_LAYOUT_S,
    "gpu_pct": UPDATE_GPU_S,
    "gpu_temp": UPDATE_GPU_S,
    "down_bps": UPDATE_NETWORK_S,
    "up_bps": UPDATE_NETWORK_S,
}

keys = ["desk", "time", "cpu", "ram", "drive", "network", "volume", "layout", "gpu"]
if not orientation:
    y=RECT // 2
    pos = [(x, y) for x in [710,647, 575, 480, 392, 272, 200, 145, 8]]
else:
    x=RECT // 2
    pos = [(x, y) for y in [15,35,55,85,105,125,145,175,190]]

scr_w, scr_h = extension[0], extension[1]
        
menu_width = 200
row_height = 30
padding = 10

color_bg_menu='green'
color_seletc_menu='red'

listeners = [
    ({"vol": "vol_pct", "mut": "vol_mut"}, [tools['vol']]),
    ({"cpu_load_pct": "cpu"},              [tools['cpu']]),
    ({"free_gb": "ram_free_gb"},           [tools['ram'], "gb"]),
    ({"free_gb": "c_free_gb"},             [tools['disk'], "C", "gb"]),
    ({"gpu_load_pct": "gpu_pct", "gpu_temp_c": "gpu_temp"}, [tools['gpu']]),
    ({"rx": "down_bps", "tx": "up_bps"},   [tools['net'], "/a", "all", "/min", "kb"]),
]
time_format="%H:%M" 