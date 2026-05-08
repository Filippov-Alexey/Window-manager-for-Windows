import os
from pathlib import Path
import logger
log=logger.setup_logging()
import os

dirtools = 'components'
components = {}

for root, dirs, files in os.walk(dirtools):
    if '__pycache__' in root:
        continue
        
    for file in files:
        if file.endswith(".exe"):
            name = file[:-4]
            if os.path.basename(root) == name:
                rel_path = os.path.relpath(root, dirtools)
                category = rel_path.split(os.sep)[0]
                if category not in components:
                    components[category] = {}
                
                path = os.path.join(root, file)
                components[category][name] = '.\\' + path

TITLE="ФиЛиПпОв_"

ports={'get_key':65431,'get_win':65432,'get_display':65434,'get_space':65435}

desktop={'space':'5', 'x':'3000', 'y':'0', 'interval':'3000'}
plugins_dir = Path(os.path.expandvars('.')) / "plugins"
plugins_dir.mkdir(parents=True, exist_ok=True)
RECT = 26
patterns = [
    TITLE,
    "Microsoft Text Input Application",
    "Системный монитор",
    "Program Manager",
    "ApplicationFrameHost",
    "XTPFrameShadow",
    "Alt-Tab Terminator*",
    "Volume² OSD Window",
    "ApplicationFrameWindow"
    "Drag",
    "Хост Windows Shell Experience",
    "Block Blast!",
    "[ApplicationFrameWindow]",
    "Недопустимый дескриптор окна."
]
patterns_for_progs=[
    'D:\\ntwind_altab_terminator_5.2\\AltTabTerminator\\App\\AltTabTerminator\\AltTabTer64.exe',
    'C:\\Windows\\SystemApps\\Microsoft.Windows.Search_cw5n1h2txyewy\\SearchApp.exe',
    "C:\\Program Files\\Adobe\\Adobe Photoshop 2023\\Photoshop.exe",
    'C:\\Windows\\System32\\ApplicationFrameHost.exe'
]
def is_ignored(window_title):
    import fnmatch
    if not window_title:
        return True
        
    for pattern in patterns:
        if fnmatch.fnmatch(window_title, pattern):
            return True
    return False
open_one=["C:\\Windows\\system32\\mspaint.exe"]
win_size={"C:\\Users\\alexey\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe":(7,0,-6,-6)}

margin=5
master_factor=0.5
tile_mode = 'grid'
display=None
 
