import threading
import json
import time
import sys
import pygetwindow
from variable import ports,patterns,tools,desktop
import win32gui
import win32con
import logger
log=logger.setup_logging()
# Флаги и хранилища
stop_event = threading.Event()
data_lock = threading.Lock()
last_desktop_data = {"data": None}
last_win_titles = {"data": []} 

SPACE_STEP = int(desktop['interval'])

def get_anchors_map():
    anchors = {}
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title.startswith("desktop_space_"):
                try:
                    # Извлекаем номер из заголовка desktop_space_1 -> 0
                    idx = int(title.split('_')[-1]) - 1
                    rect = win32gui.GetWindowRect(hwnd)
                    anchors[idx] = rect[0]
                except: pass
        return True
    win32gui.EnumWindows(callback, None)
    return anchors

def move_all_relative(target_idx):
    anchors = get_anchors_map()
    
    if not anchors:
        log.info("⚠️ Якоря не найдены! Не могу определить смещение.")
        return
    any_idx = next(iter(anchors))
    current_anchor_x = anchors[any_idx]
    ideal_anchor_x = any_idx * SPACE_STEP
    
    global_offset = current_anchor_x - ideal_anchor_x
    shift_x = -(target_idx * SPACE_STEP) - global_offset

    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title in patterns: return True
            
            rect = win32gui.GetWindowRect(hwnd)
            x, y = rect[0], rect[1]
            if x < -10000 or x > 100000: return True

            try:
                win32gui.SetWindowPos(
                    hwnd, None, x + int(shift_x), y, 0, 0,
                    win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE
                )
            except: pass
        return True

    win32gui.EnumWindows(callback, None)

def get_current_space_index():
    anchors = get_anchors_map()
    if not anchors:
        return 0
    
    # Берем любой якорь
    any_idx = next(iter(anchors))
    current_x = anchors[any_idx]
    
    current_view = (any_idx * SPACE_STEP - current_x) // SPACE_STEP
    return int(current_view)

def handle_key_press(raw_json_data):
    try:
        out = json.loads(raw_json_data)
        if out.get('status') != 'Up': return
        
        items = out.get('option', [])
        keys_str = "+".join(items).lower()

        if 'left_win' in keys_str:
            current_idx = get_current_space_index()
            
            if 'page_up' in keys_str:
                target_idx = min(current_idx + 1, 9)
                move_all_relative(target_idx)
                return 
                 
            elif 'page_down' in keys_str:
                target_idx = max(current_idx - 1, 0)
                move_all_relative(target_idx)
                return

        target_n = None
        for char in "1234567890":
            if char in keys_str:
                target_n = 9 if char == "0" else int(char) - 1
                break
        
        if not target_n is None: 

            if 'left_alt' in keys_str:
                move_all_relative(target_n)

            elif 'left_ctrl' in keys_str:
                active_win = pygetwindow.getActiveWindow()
                if active_win:
                    anchors = get_anchors_map()
                    if anchors:
                        any_idx = next(iter(anchors))
                        world_origin = anchors[any_idx] - (any_idx * SPACE_STEP)
                        
                        rect = win32gui.GetWindowRect(active_win._hWnd)
                        rel_x = (rect[0] - world_origin) % SPACE_STEP
                        new_x = world_origin + (target_n * SPACE_STEP) + rel_x
                        
                        win32gui.SetWindowPos(
                            active_win._hWnd, None, int(new_x), rect[1], 0, 0,
                            win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE
                        )
        
        space_server.broadcast(f"{get_current_space_index() + 1}")

    except Exception as e:
        log.error(f"🚨 Error: {e}")


from socket_client import BaseSocketClient
import threading
import time
from socket_server import BaseServer  
from subprocess_server import BaseSubprocessServer
space_server=None
def run_desktop_and_read_output():
    global space_server
    space_server = BaseServer(ports['get_space'], "SpaceServer", is_json=False, is_zlib=False)
    
    cmd = [tools['space'], "/space", desktop['space'], "/x", desktop['x'], "/y", desktop['y']]

    class SpaceHandler(BaseSubprocessServer):
        def handle_data(self, data):
            if data:
                with data_lock:
                    last_desktop_data["data"] = data

    handler = SpaceHandler(
        server_instance=space_server,
        cmd=cmd,
        stop_event=stop_event,
        label="SpaceServer"
    )
    
    handler.run()


def handle_win_data(raw_bytes):
        with data_lock:
            last_win_titles["data"] = raw_bytes
            

def socket_client_worker(port_name, handler, send_init=None):
    client = BaseSocketClient(
        port=ports[port_name], 
        name=f"Srv-{port_name}", 
        is_json=False
    )

    log.info(f"📡 Запуск воркера для порта {port_name}")
    def protected_handler(data):
        if not stop_event.is_set():
            handler(data)
    client.run_loop(
        handler=protected_handler, 
        init_msg=send_init
    )
from manager import win_manager  # Убедитесь, что импорт верный

if __name__ == "__main__":
    win_manager.subscribe(handle_win_data)
    threads = [
        threading.Thread(target=socket_client_worker, args=('get_key', handle_key_press), daemon=True),
    ]

    for t in threads:
        t.start()

    try:
        run_desktop_and_read_output()
    except KeyboardInterrupt:
        log.info("\n🛑 Program stopping...")
        stop_event.set()
        time.sleep(1) # Время на закрытие процессов
        sys.exit(0)
