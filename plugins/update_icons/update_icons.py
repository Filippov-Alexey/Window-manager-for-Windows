from manager import win_manager
from plugins.update_icons.variable import *
from variable import *
from windows_server import bring_window_to_front, extract_icon, extract_icon_from_hicon
from PIL import Image, ImageTk
import re
import logger
import queue
log=logger.setup_logging()

def on_icon_click_factory(hwnd):

    def handler(event, _hwnd=hwnd):
        bring_window_to_front(_hwnd)
        
    return handler
def sanitize_filename(title):
    return re.sub(r'[\/:*?"<>|]', '_', title)

at=None
class update_icons:
    def __init__(self, canvas, root, RECT_HEIGHT, w,stop_event):
        self.canvas = canvas
        self.root = root
        self.w = w
        self.data_queue = queue.Queue(maxsize=1) 
        self.current_raw_data = None  
        self.rect = []
        
        win_manager.subscribe(self.on_data_received)

    def on_data_received(self, data):
        try:
            if self.data_queue.full():
                self.data_queue.get_nowait()
            self.data_queue.put_nowait(data)
        except Exception as e:
            log.error(f"Ошибка очереди иконок: {e}")

    def run(self):
        new_data = None
        try:
            while not self.data_queue.empty():
                new_data = self.data_queue.get_nowait()
        except queue.Empty:
            pass

        if new_data and new_data != self.current_raw_data:
            self.current_raw_data = new_data
            self.update_icons_logic(new_data)
            
        self.root.after(UPDATE_ICON_MS, self.run)
    def update_icons_logic(self, tit):
        current_hwnds = [w['hwnd'] for w in tit] if tit else []
        if self.rect == current_hwnds:
            return

        self.rect = current_hwnds
        new_canvas_hwnds = set()

        curr_x, curr_y = get_start_xy(orientation)

        try:
            for win in tit:
                hwnd = win['hwnd']
                hicon_ptr = win.get('hicon', 0)
                
                photo = photo_cache.get(hwnd)
                
                if photo:
                    try:
                        self.canvas.call('image', 'width', photo)
                    except:
                        photo = None
                        photo_cache.pop(hwnd, None)

                if not photo:
                    try:
                        if hicon_ptr:
                            pil_img = extract_icon_from_hicon(hicon_ptr, ICON_SIZE)
                        else:
                            pil_img = extract_icon(win['path'], index=0, size=ICON_SIZE)
                        
                        pil_img.thumbnail((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
                        photo = ImageTk.PhotoImage(pil_img, master=self.root)
                        photo_cache[hwnd] = photo
                    except Exception as e:
                        log.error(f"Ошибка загрузки иконки {hwnd}: {e}")
                        continue

                create_new = True
                if hwnd in canvas_items:
                    item_id = canvas_items[hwnd]
                    try:
                        if self.canvas.type(item_id) == 'image':
                            self.canvas.coords(item_id, curr_x + ICON_SIZE // 2, curr_y)
                            self.canvas.itemconfigure(item_id, image=photo)
                            create_new = False
                        else:
                            self.canvas.delete(item_id)
                    except Exception:
                        pass

                if create_new:
                    item_id = self.canvas.create_image(
                        curr_x + ICON_SIZE // 2, curr_y, 
                        image=photo, 
                        tags="icon"
                    )
                    self.canvas.tag_bind(item_id, "<Button-1>", on_icon_click_factory(hwnd))
                    canvas_items[hwnd] = item_id

                new_canvas_hwnds.add(hwnd)
                
                if orientation: 
                    curr_x += ICON_SIZE + GAP
                else:           
                    curr_y += ICON_SIZE + GAP

            current_keys = list(canvas_items.keys())
            for h in current_keys:
                if h not in new_canvas_hwnds:
                    try:
                        self.canvas.delete(canvas_items[h])
                    except: pass
                    canvas_items.pop(h, None)
                    photo_cache.pop(h, None)

        except Exception as e:
            log.error(f'up_ic_error: {e}')
