import re
from variable import ports, tools
import socket
import json
import subprocess
import time
import datetime
from threading import Thread, Event
import logger
log=logger.setup_logging()

stop_event = Event()
clients = []

def handle_client(conn, addr):
    """Обработчик для каждого клиента."""
    clients.append(conn)
    try:
        while True:
            time.sleep(1)
    except (ConnectionResetError, BrokenPipeError):
        log.error(f"Connection lost with {addr}.")
    except Exception as e:
        log.error(f"Error with client {addr}: {e}")
    finally:
        clients.remove(conn)
        log.error(f"Connection with {addr} closed.")

def run_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('localhost', ports['get_key']))
        server_socket.listen(10)
        log.info("Server is listening on port ports['get_key']...")

        while True:
            try:
                conn, addr = server_socket.accept()
                log.error(f"Accepted connection from {addr}")
                Thread(target=handle_client, args=(conn, addr)).start()
            except Exception as e:
                log.error(f"Error accepting a new connection: {e}")

def send_updates(message):
    if clients and message:
        for conn in list(clients):
            try:
                conn.sendall(f'{len(message.encode('utf-8'))}\n'.encode())
                conn.sendall(message.encode('utf-8'))
            except Exception as e:
                clients.remove(conn)
                log.error(f"KS_Could not send message to client: {e}")

def parse_broken_layout(raw_string):
    raw_string = raw_string.replace('\n', '')
    if '"layout":' in raw_string and not re.search(r'"layout":\s*\{', raw_string):
        raw_string = re.sub(r'("layout":\s*)(.*?)(\s*})$', r'\1{\2}\3', raw_string)

    try:
        return json.loads(raw_string)
    except json.JSONDecodeError:
        raw_string = raw_string.replace('"', '\\"')
        try:
            return json.loads(raw_string)
        except Exception as e:
            return f"Error: {e}"

def run_mouse_and_read_output():
    process = subprocess.Popen(
        ["cmd.exe","/c",tools["blocking"],'alt+arrow_left', 'pause', 'left_win', 'left_shift+pause', 'insert'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )
    with open('log.txt','+a')as f:
        f.write(f'{datetime.datetime.now()}=>start\n')
        # subprocess.run(['press','l'])

    try:
        while not stop_event.is_set():
            output = process.stdout.readline()
            if output:
                # ic(output)
                try:
                    message = parse_broken_layout(output)
                except Exception as e:
                    log.error('keyser',e)
                    process.kill()
                    process.terminate()
                    # return
                    continue
                # ic(output)
                send_updates(json.dumps(message)+"\n")
            # time.sleep(0.1)
    except KeyboardInterrupt:
        stop_event.set()
        log.info("Stopping...")
    finally:
        return_code = process.wait()
        process.kill()
        log.info(f'Process exited with code: {return_code}')

if __name__ == "__main__":
    Thread(target=run_server).start()
    while True:
        run_mouse_and_read_output()
