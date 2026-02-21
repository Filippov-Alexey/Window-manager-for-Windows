import os
from pathlib import Path
from variable import patterns
icons_dir = Path(os.path.expandvars(r"%TEMP%")) / "icon"
icons_dir.mkdir(parents=True, exist_ok=True)
ICON_SIZE = 16

MARGIN_LEFT = 8
GAP = 8
RECT = 26
UPDATE_ICON_MS = 500

photo_cache = {}
canvas_items = {}

patterns
orientation=True
def get_start_xy(o):
    if o:
        x = MARGIN_LEFT
        y = RECT // 2
    else:
        y = MARGIN_LEFT+ICON_SIZE//2
        x = RECT // 2
    return x,y