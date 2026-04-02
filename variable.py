import subprocess
import os
from pathlib import Path
from screeninfo import get_monitors
from windows_controle import winmove
import win32api
import ctypes
import logger
import mouse
log=logger.setup_logging()
dirtools='tools'
tools={}
for root, dirs, files in os.walk(dirtools):
    if root!='__pycache__':
        for file in files:
            if root[6:]==file[:-4] and file.endswith(".exe"):
                path = os.path.join(root, file)
                tools[file[:-4]]='.\\'+path

def get_layout_names():
    LOCALE_SLANGUAGE = 0x0002 
    layout_ids = win32api.GetKeyboardLayoutList()
    layouts = []
    for hkl in layout_ids:
        lang_id = hkl & (0xFFFF)
        buffer = ctypes.create_unicode_buffer(256)
        
        if ctypes.windll.kernel32.GetLocaleInfoW(lang_id, LOCALE_SLANGUAGE, buffer, 256):
            layouts.append([f"0x{(hkl & 0xFFFFFFFFFFFFFFFF):016x}",buffer.value])
    return layouts
layouts=get_layout_names()

def get_index_layout_list(current_id):
    log.warning(current_id)
    current_index = -1
    try:
        for i,k in enumerate(layouts):
            log.info(f'{i}={k}')
            if k[0] == current_id:
                current_index = i
                break
    except Exception as e:
        log.error(e)
    return current_index
def get_next_layout_hkl(current_id):
    current_index=get_index_layout_list(current_id)
    try:        
         if current_index != -1:
            next_index = (current_index + 1) % len(layouts)
            log.warning(layouts[next_index])
            return layouts[next_index]
    except Exception as e:
        print(e)
    return None
w = get_monitors()[0].width
h = get_monitors()[0].height

extension=[w,h]

TITLE="ФиЛиПпОв_"

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
    'D:\\ntwind_altab_terminator_5.2\\AltTabTerminator\\App\\AltTabTerminator\\AltTabTer64.exe'
    'C:\\Windows\\System32\\ApplicationFrameHost.exe'
]
open_one=["C:\\Windows\\system32\\mspaint.exe"]
win_size={"C:\\Users\\alexey\\AppData\\Local\\Programs\\Microsoft VS Code\\Code.exe":(7,0,-6,-6)}
winpos={1:{0:[5,35,805,440],1:[805,35,1920,1078],2:[5,443,805,1078]},'max':[5,35,1920,1078]}

ACTIONS = {
    'pause':             lambda w, i: mouse.click('right'),
    'left_shift+pause':  lambda w, i: mouse.click('right'),
    'left_win+arrow_right': lambda w, i: winmove('right', w, i),
    'left_win+arrow_left':  lambda w, i: winmove('left', w, i),
    'left_win+arrow_up':    lambda w, i: winmove('up', w, i),
    'left_win+arrow_down':  lambda w, i: winmove('down', w, i),
    'left_win+delete':      lambda w, i: w.close(),
    'left_win+p':           lambda w, i: subprocess.run([tools['press'], 'left_win+p']),
    'left_win+v':           lambda w, i: subprocess.run([tools['press'], 'left_win+v']),
    'left_win+r':           lambda w, i: subprocess.run([tools['press'], 'left_win+r']),
    'left_win+e':           lambda w, i: subprocess.run([tools['press'], 'left_win+e']),
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
ports={'get_key':65431,'get_win':65432,'is_full_win':65433,'get_display':65434}