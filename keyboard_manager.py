from socket_client import BaseSocketClient
from variable import *
from variable_def import *
import variable
import pygetwindow
import subprocess
import logger
import mouse
min_x,min_y,max_x,max_y = get_monitor()
width = max_x-min_x
height = max_y-min_y

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
    elif key == 'return' and status=='Down':subprocess.run([components['tools']['press'],'return'])

log=logger.setup_logging()

indexwin=0
active_win=[]
w=None
i=1
cur={}
ACTIONS=get_action()
def handle_key_press(out):
    log.info(out)
    global i, w, cur
    if out.get('isInjected') != 'Physical':
        return

    items = out.get('option', [])
    valu = {key for item in items for key in item.split(', ')}
    
    
    if out.get('numpan')=='NumPad' and out.get('blocked')=='Blocked':
        handle_numpad_mouse(out)
    elif out.get('status') == 'Up':
        for value in valu:
            if value in ACTIONS:
                w = pygetwindow.getActiveWindow()
                ACTIONS[value](w, i)
                break

            elif value == 'left_win' and cur and cur.get('option', [None])[0] == value:
                if cur.get('status') == 'Down':
                    subprocess.run([components['tools']['press'], 'left_win'])
                    break
            elif value=='insert' and out.get('numpan')!='NumPad':
                subprocess.run([components['tools']['press'], 'f2'])

    else:
        for value in valu:
            if value == 'left_win+space':
                log.info('Смена раскладки для всех окон...')
                tit = win_client.request()
                if tit:
                    hwnds = [win['hwnd'] for win in tit]
                    try:
                        current_id = out.get('layout', {}).get('HKL')
                        if current_id:
                            hkl_hex = get_next_layout_hkl(current_id)[0]
                            log.info(hkl_hex)
                            for hwnd in hwnds:
                                subprocess.run([components['tools']['layout'], f'{hwnd}', f'{hkl_hex}'], capture_output=True)
                    except Exception as e:
                        log.error(f'Ошибка смены раскладки: {e}')
                break

    cur = out


def start_client(stop_event): # <--- Принимаем stop_event
    global win_client
    log.info(variable.display)
    win_client = BaseSocketClient(ports['get_win'], "WinSpace-Switcher", stop_event, is_zlib=True)
    
    # 1. Создаем клиент
    client = BaseSocketClient(
        port=ports['get_key'], 
        name="KeyManager-Client",
        stop_event=stop_event
    )
    
    log.info("KeyManager: попытка подключения к серверу клавиш...")
    
    try:
        # 2. Передаем stop_event в основной цикл клиента
        # Предполагается, что в BaseSocketClient.run_loop добавлена проверка этого события
        client.run_loop(
            handler=handle_key_press,
            stop_event=stop_event 
        )
    except Exception as e:
        log.error(f"❌ Ошибка в KeyManager-Client: {e}")
    finally:
        # 3. Гарантированно закрываем соединение при выходе
        if hasattr(client, 'close'):
            client.close()
        log.info("🛑 Клиент KeyManager остановлен")

if __name__ == "__main__":
    start_client()
