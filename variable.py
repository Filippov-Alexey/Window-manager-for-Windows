import subprocess
import os
from pathlib import Path
from screeninfo import get_monitors
from windows_controle import winmove
import py_win_keyboard_layout
layouts = py_win_keyboard_layout.get_keyboard_layout_list()
def get_index_layout_list(current_id):
    current_index = -1
    for i, k in enumerate(layouts):
        if f"0x{(k & 0xFFFF):04x}" == current_id:
            current_index = i
            break
    return current_index
def get_next_layout_hkl(current_id):
    current_index=get_index_layout_list(current_id)
    if current_index != -1:
        next_index = (current_index + 1) % len(layouts)
        next_hkl = layouts[next_index]
        
        hkl_hex = f"0x{next_hkl:016x}" 
        return hkl_hex
    return None
w = get_monitors()[0].width
h = get_monitors()[0].height

extension=[w,h]

TITLE="!@#$%^&*()_+][poiug]"

plugins_dir = Path(os.path.expandvars('.')) / "plugins"
plugins_dir.mkdir(parents=True, exist_ok=True)
RECT = 26
patterns = [
    TITLE,
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
    "Хост Windows Shell Experience",
    "Block Blast!",
    "Недопустимый дескриптор окна."
]

open_one=["C:\\Windows\\system32\\mspaint.exe"]
win_size={"C:\\Users\\alexey\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe":(7,0,-6,-6)}
winpos={1:{0:[5,35,805,440],1:[805,35,1920,1078],2:[5,443,805,1078]},'max':[5,35,1920,1078]}

ACTIONS = {
    'pause':             lambda w, i: subprocess.run(['click']),
    'left_shift+pause':  lambda w, i: subprocess.run(['click']),
    'left_win+arrow_right': lambda w, i: winmove('right', w, i),
    'left_win+arrow_left':  lambda w, i: winmove('left', w, i),
    'left_win+arrow_up':    lambda w, i: winmove('up', w, i),
    'left_win+arrow_down':  lambda w, i: winmove('down', w, i),
    'left_win+delete':      lambda w, i: w.close(),
    'left_win+v':           lambda w, i: subprocess.run(['press', 'left_win+v']),
    'left_win+r':           lambda w, i: subprocess.run(['press', 'left_win+r']),
    'left_win+e':           lambda w, i: subprocess.run(['press', 'left_win+e']),
    'insert':           lambda w, i: subprocess.run(['press', 'f2']),
    'shift+ctrl+z':lambda w, i: subprocess.run('D:\\winpanbat\\cc\\zn.bat'),
    'shift+ctrl+v':lambda w, i: subprocess.run('D:\\winpanbat\\cc\\vk.bat'),
    'shift+ctrl+o':lambda w, i: subprocess.run('D:\\winpanbat\\cc\\ok.bat'),
    'shift+ctrl+y':lambda w, i: subprocess.run('D:\\winpanbat\\cc\\yt.bat'),
    'shift+ctrl+b':lambda w, i: subprocess.run('D:\\winpanbat\\cc\\bo.bat'),
    'shift+ctrl+r':lambda w, i: subprocess.run('D:\\winpanbat\\cc\\rt.bat'),
    'shift+ctrl+t':lambda w, i: subprocess.run('D:\\winpanbat\\cc\\tg.bat'),
    'shift+ctrl+k':lambda w, i: subprocess.run('D:\\winpanbat\\cc\\kl.bat'),
    'shift+ctrl+page_down':lambda w, i: subprocess.run('D:\\winpanbat\\startsnandart.bat') 
}

new_win_open_max=True
ports={'get_key':65431,'get_win':65432,'is_full_win':65433}