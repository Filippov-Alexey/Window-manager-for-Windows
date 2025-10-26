import socket
import json
import pygetwindow
from threading import Thread
from update_icons import get_executable_paths_with_open_windows
from variable import *
from windows_controle import *

aw = []
serialized_data = ''

class WindowServer:
    def __init__(self):
        self.clients = []
        self.open_windows = []
        self.current_window_attributes = None

    def handle_client(self, conn, addr):
        global serialized_data, aw
        self.clients.append(conn)

        current_window = pygetwindow.getActiveWindow()
        if current_window!="pop" and not current_window in patterns:

            if new_win_open_max and current_window is not None and current_window.isMaximized:
                current_window.restore()
                set_window_position(current_window, winpos['max'])
                
            if current_window is not None:
                self.current_attributes = {
                    'title': current_window.title,
                    'left': current_window.left,
                    'top': current_window.top,
                    'width': current_window.width,
                    'height': current_window.height,
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
                                        winmove('right', current_window, 1)
                                    except Exception as e:
                                        print(f"err={e}")

                        aw = self.open_windows
                    if self.open_windows is not None and len(self.open_windows) > 0:
                        serialized_data = json.dumps(self.open_windows).encode('utf-8')

            conn.sendall(serialized_data)  

        self.clients.remove(conn)

    def run_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('localhost', 65432))
            server_socket.listen(5)
            print("Server is listening on port 65432...")

            while True:
                # print('ws')
                try:
                    conn, addr = server_socket.accept()
                    # print(f"Connection established with {addr}")
                    Thread(target=self.handle_client, args=(conn, addr)).start()
                except Exception as e:
                    print(f"An error occurred accepting a new connection: {e}")

if __name__ == "__main__":
    window_server = WindowServer()
    window_server.run_server()
