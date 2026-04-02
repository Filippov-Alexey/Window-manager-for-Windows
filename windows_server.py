import socket
import json
import pygetwindow
import zlib
import ast
from threading import Thread
from variable import *
from windows_controle import *
from PIL import Image
import subprocess
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

def bring_window_to_front(hwnd):
    try:
        if not win32gui.IsWindow(hwnd):
            return
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            fg = win32gui.GetForegroundWindow()
            if fg:
                cur_thread = win32api.GetCurrentThreadId()
                fg_thread = win32process.GetWindowThreadProcessId(fg)[0]
                try:
                    win32process.AttachThreadInput(cur_thread, fg_thread, True)
                    win32gui.SetForegroundWindow(hwnd)
                finally:
                    win32process.AttachThreadInput(cur_thread, fg_thread, False)

        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0,0,0,0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0,0,0,0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    except Exception as ex:
        log.error('Error bringing window to front:', ex)
import re
def get_executable_paths_with_open_windows(exe=None):
    args = [tools['getwin']]
    
    if exe:
        args.append(exe)
        
    try:
        result = subprocess.run(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            encoding='utf-8'
        )
        
        if result.stdout:
            is_ignored=[]
            out = result.stdout
            try:
                # Пробуем декодировать вывод 
                out_utf8_string = ast.literal_eval(out)
                # log.info(out_utf8_string)
                for i in out_utf8_string:
                    if i[1] in patterns or i[2] in patterns_for_progs:
                        continue
                    else:
                        is_ignored.append(i)

                # log.info(is_ignored)
                return is_ignored
            except Exception as decode_ex:
                log.error(f"Decoding error: {decode_ex}")
        
    except subprocess.CalledProcessError as e:
        log.error(f"Error when executing command: {e.stderr}")

    return None

class WindowServer:
    def __init__(self):
        self.clients = []
        self.open_windows = []
        self.current_window_attributes = None
    def handle_client(self, conn, addr):
        self.clients.append(conn)
        try:
            self.send_window_update(conn)

            conn.settimeout(0.5) 
            try:
                first_msg = conn.recv(1024)
                if first_msg:
                    conn.settimeout(None)
                    while True:
                        self.send_window_update(conn)
                        
                        time.sleep(0.1)
                else:
                    log.info(f"[{addr}] Одноразовый запрос (пустой сигнал)")
            except socket.timeout:
                log.info(f"[{addr}] Одноразовое соединение (timeout)")

        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            if conn in self.clients: self.clients.remove(conn)
            conn.close()

    def send_window_update(self, conn):
        global serialized_data
        global serialized_data, aw
        current_window = pygetwindow.getActiveWindow()
        
        if current_window is not None and not current_window in patterns:
            self.current_attributes = {
                'title': current_window.title,
                'left': current_window.left,
                'top': current_window.top,
                'width': current_window.width,
                'height': current_window.height,
                'right': current_window.left+current_window.width,
                'bottom': current_window.top+current_window.height,
                'hwnd': current_window._hWnd,
            }
            if self.current_window_attributes is None or \
                self.current_attributes != self.current_window_attributes:
                self.current_window_attributes = self.current_attributes  
                self.open_windows = get_executable_paths_with_open_windows()  
                if aw != self.open_windows and not self.open_windows is None:
                    current_windows_set = set(i[0] for i in aw)
                    open_windows_set = set(i[0] for i in self.open_windows)

                    new_windows_ids = open_windows_set - current_windows_set
                 
                    for window_id in new_windows_ids:
                        full_element = next((elem for elem in self.open_windows if elem[0] == window_id), None)
                        
                        if full_element:
                            if current_window._hWnd == full_element[0]:
                                try:
                                    winmove('up', current_window, 1)
                                except Exception as e:
                                    log.error(f"err={e}")

                    aw = self.open_windows
                if self.open_windows is not None and len(self.open_windows) > 0:
                    serialized_data = zlib.compress(json.dumps(self.open_windows).encode('utf-8',errors='replace'))
            # Формируем полный пакет: заголовок (4 байта) + данные
            packet = len(serialized_data).to_bytes(4, 'big') + serialized_data
            conn.sendall(packet)

    def run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('localhost', ports['get_win']))
            server_socket.listen(10)
            log.info("Server is listening on port ports['get_win']...")

            while True:
                try:
                    conn, addr = server_socket.accept()
                    Thread(target=self.handle_client, args=(conn, addr)).start()
                except Exception as e:
                    log.error(f"An error occurred accepting a new connection: {e}")

if __name__ == "__main__":
    window_server = WindowServer()
    window_server.run_server()
