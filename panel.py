from ctypes import windll
from tkinter import Tk, Canvas
from variable import *
import os
import importlib.util
import time
import subprocess
import logger
import socket
import threading
log=logger.setup_logging()
log.info('run')
log.info(os.getpid())
def load_plugins():
    plugins = []
    for root, dirs, files in os.walk(plugins_dir):
        if root!='__pycache__':
            for file in files:
                if root[8:]==file[:-3] and file.endswith(".py"):
                    path = os.path.join(root, file)
                    spec = importlib.util.spec_from_file_location(file[:-3], path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    plugins.append(module)
    return plugins

def draw_rounded_rectangle(canvas, x1, y1, x2, y2, radius, **kwargs):
    if radius > (x2 - x1) / 2:
        radius = (x2 - x1) / 2
    if radius > (y2 - y1) / 2:
        radius = (y2 - y1) / 2

    arc = radius * 2
    points = [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2 - radius,
        x1, y1 + radius,
    ]
    polygon_id = canvas.create_polygon(points, **kwargs, smooth=True)
    canvas.addtag_withtag("icon", polygon_id)

    arc1_id = canvas.create_arc(x1, y1, x1 + arc, y1 + arc, start=90, extent=90, style='pieslice', **kwargs)
    canvas.addtag_withtag("icon", arc1_id)

    arc2_id = canvas.create_arc(x2 - arc, y1, x2, y1 + arc, start=0, extent=90, style='pieslice', **kwargs)
    canvas.addtag_withtag("icon", arc2_id)

    arc3_id = canvas.create_arc(x2 - arc, y2 - arc, x2, y2, start=270, extent=90, style='pieslice', **kwargs)
    canvas.addtag_withtag("icon", arc3_id)

    arc4_id = canvas.create_arc(x1, y2 - arc, x1 + arc, y2, start=180, extent=90, style='pieslice', **kwargs)
    canvas.addtag_withtag("icon", arc4_id)
x=1000
def status(canvas,height,color):
    draw_rounded_rectangle(canvas, x+225,0,x+280,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+285,0,x+350,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+360,0,x+443,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+447,0,x+535,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+540,0,x+650,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+658,0,x+730,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+735,0,x+770,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+780,0,x+915,height,5,fill=color)
def shortcut(canvas,height,color):
    draw_rounded_rectangle(canvas, 1115,0,1160,height,5,fill=color)
    draw_rounded_rectangle(canvas, 1040,0,1100,height,5,fill=color)
    draw_rounded_rectangle(canvas, 830,0,1010,height,5,fill=color)
    draw_rounded_rectangle(canvas, 550,0,800,height,5,fill=color)
    draw_rounded_rectangle(canvas, 450,0,510,height,5,fill=color)
def send_updates(message, clients):
    if clients and message:
        for conn in list(clients):
            try:
                conn.sendall(message.encode('utf-8'))
            except Exception as e:
                clients.remove(conn)
                log.error(f"Could_panel not send message to client: {e}")
clients = []
from datetime import datetime
def handle_client(conn, addr, root):
    """Обработчик для каждого клиента."""
    clients.append(conn)
    try:
        while True:
            send_updates(f't={datetime.now()}-{root.winfo_exists()}',clients)
            time.sleep(1)
    except Exception as e:
        log.error(e)
    finally:
        clients.remove(conn)

def set_taskbar_visible(visible=True):
    cmd = 5 if visible else 0  # 5 - показать (SW_SHOW), 0 - скрыть (SW_HIDE)
    
    # 1. Основная панель задач
    h_tray = windll.user32.FindWindowA(b'Shell_TrayWnd', None)
    if h_tray:
        windll.user32.ShowWindow(h_tray, cmd)

    # 2. Дополнительные панели задач (на других мониторах)
    # Ищем все окна с классом 'Shell_SecondaryTrayWnd'
    h_secondary = windll.user32.FindWindowExA(0, 0, b'Shell_SecondaryTrayWnd', None)
    while h_secondary:
        windll.user32.ShowWindow(h_secondary, cmd)
        # Ищем следующую вторичную панель, если мониторов больше двух
        h_secondary = windll.user32.FindWindowExA(0, h_secondary, b'Shell_SecondaryTrayWnd', None)


# Создаем сокет заранее (вне функции, чтобы не плодить подключения)
import queue
data_queue = queue.Queue()

class State:
    last_tk_tick = time.time()

state = State()

def run_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('127.0.0.1', 65438))
        server_socket.listen(5)
        time.sleep(5)
        while True:
            time.sleep(0.7)
            # 1. Проверяем, не «протух» ли GUI (допустим, задержка > 1 сек)
            if time.time() - state.last_tk_tick > 1.0:
                try:
                    conn, addr = server_socket.accept()
                    with conn:
                        
                        # Логика отправки
                        message = 'err\n'
                        payload = message.encode('utf-8')
                        conn.sendall(f'{len(payload)}\n'.encode())
                        conn.sendall(payload)
                except Exception as e:
                    log.error(f"Ошибка: {e}")
            else:            
                try:
                    conn, addr = server_socket.accept()
                    with conn:
                        
                        # Логика отправки
                        if not data_queue.empty():
                            msg = data_queue.get_nowait()
                            payload = msg.encode('utf-8')
                            conn.sendall(f'{len(payload)}\n'.encode())
                            conn.sendall(payload)
                        # Ваша логика отправки...
                except socket.timeout:
                    # Если никто не подключился, просто идем на следующий круг While
                    continue 
                except Exception as e:
                    log.error(f"Ошибка: {e}")

def update(canvas):
    try:
        # Обновляем метку времени — "я жив"
        state.last_tk_tick = time.time()
        
        data_queue.put('ok\n')
        
        canvas.after(500, lambda: update(canvas))
    except Exception as e:
        log.error(f'err-{e}')

threading.Thread(target=run_server, daemon=True).start()

def main():

    root = Tk()
    # root.title("pop")
    root.title(TITLE)

    # 1. Считаем общие габариты всех мониторов
    monitors = get_monitors()
    min_x = min(m.x for m in monitors)
    min_y = min(m.y for m in monitors)
    max_x = max(m.x + m.width for m in monitors)
    max_y = max(m.y + m.height for m in monitors)

    full_width = max_x - min_x
    full_height = max_y - min_y

    # 2. Настраиваем окно
    # Формат geometry: "ШиринаxВысота+СмещениеX+СмещениеY"
    root.geometry(f"{full_width}x{full_height}+{min_x}+{min_y}")

    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.attributes("-transparentcolor", "#45765a")

    # 3. Создаем канвас на всю площадь
    canvas = Canvas(root, width=full_width, height=full_height, bg='#45765a', highlightthickness=0)
    canvas.pack()

    # Скрыть всё
    set_taskbar_visible(False)
    color="#220294" 
    bar=canvas.create_rectangle(0, 0, 400, RECT, fill=color, outline='')
    canvas.addtag_withtag("icon", bar)
    status(canvas,RECT,color)
    shortcut(canvas,RECT,color)
    k=0

    p=load_plugins()
    for i, module in enumerate(p):
        class_name = module.__name__.split('.')[-1]
        root.after(100 * (i + 1), lambda m=module, cn=class_name: getattr(m, cn)(canvas, root, RECT, extension[0]).run())
        k=i
    root.after(100*(k+1),lambda: subprocess.run([tools['press'],'packet']))
    root.after(100*(k+2),lambda: update(canvas))
    root.mainloop()
if __name__=="__main__":
    main()
