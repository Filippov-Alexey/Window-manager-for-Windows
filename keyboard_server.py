from icecream import ic
import ast
import socket
import json
import subprocess
import time
from threading import Thread
import threading

serialized_data = ''
stop_event = threading.Event()

class WindowServer:
    def __init__(self):
        self.clients = []
        self.current_window_attributes = None

    def handle_client(self, conn, addr):
        """Обработчик для каждого клиента."""
        self.clients.append(conn)
        try:
            while True:                
                # Держим соединение открытым, чтобы отправлять данные когда они будут.
                time.sleep(1)
        except (ConnectionResetError, BrokenPipeError):
            print(f"Connection lost with {addr}.")
        except Exception as e:
            print(f"1 keyser An error occurred with client {addr}: {e}")
        finally:
            print("rrrrrrr")
            self.clients.remove(conn)

    def run_server(self):
        """Основная функция сервера."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind(('localhost', 65431))
            server_socket.listen(5)
            print("Server is listening on port 65431...")

            while True:
                try:
                    conn, addr = server_socket.accept()
                    print(f"Accepted connection from {addr}")
                    Thread(target=self.handle_client, args=(conn, addr)).start()
                except Exception as e:
                    print(f"2 keyser An error occurred accepting a new connection: {e}")

    def send_updates(self, message):
        """Отправляет сообщения всем подключенным клиентам."""
        # print(message)
        if self.clients and len(message)>0:
            for conn in self.clients:
                try:
                    conn.sendall(message.encode('utf-8'))
                except Exception as e:
                    self.clients.remove(conn)
                    print(f"Could not send message to client: {e}")

def run_mouse():
    process = subprocess.Popen(
        ["blocking.exe", 'pause', 'left_shift+pause', 'left_win+delete', 'left_win+arrow_left', 'left_win+arrow_right', 'left_win+arrow_up', 'left_win+arrow_down'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    output_thread = threading.Thread(target=output_reader, args=(process.stdout,))
    output_thread.start()

    try:
        while True:  
            time.sleep(0.1) 
    except KeyboardInterrupt:
        stop_event.set() 
        ic("Stopping...")
    finally:
        stop_event.set() 
        output_thread.join()  
        return_code = process.wait()  
        ic(f'Process exited with code: {return_code}')

def output_reader(stdout):
    while not stop_event.is_set():
        output = stdout.readline()
        if len(output) > 0:
            output = output.strip()
            message = json.dumps(ast.literal_eval(output)) + '\n'  # Добавляем разделитель
            window_server.send_updates(message)

if __name__ == "__main__":
    window_server = WindowServer()
    Thread(target=window_server.run_server).start()  # Запуск сервера
    run_mouse()  # Запуск run_mouse
