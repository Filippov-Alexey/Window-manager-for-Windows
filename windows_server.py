from socket_server import BaseServer
from subprocess_server import BaseSubprocessServer
import pygetwindow
import psutil
import ujson
from variable import *
import variable
from windows_controle import *
from PIL import Image
import win32gui
import win32process
import win32api
import win32ui
import win32con
import logger
import win32com
log=logger.setup_logging()
aw = []
serialized_data = ''.encode()
import os
import win32gui
import win32ui
import win32con
from ctypes import Structure, windll, c_uint, sizeof, byref, c_void_p, wintypes
from PIL import Image

class SHFILEINFO(Structure):
    _fields_ = [
        ("hIcon", c_void_p),
        ("iIcon", c_uint),
        ("dwAttributes", c_uint),
        ("szDisplayName", wintypes.WCHAR * 260),
        ("szTypeName", wintypes.WCHAR * 80)
    ]

def extract_icon(path, index=0, size=32):
    path = os.path.expandvars(path)
    hicon = None
    
    try:
        shfileinfo = SHFILEINFO()
        flags = 0x100 | 0x10 | (0x0 if size > 16 else 0x1)
        
        ret = windll.shell32.SHGetFileInfoW(path, 0x80, byref(shfileinfo), sizeof(shfileinfo), flags)
        if shfileinfo.hIcon:
            hicon = shfileinfo.hIcon
    except Exception:
        pass

    if not hicon:
        try:
            large, small = win32gui.ExtractIconEx(path, index)
            if size <= 16 and small:
                hicon = small[0]
                if large: [win32gui.DestroyIcon(h) for h in large]
            elif large:
                hicon = large[0]
                if small: [win32gui.DestroyIcon(h) for h in small]
        except Exception:
            pass

    if not hicon:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))

    try:
        hdc_screen = win32gui.GetDC(0)
        hdc = win32ui.CreateDCFromHandle(hdc_screen)
        mem_dc = hdc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(hdc, size, size)
        mem_dc.SelectObject(bmp)

        win32gui.DrawIconEx(mem_dc.GetHandleOutput(), 0, 0, hicon, size, size, 0, None, 3)

        bmpinfo = bmp.GetInfo()
        bmpstr = bmp.GetBitmapBits(True)
        img = Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), 
                               bmpstr, 'raw', 'BGRA', 0, 1)
        return img
    finally:
        if hicon: win32gui.DestroyIcon(hicon)
        if 'mem_dc' in locals() and mem_dc: mem_dc.DeleteDC()
        if 'hdc' in locals() and hdc: hdc.DeleteDC()
        win32gui.ReleaseDC(0, hdc_screen)
   
def extract_icon_from_hicon(hicon_ptr, size=32):
    if not hicon_ptr:
        return Image.new("RGBA", (size, size), (0,0,0,0))
    
    hdc_screen = None
    try:
        hdc_screen = win32gui.GetDC(0)
        hdc = win32ui.CreateDCFromHandle(hdc_screen)
        mem_dc = hdc.CreateCompatibleDC()
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(hdc, size, size)
        mem_dc.SelectObject(bmp)

        win32gui.DrawIconEx(mem_dc.GetHandleOutput(), 0, 0, hicon_ptr, size, size, 0, None, 3)

        bmpinfo = bmp.GetInfo()
        bmpstr = bmp.GetBitmapBits(True)
        return Image.frombuffer('RGBA', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), 
                                bmpstr, 'raw', 'BGRA', 0, 1)
    except:
        return Image.new("RGBA", (size, size), (0,0,0,0))
    finally:
        if hdc_screen:
            if 'mem_dc' in locals(): mem_dc.DeleteDC()
            if 'hdc' in locals(): hdc.DeleteDC()
            win32gui.ReleaseDC(0, hdc_screen)
def force_activate(hwnd):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys('%') 
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW) 
        return True
    except Exception as e:
        log.error(f"Ошибка: {e}")
        return False



def bring_window_to_front(hwnd):
    if not win32gui.IsWindow(hwnd):
        return
    import ctypes
    user32 = ctypes.windll.user32
    
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

        fore_hwnd = win32gui.GetForegroundWindow()
        fore_thread = win32process.GetWindowThreadProcessId(fore_hwnd)[0]
        curr_thread = win32api.GetCurrentThreadId()
        if fore_thread != curr_thread:
            user32.AttachThreadInput(curr_thread, fore_thread, True)
        user32.AllowSetForegroundWindow(-1)
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
        win32gui.SetActiveWindow(hwnd)
        
        if fore_thread != curr_thread:
            user32.AttachThreadInput(curr_thread, fore_thread, False)
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, 
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, 
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)

    except Exception as e:
        win32gui.PostMessage(hwnd, win32con.WM_SYSCOMMAND, win32con.SC_RESTORE, 0)

lest_line = None
lest_hwnd = set()
import win32gui

lest_hwnd_info = {} 
def c_plus_plus_listener(stop_event):
    global lest_hwnd
    win_server = BaseServer(ports['get_win'], "WindowServer", is_json=True, is_zlib=True)

    class WindowProcessHandler(BaseSubprocessServer):
        def parse_line(self, line):
            global lest_hwnd
            line = line.strip()
            log.info(line)
            if not line.startswith('['): 
                return None
                
            win = pygetwindow.getActiveWindow()
            if not win: return None
            
            if not (line.startswith('[') and (not is_ignored(win.title) or win.title == TITLE or win.title == "Program Manager")):
                return None
            
            _, pid = win32process.GetWindowThreadProcessId(win._hWnd)
            path = psutil.Process(pid).exe().replace('\\','\\\\')
            
            if path in patterns_for_progs:
                return None

            try:
                data_obj = ujson.loads(line)
                if not data_obj: return None

                win_server.broadcast(data_obj)
                
                active_info = data_obj[0]
                current_hwnds = {item['hwnd'] for item in data_obj}
                
                added = current_hwnds - lest_hwnd
                removed = lest_hwnd - current_hwnds

                if added or removed:
                    log.info(f"🔄 Изменение окон: +{len(added)} / -{len(removed)}")
                    lest_hwnd = current_hwnds.copy()

                    first_path = active_info['path']
                    consecutive_windows = []
                    for item in data_obj:
                        if item['path'] == first_path:
                            consecutive_windows.append(item)
                        else:
                            break
                    
                    total_count = len(consecutive_windows)
                    mode = tile_mode
                    for i, win_data in enumerate(reversed(consecutive_windows)):
                        if self.stop_event.is_set(): 
                            break 
                            
                        try:
                            target_window = pygetwindow.Win32Window(win_data['hwnd'])
                            winmove(mode, target_window, i, total_count)
                        except Exception as e:
                            log.debug(f"Ошибка перемещения: {e}")

                if active_info.get('active') != 1 and not self.stop_event.is_set():
                    bring_window_to_front(active_info['hwnd'])

            except Exception as e:
                log.error(f"Ошибка в WindowProcessHandler: {e}")
            
            return None 

    handler = WindowProcessHandler(
        server_instance=win_server,
        cmd=[components['services']['getwin']],
        stop_event=stop_event,
        label="Слушатель окон"
    )
    handler.run()

if __name__ == "__main__":
    c_plus_plus_listener()
