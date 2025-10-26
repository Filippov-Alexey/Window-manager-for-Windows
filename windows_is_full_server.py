from ctypes import windll
import win32gui
import socket
from threading import Thread
import pygetwindow
from variable import *
user32 = windll.user32
user32.SetProcessDPIAware()  # опционально, заставляет функции возвращать реальные числа пикселей
full_screen_rect = (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))

def is_full_screen():
    try:
        hWnd = user32.GetForegroundWindow()
        rect = win32gui.GetWindowRect(hWnd)
        return int(rect == full_screen_rect)  # Возвращаем 1 (True) или 0 (False)
    except:
        return 0

class WindowServer:
    def __init__(self):
        self.clients = []
        self.current_window_attributes = None

    def handle_client(self, conn, addr):
        """Обработчик для каждого клиента."""
        self.clients.append(conn)

        try:
            t=pygetwindow.getActiveWindowTitle()
            if t!="pop" and not t in patterns:
                screen_status = is_full_screen()
            else:
                screen_status=0
            conn.sendall(str(screen_status).encode('utf-8'))  # Конвертируем в байты и отправляем
        except (ConnectionResetError, BrokenPipeError):
            print(f"Connection lost with {addr}.")
        except Exception as e:
            print(f"WIFS 1 An error occurred with client {addr}: {e}")
        finally:
            self.clients.remove(conn)

    def run_server(self):
        """Основная функция сервера."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('localhost', 65433))
            server_socket.listen(5)
            print("Server is listening on port 65433...")

            while True:
                try:
                    conn, addr = server_socket.accept()
                    Thread(target=self.handle_client, args=(conn, addr)).start()
                except Exception as e:
                    print(f"WIFS 2 An error occurred accepting a new connection: {e}")

if __name__ == "__main__":  # Исправлено для правильного определения
    window_server = WindowServer()
    window_server.run_server()
