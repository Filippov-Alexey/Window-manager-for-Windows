from variable import *
from windows_controle import *
import pygetwindow
import threading
import subprocess
import socket
import logger
log=logger.setup_logging()

stop_event = threading.Event()
indexwin=0
active_win=[]
w=None
i=1
cur={}

def handle_key_press(out):
    global i, w, event, cur
    
    if out.get('isInjected') != 'Physical':
        return

    items = out.get('option', [])
    valu = {key for item in items for key in item.split(', ')}
    
    w = pygetwindow.getActiveWindow()
    log.info(out)
    
    if w and w.title != TITLE:
        if out.get('status') == 'Up':
            for value in valu:
                if value in ACTIONS:
                    ACTIONS[value](w, i)
                    break

                elif value == 'left_win' and cur and cur.get('option', [None])[0] == value:
                    if cur.get('status') == 'Down':
                        subprocess.run(['press', 'left_win'])
                        break
        else:
            for value in valu:
                if value == 'left_win+space':
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                        client_socket.connect(('localhost', ports['get_win']))
                        m = client_socket.recv(4).decode('utf-8', errors='replace')
                        data = client_socket.recv(int(m))
        
                        open_windows = zlib.decompress(data).decode('utf-8')
                        tit = json.loads(open_windows)
                        rects = [w[0] for w in tit] if tit else []
                        current_id = out.get('layout')['ID']  # Ваше значение '0x0422'
                        hkl_hex=get_next_layout_hkl(current_id)
                        for hwnd in rects:
                            subprocess.run(['layout.exe',f'{hwnd}',f'{hkl_hex}'])
                    break

    cur = out

def start_client():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect(('localhost', ports['get_key']))
        log.info("Connected to server. key")

        while True:
            try:
                m = client_socket.recv(4).decode('utf-8', errors='replace')
                message = client_socket.recv(int(m)).decode('utf-8', errors='replace')
                handle_key_press(json.loads(message))
            
            except Exception as e:
                log.error(f"KeyMan An error occurred: {e}")

if __name__ == "__main__":
    start_client()
