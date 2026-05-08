import subprocess
import mouse
from variable import *

def get_layout_names():
    import win32api
    import ctypes
    LOCALE_SLANGUAGE = 0x0002 
    layout_ids = win32api.GetKeyboardLayoutList()
    layouts = []
    for hkl in layout_ids:
        lang_id = hkl & (0xFFFF)
        buffer = ctypes.create_unicode_buffer(256)
        
        if ctypes.windll.kernel32.GetLocaleInfoW(lang_id, LOCALE_SLANGUAGE, buffer, 256):
            layouts.append([f"0x{(hkl & 0xFFFFFFFFFFFFFFFF):016x}",buffer.value])
    return layouts

def get_index_layout_list(current_id):
    layouts=get_layout_names()
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
    layouts=get_layout_names()
    try:        
         if current_index != -1:
            next_index = (current_index + 1) % len(layouts)
            return layouts[next_index]
    except Exception as e:
        print(e)
        return None
def get_monitor():
    from screeninfo import get_monitors
    monitors=get_monitors()
    min_x = min(m.x for m in monitors)
    min_y = min(m.y for m in monitors)
    max_x = max(m.x + m.width for m in monitors)
    max_y = max(m.y + m.height for m in monitors)

    return min_x,min_y,max_x,max_y
def get_winpos(taskbar_height=RECT+10):
    min_x,min_y,max_x,max_y = get_monitor()
    scr_w = max_x-min_x
    scr_h = max_y-min_y
    W = scr_w
    H = scr_h
    T = taskbar_height
    M = margin

    split_x = int(W * 0.47) 
    split_y = int(H * 0.47)

    return {
        1: {
            0: [M, T, split_x, split_y - M],
            1: [M, split_y, split_x, H],
            2: [split_x, T, W, H]
        },
        'max': [M, T, W, H]
    }
def get_action():
    from windows_controle import winmove
    ACTIONS = {
        'pause':             lambda w, i, out=None: mouse.click('right'),
        'left_shift+pause':  lambda w, i, out=None: mouse.click('right'),
        'left_win+arrow_right': lambda w, i, out=None: winmove('right', w, i),
        'left_win+arrow_left':  lambda w, i, out=None: winmove('left', w, i),
        'left_win+arrow_up':    lambda w, i, out=None: winmove('up', w, i),
        'left_win+arrow_down':  lambda w, i, out=None: winmove('down', w, i),
        'left_win+delete':      lambda w, i, out=None: w.close() if w else None,
        'left_win+p':           lambda w, i: subprocess.run([components['tools']['press'], 'left_win+p']),
        'left_win+v':           lambda w, i: subprocess.run([components['tools']['press'], 'left_win+v']),
        'left_win+r':           lambda w, i: subprocess.run([components['tools']['press'], 'left_win+r']),
        'left_win+e':           lambda w, i: subprocess.run([components['tools']['press'], 'left_win+e']),
        'left_win+x':           lambda w, i: subprocess.run([components['tools']['press'], 'left_win+x']),
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
    return ACTIONS