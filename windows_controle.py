from icecream import ic
from variable import *
import pygetwindow
import threading
import subprocess
import time
ic.configureOutput(includeContext=True)
stop_event = threading.Event()
indexwin=0
active_win=[]
def keywork(stdout):
    while not stop_event.is_set():  
        output = stdout.readline().encode('cp1251').decode()
        ic(output)
        if not output: 
            break
        output = output.strip()
        if output:
            try:
                result_data = output.split(': ')[1]
                handle_key_press(result_data)
            except Exception as e:
                ic(f"Error processing output: {e}\t{output}")
def set_window_position(w, wp):
    left=wp[0] 
    top=wp[1]
    right=wp[2]
    bottom=wp[3]
    width = right - left
    height = bottom - top
    w.resizeTo(width, height)
    w.moveTo(left, top)      
def getindexwin(windows):
    if windows is not None:
        ic(windows.left,windows.top,windows.width,windows.height)
        centerx=windows.left+windows.width//2 
        centery=windows.top+windows.height//2
        for index,coord in winpos[1].items():
            if coord[0]<centerx<coord[2] and coord[1]<centery<coord[3]:
                ic(index)
                return index
    return None
def winmove(directions, w, i):
    indexwin = getindexwin(w)
    ic(directions)
    if indexwin is not None:
        if directions == 'up':
            w.maximize()
        elif directions == 'down':
            w.minimize()
        elif directions=='right':
            indexwin+=1
            if indexwin>2:
                indexwin=0
            set_window_position(w,winpos[i][indexwin])
        elif directions=='left':
            indexwin-=1
            if indexwin<0:
                indexwin=2
            set_window_position(w,winpos[i][indexwin])
        ic(indexwin)

def handle_key_press(out):
    title=out.split(', ')[3][6:]
    status=int(out.split(', ')[1][4:])
    w=pygetwindow.getWindowsWithTitle(title)[0]
    if status==3:
        set_window_position(w, winpos['max'])
        print('расскрыть')
def runmouse():
    process = subprocess.Popen(
        ["win.exe"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    output_thread = threading.Thread(target=keywork, args=(process.stdout,))
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
        ic(f'Процесс завершился с кодом: {return_code}')
if __name__ == "__main__":
    runmouse()