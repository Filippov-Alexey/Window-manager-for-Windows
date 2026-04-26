from socket_client import BaseSocketClient
import pygetwindow
import threading
import subprocess
import time
import variable
import logger

log=logger.setup_logging()

stop_event = threading.Event()
indexwin=0
active_win=[]
def keywork(stdout):
    while not stop_event.is_set():  
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
import win32process
import win32api
import win32con
def get_path_from_hwnd(hwnd):
    try:
        # 1. Получаем ID процесса (PID) по HWND
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        
        # 2. Открываем процесс для получения информации
        # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
        handle = win32api.OpenProcess(
            win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, 
            False, 
            pid
        )
        
        if handle:
            # 3. Получаем путь к исполняемому файлу
            path = win32process.GetModuleFileNameEx(handle, 0)
            win32api.CloseHandle(handle)
            return path
            
    except Exception as e:
        return f"Ошибка: {e}"
    
    return None

def set_window_position(w, wp):
    client = BaseSocketClient(variable.ports['get_win'], "WinCtrl-SetPos", is_zlib=True)
    tit = client.request()
    if not tit: return
    hw = w._hWnd
    log.info(tit)
    log.info(w.title)
    target_data = next((item for item in tit if item['hwnd'] == hw), None)
    log.info(target_data)
    for item in tit:
        log.info(f'{item['hwnd']}={hw}')
        if item['hwnd'] == hw:
            log.info(hw)
            target_data = item
            break  # Нашли — выходим из цикла
    log.info(target_data)
    
    path = target_data.get('path')
    title = target_data.get('title')

    # Проверка на игнорируемые паттерны
    # if title in variable.patterns:
    #     return

    # 1. Проверяем наличие оффсетов для этой программы
    size = variable.win_size.get(path)
    
    if size:
        # Если программа в списке — добавляем оффсеты к координатам сетки
        left = wp[0] + size[0]
        top = wp[1] + size[1]
        right = wp[2] + size[2]
        bottom = wp[3] + size[3]
        log.info(f"📐 Коррекция для {title}: {size}")
    else:
        # Если программы нет в списке — используем чистую сетку wp
        log.info(wp)
        left, top, right, bottom = wp

    # 2. Вычисляем финальные размеры
    width = right - left
    height = bottom - top
    log.info(f'{left} {top} {width} {height} {w.title }')

    # 3. Применяем позицию
    try:
        if w.isMaximized:
            w.restore()
        w.moveTo(left, top)      
        w.resizeTo(width, height)
    except Exception as e:
        log.error(f"Ошибка перемещения: {e}")
    
def getindexwin(windows):
    if windows is not None:
        centerx=windows.left+windows.width//2 
        centery=windows.top+windows.height//2
        for index,coord in variable.winpos[1].items():
            if coord[0]<centerx<coord[2] and coord[1]<centery<coord[3]:
                return index
    return None
def winmove(directions, w, i, indexwin=None):
    try:
        if not w:
            return
        log.info(w)

        # 1. Сначала проверяем ручные команды (вне тайлинга)
        if directions in ['up', 'down', 'left', 'right']:
            try:
                # Получаем текущий индекс положения окна для циклического переключения
                idx = getindexwin(w) 
                if directions == 'up':
                    log.info('up')
                    set_window_position(w, variable.winpos['max'])
                elif directions == 'down':
                    w.minimize()
                elif directions == 'right':
                    idx = (idx + 1) % 3
                    set_window_position(w, variable.winpos[i][idx])
                elif directions == 'left':
                    idx = (idx - 1) % 3
                    set_window_position(w, variable.winpos[i][idx])
                return # Выходим, тайлинг не нужен
            except Exception as e:
                log.error(f"Manual move error: {e}")
                return

        # 2. Логика автоматического тайлинга
        scr_w, scr_h = variable.extension
        margin = variable.margin
        top_offset = variable.RECT
        
        # Определяем режим: либо из аргумента, либо из глобальной переменной
        mode = directions if directions in ['bsp', 'grid', 'master'] else getattr(variable, 'tile_mode', 'bsp')

        curr_x, curr_y = margin, top_offset + margin
        work_w = scr_w - (margin * 2)
        work_h = scr_h - top_offset - (margin * 2)


        w.restore()
        # --- BSP ---
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

        # --- MASTER ---
        elif mode == 'master':
            if indexwin == 1:
                winmove('up', w, i)
                # w.moveTo(curr_x, curr_y)
                # w.resizeTo(work_w, work_h)
            else:
                m_factor = getattr(variable, 'master_factor', 0.5)
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

        # --- GRID (Цикличное размещение по кастомной сетке) ---
        elif mode == 'grid':
            # Если окно всего одно — используем координаты 'max'
            if indexwin == 1:
                log.info('m')
                winmove('up', w, i)
            else:
                # Если окон несколько — идем по циклу 0, 1, 2...
                grid_positions = variable.winpos.get(1, {})
                max_predefined = len(grid_positions)

                # Выбираем позицию (0, 1 или 2)
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
        set_window_position(w, variable.winpos['max'])

def run_and_check():
    while True:
        process = subprocess.Popen(
            [variable.tools["win"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        
        # Даем время на запуск
        time.sleep(2)
        
        # Если poll() возвращает None, значит процесс ЖИВ
        if process.poll() is None:
            log.error("Процесс стабилен, выходим из цикла.")
            return process  # Выход из функции и цикла
        
        # Если мы здесь, значит процесс умер
        log.info("Процесс упал. Пробуем еще раз через секунду...")
        time.sleep(1) 
def runmouse():
    process=run_and_check()
    output_thread = threading.Thread(target=keywork, args=(process.stdout,))
    output_thread.start()
    try:
        while True:  
            time.sleep(0.1) 
    except KeyboardInterrupt:
        stop_event.set() 
        log.info("Stopping...")
    finally:
        stop_event.set() 
        output_thread.join()  
        return_code = process.wait()  
        
if __name__ == "__main__":
    runmouse()