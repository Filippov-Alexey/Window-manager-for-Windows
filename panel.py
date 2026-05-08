from ctypes import windll
from tkinter import Tk, Canvas
from variable_def import *
from manager import win_manager
import os
import importlib.util
import time
import subprocess
import variable
import logger

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
    draw_rounded_rectangle(canvas, x+195,0,x+215,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+225,0,x+280,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+285,0,x+350,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+360,0,x+443,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+447,0,x+535,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+540,0,x+650,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+658,0,x+730,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+735,0,x+770,height,5,fill=color)
    draw_rounded_rectangle(canvas, x+780,0,x+915,height,5,fill=color)
def shortcut(canvas,height,color):
    draw_rounded_rectangle(canvas, 1165,0,1190,height,5,fill=color)
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
    cmd = 5 if visible else 0  
    h_tray = windll.user32.FindWindowA(b'Shell_TrayWnd', None)
    if h_tray:
        windll.user32.ShowWindow(h_tray, cmd)
    h_secondary = windll.user32.FindWindowExA(0, 0, b'Shell_SecondaryTrayWnd', None)
    while h_secondary:
        windll.user32.ShowWindow(h_secondary, cmd)
        h_secondary = windll.user32.FindWindowExA(0, h_secondary, b'Shell_SecondaryTrayWnd', None)


import queue
data_queue = queue.Queue() 

class State:
    last_tk_tick = time.time()

state = State()

icons_visible = None 
ow = None

ow = None
icons_visible = True

def update_ui_state(canvas,should_be_visible):
    global icons_visible
    if should_be_visible != icons_visible:
        new_state = 'normal' if should_be_visible else 'hidden'
        canvas.itemconfigure("icon", state=new_state)
        icons_visible = should_be_visible

def process_windows_data(new_data):
    global ow,canvas
    
    try:
        if new_data is None or new_data == ow:
            return
            
        ow = new_data
        
       
        if ow and isinstance(ow, list):
            should_be_visible = (ow[0].get('full') == 0)
            
            canvas.after(0, lambda: update_ui_state(canvas,should_be_visible))
            
    except Exception as e:
        log.error(f"Data processing error: {e}")

def main_func(stop_event): 
    log.info(variable.display)
    global canvas 
    root = Tk()
    root.title(TITLE)

    min_x, min_y, max_x, max_y = get_monitor()
    full_width = max_x - min_x
    full_height = max_y - min_y

    root.geometry(f"{full_width}x{full_height}+{min_x}+{min_y}")
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    root.attributes("-transparentcolor", "#45765a")
    canvas = Canvas(root, width=full_width, height=full_height, bg='#45765a', highlightthickness=0)
    canvas.pack()

    def check_stop():
        log.error('work')
        if stop_event.is_set():
            log.info("👋 Получен сигнал остановки Tkinter. Закрываю окно...")
            root.destroy()
        else:
            root.after(500, check_stop)
    win_manager.subscribe(process_windows_data)

    set_taskbar_visible(False)
    color = "#220294" 
    bar = canvas.create_rectangle(0, 0, 400, RECT, fill=color, outline='')
    canvas.addtag_withtag("icon", bar)
    
    status(canvas, RECT, color)
    shortcut(canvas, RECT, color)

    plugins = load_plugins()
    k = 0
    for i, module in enumerate(plugins):
        class_name = module.__name__.split('.')[-1]
        root.after(100 * (i + 1), lambda m=module, cn=class_name: getattr(m, cn)(canvas, root, RECT, full_width, stop_event).run())
        k = i

    root.after(100 * (k + 1), lambda: subprocess.run([components['tools']['press'], 'packet']))
    root.after(100 * (k + 2), lambda: process_windows_data(data_queue))


    root.mainloop()
if __name__ == "__main__":
    main_func()
