from socket_server import BaseServer
from subprocess_server import BaseSubprocessServer
import pygetwindow
import json
import ast
from variable import *
from windows_controle import *
from PIL import Image
import win32gui
import win32process
import win32api
import win32ui
import win32con
import logger
log=logger.setup_logging()
aw = []
serialized_data = ''.encode()
def extract_icon_from_exe(path, index=0, size=2 , save_to=None):
    log.log('run')
    large, small = win32gui.ExtractIconEx(path, index)
    hicon = None
    
    if size <= 32 and small:
        hicon = small[0]
    elif large:
        hicon = large[0]
    elif small:
        hicon = small[0]

    if not hicon:
        raise FileNotFoundError("Icon not found in: " + path)

    hdc_screen = win32gui.GetDC(0)
    hdc = win32ui.CreateDCFromHandle(hdc_screen)
    mem_dc = hdc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(hdc, size, size)

    mem_dc.SelectObject(bmp)
    win32gui.DrawIconEx(mem_dc.GetHandleOutput(), 0, 0, hicon, size, size, 0, None, win32con.DI_NORMAL)

    bmpinfo = bmp.GetInfo()
    bmpstr = bmp.GetBitmapBits(True)
    
    img = Image.frombuffer(
        'RGBA',
        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
        bmpstr, 'raw', 'BGRA', 0, 1
    )

    if save_to:
        img.save(save_to)

    win32gui.DestroyIcon(hicon)
    mem_dc.DeleteDC()
    hdc.DeleteDC()
    win32gui.ReleaseDC(0, hdc_screen)

    return img
import win32com
def force_activate(hwnd):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys('%') # Имитируем нажатие ALT
        
        # 1. Восстанавливаем окно, если оно свернуто
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        # 2. Выводим на передний план
        win32gui.SetForegroundWindow(hwnd)
        # 3. Разворачиваем (опционально)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW) 
        return True
    except Exception as e:
        log.error(f"Ошибка: {e}")
        return False



def bring_window_to_front(hwnd):
    if not win32gui.IsWindow(hwnd):
        return

    user32 = ctypes.windll.user32
    
    try:
        # 1. Подготовка окна
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

        # 2. Получаем поток текущего активного окна
        fore_hwnd = win32gui.GetForegroundWindow()
        fore_thread = win32process.GetWindowThreadProcessId(fore_hwnd)[0]
        curr_thread = win32api.GetCurrentThreadId()

        # 3. ГЛАВНЫЙ ХАК: Привязываемся к потоку активного окна
        # Это дает нам временное "право" управлять окнами от его лица
        if fore_thread != curr_thread:
            user32.AttachThreadInput(curr_thread, fore_thread, True)
            
        # 4. Попытка установить фокус через несколько системных вызовов
        user32.AllowSetForegroundWindow(-1)
        
        # Порядок вызовов важен
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
        win32gui.SetActiveWindow(hwnd)
        
        # 5. Отвязываемся
        if fore_thread != curr_thread:
            user32.AttachThreadInput(curr_thread, fore_thread, False)

        # 6. Форсируем Z-порядок (поверх всех на миллисекунду)
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, 
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)

    except Exception as e:
        # Последний шанс: если API отказало, используем системную команду "свернуть-развернуть"
        # Это заставляет ядро Windows перерисовать окно сверху
        win32gui.PostMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_RESTORE, 0)

lest_line = None
lest_hwnd = set()
import win32gui

lest_hwnd_info = {} # Структура: {hwnd: {"title": title, "path": path}}
def c_plus_plus_listener():
    global lest_hwnd
    win_server = BaseServer(ports['get_win'], "WindowServer", is_json=True, is_zlib=True)

    class WindowProcessHandler(BaseSubprocessServer):
        def parse_line(self, line):
            global lest_hwnd
            line = line.strip()
            if not line.startswith('['): 
                return None
                
            win = pygetwindow.getActiveWindow()
            if not win: return None
            
            # Проверка игнорируемых окон
            if not (line.startswith('[') and (not is_ignored(win.title) or win.title == TITLE or win.title == "Program Manager")):
                return None

            try:
                data_obj = ast.literal_eval(line)
                if not data_obj: return None

                win_server.broadcast(data_obj)
                
                active_info = data_obj[0]
                current_hwnds = {item['hwnd'] for item in data_obj}
                
                added = current_hwnds - lest_hwnd
                removed = lest_hwnd - current_hwnds

                if added or removed:
                    log.error('='*20)
                    lest_hwnd = current_hwnds.copy()

                    first_path = active_info['path']
                    consecutive_windows = []
                    for item in data_obj:
                        if item['path'] == first_path:
                            consecutive_windows.append(item)
                        else:
                            break
                    
                    total_count = len(consecutive_windows)
                    mode = getattr(variable, 'tile_mode', 'tile')

                    # Тяжелый цикл перемещения
                    for i, win_data in enumerate(reversed(consecutive_windows)):
                        try:
                            target_window = pygetwindow.Win32Window(win_data['hwnd'])
                            winmove(mode, target_window, i, total_count)
                        except Exception as e:
                            log.debug(f"Ошибка перемещения: {e}")

                if active_info.get('active') != 1:
                    bring_window_to_front(active_info['hwnd'])

            except Exception as e:
                log.error(f"Ошибка в WindowProcessHandler: {e}")
            
            # Возвращаем None, так как broadcast уже выполнен вручную
            return None 

    handler = WindowProcessHandler(
        server_instance=win_server,
        cmd=[tools['getwin']],
        stop_event=stop_event,
        label="Слушатель окон"
    )
    handler.run()

if __name__ == "__main__":
    while True: # Добавьте цикл перезапуска по аналогии с клавиатурным сервером
        try:
            c_plus_plus_listener()
        except Exception as e:
            log.error(f"Рестарт слушателя окон из-за ошибки: {e}")
            time.sleep(1)
