import time
import socket
import json
from icecream import ic
from variable import *
from windows_controle import *
import mouse
import pygetwindow
import threading
import subprocess
ic.configureOutput(includeContext=True)
stop_event = threading.Event()
indexwin=0
active_win=[]

i=1
def run_command(hotkey):
    command=hot_key.get(hotkey)
    ic(command)
    if command:
        subprocess.run([command])
def handle_key_press(out):
    global i
    if out.get('status') == 'Up':
        valu=[]
        item=out.get('option')
        if ', 'in item:
            for key in item.split(', '):
                valu.append(key)
        else:
            valu.append(item)
        valu = list(dict.fromkeys(valu))
        ic(valu)
        w = pygetwindow.getActiveWindow()
        for value in valu:
            if value == 'left_win+delete':
                ic("close")
                if w is not None:
                    w.close()
            elif value in ['pause', 'left_shift+pause']:
                mouse.click('right')
            elif value == 'left_win+arrow_right':
                winmove('right',w,i)
            elif value == 'left_win+arrow_left':
                winmove('left',w,i)
            elif value == 'left_win+arrow_up':
                winmove('up',w,i)
            elif value == 'left_win+arrow_down':
                winmove('down',w,i)
            else:
                run_command(value)

def start_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect(('localhost', 65431))
        print("Connected to server. key")
        buffer = ""

        while True:
            # print(90)
            time.sleep(0.1)
            try:
                # Получаем данные
                data = client_socket.recv(1024).decode('utf-8', errors='replace')
                # ic(data)
                if not data:
                    continue
                    # break

                buffer += data  # Добавляем данные в буфер
                # Проверяем, есть ли полные сообщения (разделенные новой строкой)
                while '\n' in buffer:
                    message, buffer = buffer.split('\n', 1)  # Разделяем на первое сообщение и оставшуюся часть
                    try:
                        # Парсим JSON
                        handle_key_press(json.loads(message.strip()))  # Убираем пробелы вокруг
                    except json.JSONDecodeError as e:
                        print(f"JSON decoding error: {e} for message: {message.strip()}")
            
            except Exception as e:
                print(f"KeyMan An error occurred: {e}")
                # break

if __name__ == "__main__":
    start_client()
