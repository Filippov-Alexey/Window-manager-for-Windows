import socket
import win32gui
from ctypes import windll
from variable import *
import logger
import time
log=logger.setup_logging()
user32 = windll.user32
get_foreground_window = user32.GetForegroundWindow
get_window_rect = win32gui.GetWindowRect
get_window_text = win32gui.GetWindowText

SW, SH = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
FULL_SCREEN_RECT = (0, 0, SW, SH)

PATTERNS_SET = set(patterns)

def is_full_screen(hwnd):
    try:
        if hwnd != 1400:
            return 1 if get_window_rect(hwnd) == FULL_SCREEN_RECT else 0
    except:
        return 0
st=0
class WindowServer:
    def handle_client(self, conn):
        global st
        try:
            while True: # Цикл отправки внутри соединения
                hwnd = get_foreground_window()
                title = get_window_text(hwnd)
                
                status = 0
                if title != TITLE and title not in PATTERNS_SET and hwnd != 1400:
                    status = is_full_screen(hwnd)
                if st!=status:
                    st=status
                    conn.sendall(status.to_bytes(4, 'big')) # Добавил \n для разделения
                time.sleep(0.2) # Интервал опроса
        except (ConnectionResetError, BrokenPipeError):
            pass 
        finally:
            conn.close()

    def run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('localhost', ports['is_full_win']))
            s.listen(1) # Если клиент всегда один
            while True:
                conn, _ = s.accept()
                self.handle_client(conn)

if __name__ == "__main__":
    user32.SetProcessDPIAware()
    WindowServer().run_server()
