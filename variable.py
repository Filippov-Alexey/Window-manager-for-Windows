import re
import socket
import subprocess
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

def get_excluded_ports():
    excluded_ranges = []
    try:
        result = subprocess.run(
            ["netsh", "int", "ipv4", "show", "excludedportrange", "protocol=tcp"],
            capture_output=True,
            text=True,
            encoding="cp866",
        )
        if result.returncode == 0:
            matches = re.findall(r"(\d+)\s+(\d+)", result.stdout)
            for start, end in matches:
                excluded_ranges.append((int(start), int(end)))
    except Exception:
        pass
    return excluded_ranges


def is_port_blocked_by_system(port, excluded_ranges):
    for start, end in excluded_ranges:
        if start <= port <= end:
            return True
    return False


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("localhost", port))
            return False 
        except socket.error:
            return True 


def find_free_ports(services, start_port=50000):
    allocated_ports = {}
    excluded_ranges = get_excluded_ports()
    current_port = start_port

    for service in services:
        while True:
            if not is_port_blocked_by_system(
                current_port, excluded_ranges
            ) and not is_port_in_use(current_port):
                allocated_ports[service] = current_port
                current_port += 1
                break
            current_port += 1  
    return allocated_ports
required_services = ["get_key", "get_win", "get_display", "get_space"]
ports = find_free_ports(required_services, start_port=50000)

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
# win_size={"C:\\Users\\alexey\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe":(7,0,-6,-6),"O:\\program\\Obsidian\\Obsidian.exe":(6,0,-7,-7)}
win_size={}
margin=5
master_factor=0.5
tile_mode = 'grid'
display=None
 
