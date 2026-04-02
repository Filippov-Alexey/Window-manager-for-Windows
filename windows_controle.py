import zlib
import pygetwindow
import threading
import subprocess
import time
import socket
import json
import variable
import logger

log=logger.setup_logging()

stop_event = threading.Event()
indexwin=0
active_win=[]
def keywork(stdout):
    while not stop_event.is_set():  
        output = stdout.readline()
        if not output: 
            break
        output = output.strip()
        if output:
            try:
                result_data = output.split(': ')[1]
                handle_key_press(result_data)
            except Exception as e:
                log.info(f"Error processing output: {e}\t{output}")
def set_window_position(w, wp):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5.0)  # Защита от зависания
        s.connect(('localhost', variable.ports['get_win']))
        raw_header = s.recv(4)
        data_len = int.from_bytes(raw_header, 'big')
        data = s.recv(data_len)
    open_windows = zlib.decompress(data).decode('utf-8')
                
    tit = json.loads(open_windows)
    pid, title, path, coordinates = tit[0]
    if not title in variable.patterns:
        size = variable.win_size.get(path, None)
        if not size is None:
                left=wp[0]+size[0]
                top=wp[1]+size[1]
                right=wp[2]+size[2]
                bottom=wp[3]+size[3]
        else:
            left=wp[0] 
            top=wp[1]
            right=wp[2]
            bottom=wp[3]
        width = right - left
        height = bottom - top
        if w.isMaximized:
            w.restore()
        w.moveTo(left, top)      
        w.resizeTo(width, height)
    
def getindexwin(windows):
    if windows is not None:
        centerx=windows.left+windows.width//2 
        centery=windows.top+windows.height//2
        for index,coord in variable.winpos[1].items():
            if coord[0]<centerx<coord[2] and coord[1]<centery<coord[3]:
                return index
    return None
def winmove(directions, w, i):
    if w and w.title != variable.TITLE:
        indexwin = getindexwin(w)
        if directions == 'up':
            w.maximize()
        elif directions == 'down':
            w.minimize()
        elif directions=='right':
            indexwin+=1
            if indexwin>2:
                indexwin=0
            set_window_position(w,variable.winpos[i][indexwin])
        elif directions=='left':
            indexwin-=1
            if indexwin<0:
                indexwin=2
            set_window_position(w,variable.winpos[i][indexwin])

def handle_key_press(out):
    title=out.split(', ')[3][6:]
    status=int(out.split(', ')[1][4:])
    w=pygetwindow.getWindowsWithTitle(title)[0]
    if status==3:
        set_window_position(w, variable.winpos['max'])

def run_and_check():
    while True:
        process = subprocess.Popen(
            [variable.tools["win"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
        
        # Даем время на запуск
        time.sleep(2)
        
        # Если poll() возвращает None, значит процесс ЖИВ
        if process.poll() is None:
            log.error("Процесс стабилен, выходим из цикла.")
            return process  # Выход из функции и цикла
        
        # Если мы здесь, значит процесс умер
        log.info("Процесс упал. Пробуем еще раз через секунду...")
        time.sleep(1) 
def runmouse():
    process=run_and_check()
    output_thread = threading.Thread(target=keywork, args=(process.stdout,))
    output_thread.start()
    try:
        while True:  
            time.sleep(0.1) 
    except KeyboardInterrupt:
        stop_event.set() 
        log.info("Stopping...")
    finally:
        stop_event.set() 
        output_thread.join()  
        return_code = process.wait()  
        
if __name__ == "__main__":
    runmouse()