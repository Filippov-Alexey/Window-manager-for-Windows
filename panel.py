from ctypes import windll
from tkinter import Tk, Canvas
from variable import *
import os
import importlib.util
import time
import subprocess
import logger
log=logger.setup_logging()
log.info('run')
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
def status(canvas,height,color):
    draw_rounded_rectangle(canvas, 1192,0,1243,height,5,fill=color)
    draw_rounded_rectangle(canvas, 1250,0,1315,height,5,fill=color)
    draw_rounded_rectangle(canvas, 1320,0,1405,height,5,fill=color)
    draw_rounded_rectangle(canvas, 1412,0,1490,height,5,fill=color)
    draw_rounded_rectangle(canvas, 1503,0,1652,height,5,fill=color)
    draw_rounded_rectangle(canvas, 1658,0,1725,height,5,fill=color)
    draw_rounded_rectangle(canvas, 1735,0,1770,height,5,fill=color)
    draw_rounded_rectangle(canvas, 1780,0,1915,height,5,fill=color)
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

def main():
    # Создаем главное окно
    root = Tk()
    root.title(TITLE)
    root.attributes('-fullscreen', True)  # Полноэкранный режим
    root.resizable(False, False)  # Отключаем изменение размера окна
    root.overrideredirect(True)
    root.wm_attributes('-topmost', True)  # Сделать окно поверх других
    root.wm_overrideredirect(True)  # Скрыть заголовок окна
    root.wm_attributes("-transparentcolor", "#45765a")  # Прозрачный цвет

    # Создание канваса
    canvas = Canvas(root, width=w, height=h, bg='#45765a', highlightthickness=0)
    canvas.pack()

    # Скрываем панель задач
    h_tray = windll.user32.FindWindowA(b'Shell_TrayWnd', None)
    windll.user32.ShowWindow(h_tray, 0)

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
    root.after(100*(k+1),lambda: subprocess.run(['press','l']))
    root.mainloop()
if __name__=="__main__":
    main()
