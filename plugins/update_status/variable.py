from variable import *
W_CPU   = 7 
W_RAM   = 9
W_DRIVE = 9
W_NET   = 7
W_VOL   = 7 
W_GPU   = 8 
W_TEMP  = 7 
W_LAYOUT= 5
W_TIME  = 6
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

keys = ["time", "cpu", "ram", "drive", "network", "volume", "layout", "gpu"]
if not orientation:
    y=RECT // 2
    pos = [(x, y) for x in [682, 608, 520, 432, 272, 200, 145, 8]]
else:
    x=RECT // 2
    pos = [(x, y) for y in [15,35,55,85,105,125,145,175]]

scr_w, scr_h = extension[0], extension[1]
        
menu_width = 200
row_height = 30
padding = 10

color_bg_menu='green'
color_seletc_menu='red'

