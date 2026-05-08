from socket_client import BaseSocketClient
import pygetwindow
import threading
import subprocess
import time
from variable import ports,win_size,components,RECT,tile_mode,master_factor,margin
from variable_def import get_monitor, get_winpos
import logger
import win32process
import win32api
import win32con

log=logger.setup_logging()
indexwin=0
active_win=[]
winpos = get_winpos()

def keywork(stdout, stop_event):
    while stop_event.is_set():  
        output = stdout.readline()
        if not output: 
            break
        output = output.strip()
        if output:
            try:
                result_data = output.split(': ')[1]
                handle_key_press(result_data)
            except Exception as e:
                log.info(f"Error processing output: {e}\t{output}")
def get_path_from_hwnd(hwnd):
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, 
            False, 
            pid
        )
        
        if handle:
            path = win32process.GetModuleFileNameEx(handle, 0)
            win32api.CloseHandle(handle)
            return path
            
    except Exception as e:
        return f"Ошибка: {e}"
    
    return None

def set_window_position(w, wp):
    client = BaseSocketClient(ports['get_win'], "WinCtrl-SetPos", is_zlib=True)
    tit = client.request()
    if not tit: return
    hw = w._hWnd
    target_data = next((item for item in tit if item['hwnd'] == hw), None)
    for item in tit:
        log.info(f'{item['hwnd']}={hw}')
        if item['hwnd'] == hw:
            log.info(hw)
            target_data = item
            break  
    path = target_data.get('path')
    title = target_data.get('title')
    size = win_size.get(path)
    
    if size:
        left = wp[0] + size[0]
        top = wp[1] + size[1]
        right = wp[2] + size[2]
        bottom = wp[3] + size[3]
        log.info(f"📐 Коррекция для {title}: {size}")
    else:
        left, top, right, bottom = wp

    width = right - left
    height = bottom - top
    try:
        if w.isMaximized:
            w.restore()
        w.moveTo(left, top)      
        w.resizeTo(width, height)
    except Exception as e:
        log.error(f"Ошибка перемещения: {e}")
    
def getindexwin(windows,winpos):
    if windows is not None:
        centerx=windows.left+windows.width//2 
        centery=windows.top+windows.height//2
        for index,coord in winpos[1].items():
            if coord[0]<centerx<coord[2] and coord[1]<centery<coord[3]:
                return index
    return None
def winmove(directions, w, i, indexwin=None):
    try:
        if not w:
            return

        if directions in ['up', 'down', 'left', 'right']:
            try:
                idx = getindexwin(w,winpos) 
                if directions == 'up':
                    log.info('up')
                    set_window_position(w, winpos['max'])
                elif directions == 'down':
                    w.minimize()
                elif directions == 'right':
                    idx = (idx + 1) % 3
                    set_window_position(w, winpos[i][idx])
                elif directions == 'left':
                    idx = (idx - 1) % 3
                    set_window_position(w, winpos[i][idx])
                return 
            except Exception as e:
                log.error(f"Manual move error: {e}")
                return

        min_x,min_y,max_x,max_y = get_monitor()
        scr_w = max_x-min_x
        scr_h = max_y-min_y

        top_offset = RECT
        
        mode = tile_mode

        curr_x, curr_y = margin, top_offset + margin
        work_w = scr_w - (margin * 2)
        work_h = scr_h - top_offset - (margin * 2)


        w.restore()
        if mode == 'bsp':
            temp_w, temp_h = work_w, work_h
            for step in range(indexwin):
                if step == i:
                    if step < indexwin - 1:
                        if temp_w > temp_h:
                            target_w, target_h = (temp_w - margin) // 2, temp_h
                        else:
                            target_w, target_h = temp_w, (temp_h - margin) // 2
                    else:
                        target_w, target_h = temp_w, temp_h
                    
                    w.moveTo(int(curr_x), int(curr_y))
                    w.resizeTo(int(target_w), int(target_h))
                    break

                if temp_w > temp_h:
                    split = (temp_w - margin) // 2
                    curr_x += (split + margin)
                    temp_w -= (split + margin)
                else:
                    split = (temp_h - margin) // 2
                    curr_y += (split + margin)
                    temp_h -= (split + margin)

        elif mode == 'master':
            if indexwin == 1:
                winmove('up', w, i)
            else:
                m_factor = master_factor
                m_w = int(work_w * m_factor) - (margin // 2)
                if i == 0:
                    w.moveTo(curr_x, curr_y)
                    w.resizeTo(m_w, work_h)
                else:
                    s_win_h = (work_h - (margin * (indexwin - 2))) // (indexwin - 1)
                    pos_x = curr_x + m_w + margin
                    pos_y = curr_y + (i - 1) * (s_win_h + margin)
                    final_h = (curr_y + work_h) - pos_y if i == indexwin - 1 else s_win_h
                    w.moveTo(pos_x, pos_y)
                    w.resizeTo(work_w - m_w - margin, final_h)

        elif mode == 'grid':
            if indexwin == 1:
                log.info('m')
                winmove('up', w, i)
            else:
                grid_positions = winpos.get(1, {})
                max_predefined = len(grid_positions)

                pos_index = i % max_predefined
                rect = grid_positions.get(pos_index)

                if rect:
                    x1, y1, x2, y2 = rect
                    final_w = x2 - x1 - margin
                    final_h = y2 - y1 - margin

                    w.restore()
                    w.moveTo(int(x1), int(y1))
                    w.resizeTo(int(final_w), int(final_h))

    except Exception as e:
        log.error(f"Ошибка в winmove: {e}")

def handle_key_press(out):
    title=out.split(', ')[3][6:]
    status=int(out.split(', ')[1][4:])
    w=pygetwindow.getWindowsWithTitle(title)[0]
    if status==3:
        set_window_position(w, winpos['max'])

def run_and_check(stop_event):
    while not stop_event.is_set():
        process = subprocess.Popen(
            [components['services']["win"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        
        time.sleep(2)
        
        if process.poll() is None:
            log.error("Процесс стабилен, работаем.")
            return process
        
        log.info("Процесс упал мгновенно. Перезапуск...")
        time.sleep(1)
    return None

def runmouse(stop_event):
    process = run_and_check(stop_event)
    
    if process is None:
        log.error("❌ Не удалось запустить процесс в runmouse.")
        return
    output_thread = threading.Thread(
        target=keywork, 
        args=(process.stdout,stop_event,), 
        name="KeyworkThread",
        daemon=True
    )
    output_thread.start()

    try:
        while not stop_event.wait(timeout=0.5):
            if process.poll() is not None:
                log.warning("⚠️ Процесс в runmouse завершился сам по себе")
                break
                
    finally:
        stop_event.set() 
        
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except:
                process.kill()
        if process.stdout:
            process.stdout.close()
            
        log.info("✅ Модуль runmouse полностью остановлен")

if __name__ == "__main__":
    runmouse()