import os
from pathlib import Path
icons_dir = Path(os.path.expandvars(r"%TEMP%")) / "icon"
icons_dir.mkdir(parents=True, exist_ok=True)
UPDATE_ICON_MS = 500
UPDATE_STATUS_MS = 500
UPDATE_GRAPMS = 100
ICON_SIZE = 16
MARGIN_LEFT = 8
GAP = 8
RECT_HEIGHT = 26

W_CPU   = 7 
W_RAM   = 9
W_DRIVE = 9
W_NET   = 7
W_VOL   = 7 
W_GPU   = 8 
W_TEMP  = 7 
W_LAYOUT= 5
W_TIME  = 6

patterns = [
    "Microsoft Text Input Application",
    "Microsoft*",
    "Системный монитор",
    "SystemSettings.exe",
    "Program Manager",
    "ApplicationFrameHost.exe",
    "XTPFrameShadow",
    "Alt-Tab Terminator*",
    "Volume² OSD Window",
    "Drag",
    "Хост Windows Shell Experience"
]

photo_cache = {}
canvas_items = {}
points=[]
tit=[]

UPDATE_TIME_S = 60
UPDATE_VOLUME_S = 1
UPDATE_NETWORK_S = 1
UPDATE_CPU_S = 1
UPDATE_LAYOUT_S = 0.5
UPDATE_RAM_S = 1
UPDATE_GPU_S = 1
UPDATE_DISK_S = 60
SHORTCUTS_DIR = [[Path("E:\\pymypcserver\\win\\shortcus\\"),500,0],[Path("D:\\inet\\"),600,0],[Path("D:\\shutdown\\"),1120,0],[Path("D:\\winpanstart\\"),1000,0]]

open_one=["C:\\Windows\\system32\\mspaint.exe"]
win_rect={
            "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe":(1.002,1.002,1.001,1.001),
         }
winpos={1:{0:[0,35,805,440],1:[805,35,1920,1078],2:[0,443,805,1078]},'max':[0,35,1920,1078]}

hot_key={'shift+ctrl+z':'D:\\winpanbat\\cc\\zn.bat',
         'shift+ctrl+v':'D:\\winpanbat\\cc\\vk.bat',
         'shift+ctrl+o':'D:\\winpanbat\\cc\\ok.bat',
         'shift+ctrl+y':'D:\\winpanbat\\cc\\yt.bat',
         'shift+ctrl+b':'D:\\winpanbat\\cc\\bo.bat',
         'shift+ctrl+r':'D:\\winpanbat\\cc\\rt.bat',
         'shift+ctrl+t':'D:\\winpanbat\\cc\\tg.bat',
         'shift+ctrl+k':'D:\\winpanbat\\cc\\kl.bat',
         'shift+ctrl+page_down':'D:\\winpanbat\\cc\\startsnandart.bat' 
        }
new_win_open_max=True
