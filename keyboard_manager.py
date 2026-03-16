from variable import *
from windows_controle import *
import pygetwindow
import threading
import subprocess
import socket
import logger
import mouse
width,height=extension
directions = {
    'home': (-1, -1), 'arrow_up': (0, -1), 'page_up': (1, -1),
    'arrow_left': (-1, 0),                 'arrow_right': (1, 0),
    'end': (-1, 1),  'arrow_down': (0, 1), 'page_down': (1, 1),
}

MIN_SPEED = 1       
MAX_SPEED = 100     
ACCEL_TIME_MS = 4000

current_button = 'left'
w_step = width // 3
h_step = height // 3

grid_map = {
    'home': (0, 0), 'arrow_up': (1, 0), 'page_up': (2, 0),
    'arrow_left': (0, 1), 'clear': (1, 1), 'arrow_right': (2, 1),
    'end': (0, 2), 'arrow_down': (1, 2), 'page_down': (2, 2)
}

def handle_numpad_mouse(out):
    global current_button
    key = out.get('key_name')
    items = out.get('option', [])
    status = out.get('status')

    for d_key in grid_map:
        if f'alt+{d_key}' in items:
            col, row = grid_map[d_key]
            center_x = col * w_step + w_step // 2
            center_y = row * h_step + h_step // 2
            mouse.move(center_x, center_y, absolute=True)
            return

    try:
        duration = int(out.get('duretion', 500))
        progress = min(1.0, max(0, (duration - 500) / ACCEL_TIME_MS))
    except:
        progress = 0

    speed = MIN_SPEED + (MAX_SPEED - MIN_SPEED) * progress

    if key in directions:
        dx, dy = directions[key]
        mouse.move(int(dx * speed), int(dy * speed), absolute=False)

    elif key == 'numpad_/': current_button = 'left'
    elif key == 'numpad_*': current_button = 'right'
    elif key == 'clear' and status=='Up':
        mouse.click(button=current_button)
    elif key == 'numpad_+' and status=='Up': mouse.double_click(button=current_button)
    elif key == 'insert': 
        if not mouse.is_pressed(current_button): mouse.press(current_button)
    elif key == 'delete': mouse.release(current_button)
    elif key == 'return' and status=='Down':subprocess.run([tools['press'],'return'])

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
    # log.info(out)
    
    # if w and w.title != TITLE:
    if out.get('numpan')=='NumPad' and out.get('blocked')=='Blocked':
        handle_numpad_mouse(out)
    elif out.get('status') == 'Up':
        for value in valu:
            if value in ACTIONS:
                ACTIONS[value](w, i)
                break

            elif value == 'left_win' and cur and cur.get('option', [None])[0] == value:
                if cur.get('status') == 'Down':
                    subprocess.run([tools['press'], 'left_win'])
                    break
            elif value=='insert' and out.get('numpan')!='NumPad':
                subprocess.run([tools['press'], 'f2'])

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
                    try:
                        current_id = out.get('layout')['HKL']  # Ваше значение '0x0422'
                        hkl_hex=get_next_layout_hkl(current_id)[0]
                        for hwnd in rects:
                            subprocess.run([tools['layout'],f'{hwnd}',f'{hkl_hex}'])
                    except Exception as e:
                        log.error(f'kl{e}')
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
