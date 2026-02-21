from plugins.update_icons.variable import *
from variable import *
from PIL import Image, ImageTk
import zlib
import socket
import json
import win32gui
import win32process
import pygetwindow as gw
import win32api
import win32ui
import win32con
import re
import logger
log=logger.setup_logging()

def check_window_exists(window_id):
    try:
        window = gw.Window(window_id)
        if window.title!='':
            return True
        return False
    except gw.PyGetWindowException:
        return False

def is_window_valid(hwnd):
    return win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd)

def bring_window_to_front(hwnd):
    try:
        if not win32gui.IsWindow(hwnd):
            return
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

        try:
            win32gui.SetForegroundWindow(hwnd)
        except Exception as e:
            fg = win32gui.GetForegroundWindow()
            if fg:
                cur_thread = win32api.GetCurrentThreadId()
                fg_thread = win32process.GetWindowThreadProcessId(fg)[0]
                try:
                    win32process.AttachThreadInput(cur_thread, fg_thread, True)
                    win32gui.SetForegroundWindow(hwnd)
                finally:
                    win32process.AttachThreadInput(cur_thread, fg_thread, False)

        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0,0,0,0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0,0,0,0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    except Exception as ex:
        log.error('Error bringing window to front:', ex)

def on_icon_click_factory(hwnd):

    def handler(event, _hwnd=hwnd):
        bring_window_to_front(_hwnd)
        
    return handler
def extract_icon_from_exe(path, index=0, size=2 , save_to=None):
    large, small = win32gui.ExtractIconEx(path, index)
    hicon = None
    
    if size <= 32 and small:
        hicon = small[0]
    elif large:
        hicon = large[0]
    elif small:
        hicon = small[0]

    if not hicon:
        raise FileNotFoundError("Icon not found in: " + path)

    hdc_screen = win32gui.GetDC(0)
    hdc = win32ui.CreateDCFromHandle(hdc_screen)
    mem_dc = hdc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(hdc, size, size)

    mem_dc.SelectObject(bmp)
    win32gui.DrawIconEx(mem_dc.GetHandleOutput(), 0, 0, hicon, size, size, 0, None, win32con.DI_NORMAL)

    bmpinfo = bmp.GetInfo()
    bmpstr = bmp.GetBitmapBits(True)
    
    img = Image.frombuffer(
        'RGBA',
        (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
        bmpstr, 'raw', 'BGRA', 0, 1
    )

    if save_to:
        img.save(save_to)

    win32gui.DestroyIcon(hicon)
    mem_dc.DeleteDC()
    hdc.DeleteDC()
    win32gui.ReleaseDC(0, hdc_screen)

    return img

at=None
class update_icons:
    def __init__(self, canvas, root, RECT_HEIGHT,w):
         self.canvas=canvas
         self.root=root
         self.w=w
    def run(self):
        global at
        def sanitize_filename(title):
            return re.sub(r'[\/:*?"<>|]', '_', title)
        open_windows=[]
        a=gw.getActiveWindow()
        if a!=at:
            at=a 
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                client_socket.connect(('localhost', ports['get_win']))
                m = client_socket.recv(4).decode('utf-8', errors='replace')
                data = client_socket.recv(int(m))
  
                open_windows = zlib.decompress(data).decode('utf-8')
                open_windows=json.loads(open_windows)
                client_socket.close()
            except Exception as e:
                log.error(f"UI An error occurred: {e}")

            current_files = set()
            visible_hwnds = []
            try:
                for hwnd, title, exe, coor in open_windows:
                    safe = sanitize_filename(title) or "untitled"
                    filename = f"{safe}_{hwnd}.png"
                    dst = icons_dir / filename
                    current_files.add(str(dst))
                    visible_hwnds.append((hwnd, title, exe, dst))

                for f in icons_dir.iterdir():
                    if f.is_file() and str(f) not in current_files:
                        try:
                            f.unlink()
                        except Exception:
                            pass
                new_canvas_hwnds = set()
                x,y=get_start_xy(orientation)

                for hwnd, title, exe, dst in visible_hwnds:
                    try:
                        # Проверяем, существует ли файл иконки, и если нет, пытаемся создать его
                        if not dst.exists():
                            try:
                                img = extract_icon_from_exe(exe, size=ICON_SIZE)
                                if hasattr(img, "thumbnail"):
                                    img = img.convert("RGBA")
                                    img.thumbnail((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
                                    img.save(str(dst), format="PNG")
                            except Exception:
                                pass

                        # Получаем время последнего изменения
                        try:
                            mtime = dst.stat().st_mtime if dst.exists() else None
                        except Exception:
                            mtime = None

                        # Проверяем кэш фотографий
                        cached = photo_cache.get(hwnd)
                        if cached and cached[1] == mtime:
                            photo = cached[0]
                        else:
                            if dst.exists():
                                try:
                                    pil = Image.open(str(dst)).convert("RGBA")
                                    pil = pil.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
                                except Exception:
                                    pil = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
                            else:
                                pil = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))

                            photo = ImageTk.PhotoImage(pil)
                            photo_cache[hwnd] = (photo, mtime)

                        if hwnd in canvas_items:
                            item_id = canvas_items[hwnd]
                            self.canvas.coords(item_id, x + ICON_SIZE // 2, y)
                            self.canvas.itemconfigure(item_id, image=photo)  # Обновляем изображение
                        else:
                            # Создаем новое изображение и добавляем тег "icon"
                            item_id = self.canvas.create_image(x + ICON_SIZE // 2, y, image=photo)
                            self.canvas.addtag_withtag("icon", item_id)  # Добавляем тег "icon" для управления
                            self.canvas.tag_bind(item_id, "<Button-1>", on_icon_click_factory(hwnd))  # Привязываем событие клика
                            canvas_items[hwnd] = item_id  # Сохраняем item_id для последующей работы

                        new_canvas_hwnds.add(hwnd)
                        if orientation:
                            x += ICON_SIZE + GAP
                        else:
                            y += ICON_SIZE + GAP

                    except Exception:
                        continue
                remove_hwnds = [h for h in canvas_items.keys() if h not in new_canvas_hwnds]
                for h in remove_hwnds:
                    try:
                        self.canvas.delete(canvas_items[h])
                    except Exception:
                        pass
                    canvas_items.pop(h, None)
                    photo_cache.pop(h, None)
            except Exception as e:
                log.error(f'up_ic-{e}')
    
        self.root.after(UPDATE_ICON_MS, lambda: self.run())
        