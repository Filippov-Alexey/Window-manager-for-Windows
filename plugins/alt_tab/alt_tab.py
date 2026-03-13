from PIL import Image, ImageTk
from queue import Queue
from variable import *
from plugins.alt_tab.variable import *
import socket
import threading
import pygetwindow
import zlib
import json
import ctypes
import win32gui
import win32ui
import win32con
from PIL import Image, ImageTk
from queue import Queue
import win32com.client
import logger
log=logger.setup_logging()
log.info('run')
def force_activate(hwnd):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shell.SendKeys('%') # Имитируем нажатие ALT
        
        # 1. Восстанавливаем окно, если оно свернуто
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        # 2. Выводим на передний план
        win32gui.SetForegroundWindow(hwnd)
        # 3. Разворачиваем (опционально)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW) 
        return True
    except Exception as e:
        log.error(f"Ошибка: {e}")
        return False

# В вашем цикле используйте:
def capture_window(hwnd, title):
    # Проверка на корректность hwnd
    im = None
    try:
        left, top, right, bot = win32gui.GetWindowRect(hwnd)
        w, h = right - left, bot - top
        log.info(f'{title}={left},{top},{right},{bot}')

        if w <= 100 and h <= 100: return None

        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC  = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, w, h)
        saveDC.SelectObject(saveBitMap)

        # ВАЖНО: Флаг 3 (PW_RENDERFULLCONTENT) позволяет захватывать современные окна
        result = ctypes.windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)
        
        if result == 1:
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            im = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), 
                                bmpstr, 'raw', 'BGRX', 0, 1)

        # Чистим ресурсы строго
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
    except Exception as e:log.error(f'cw err--{e}')
    finally:
        return im
img=[]

class alt_tab:
    def __init__(self, canvas, root, w, rect):
        self.root = root
        self.canvas = canvas
        self.command_queue = Queue()
        self.rect=rect
        self.tag='alt_tab'
        self.is_active = False
        self.windows_data = []
        self.selected_index = 1
        self.tk_images = []

        # 1. Запускаем ТОЛЬКО слушатель клавиатуры в фоне
        threading.Thread(target=self.listen_keyboard, daemon=True).start()
        threading.Thread(target=self.process_queue_tick, daemon=True).start()
        
        # 2. Запускаем цикл проверки очереди в ГЛАВНОМ потоке
        self.process_queue_tick()

    def listen_keyboard(self):
        keys='+'.join(key_run)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', ports['get_key']))
            while True:
                m = s.recv(4).decode('utf-8', errors='replace')
                data=s.recv(int(m)).decode('utf-8', errors='replace')
                if not data: continue
                try:
                    msg = json.loads(data)
                    key = msg.get('key_name')
                    status = msg.get('status')
                    options = msg.get('option', '')
                    if msg.get('numpan')=='Main':
                        # Нажали Alt + Left: отправляем сигнал на начало захвата
                        if keys in options and status == 'Down':
                            if not self.is_active:
                                self.is_active = True
                                # Кладем задачу в очередь для ГЛАВНОГО потока
                                self.command_queue.put(('PREPARE_AND_CAPTURE', None))
                            else:
                                self.command_queue.put(('NEXT_STEP', None))

                        # Отпустили Alt: закрываем интерфейс
                        if key == key_run[0] and status == 'Up':
                            if self.is_active:
                                self.is_active = False
                                self.command_queue.put(('ACTIVATE_AND_CLEAR', None))
                except Exception as e:
                    log.error(e)

    def process_queue_tick(self):
        try:
            if not self.command_queue.empty():
                cmd, data = self.command_queue.get_nowait()
                
                if cmd == 'PREPARE_AND_CAPTURE':
                    # Выполняем захват окон (можно вынести в поток, если окон много)
                    self.fetch_and_show_windows()
                    
                elif cmd == 'NEXT_STEP':
                    if self.windows_data:
                        self.selected_index = (self.selected_index + 1) % len(self.windows_data)
                        self.draw_ui()
                        
                elif cmd == 'ACTIVATE_AND_CLEAR':
                    try:
                        self.activate_selected()
                        self.canvas.delete(self.tag)
                        self.windows_data = []
                        self.tk_images = [] # Чистим память
                    except Exception as e:
                        log.error(e)
                        
        except Exception as e:
            log.error(e)
            
        # Перезапуск проверки через 20мс
        self.root.after(20, self.process_queue_tick)

    def fetch_and_show_windows(self):
        """Получает список окон и делает скриншоты"""
        # Подключаемся к серверу окон только когда это нужно (при нажатии)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('localhost', ports['get_win']))
                m = s.recv(4).decode('utf-8', errors='replace').strip() 
                data=s.recv(int(m))

            if not data is None:
                d = zlib.decompress(data)
                tit = json.loads(d.decode('utf-8'))
                
                self.windows_data = []
                for hwnd, title, path, rects in tit:
                    img = capture_window(hwnd, title)
                    if img:
                        self.windows_data.append({
                            'hwnd': hwnd, 
                            'title': title,
                            'img': img.resize(size)
                        })
                
                if self.windows_data:
                    self.selected_index = 1
                    self.draw_ui()
        except Exception as e:
            log.error(e)
    def create_rectangle(self, x1, y1, x2, y2, **kwargs):
        tag = kwargs.pop("tags", self.tag) # Используем переданный тег или тег по умолчанию
        
        if "alpha" in kwargs:
            alpha = int(kwargs.pop("alpha") * 255)
            fill = kwargs.pop("fill", "white")
            
            # Получаем доступ к окну через canvas, если self.master не определен
            root = self.canvas.winfo_toplevel()
            rgb = root.winfo_rgb(fill)
            rgba = (rgb[0] >> 8, rgb[1] >> 8, rgb[2] >> 8, alpha)
            
            image = Image.new("RGBA", (x2-x1, y2-y1), rgba)
            tk_image = ImageTk.PhotoImage(image)
            
            # Сохраняем ссылку, чтобы картинка не удалилась
            if not hasattr(self, 'tk_images'): self.tk_images = []
            self.tk_images.append(tk_image)
            
            self.canvas.create_image(x1, y1, image=tk_image, anchor="nw", tags=tag)

        # Убираем self из аргументов и рисуем границы (или прозрачный прямоугольник для событий)
        return self.canvas.create_rectangle(x1, y1, x2, y2, tags=tag, **kwargs)

    def draw_ui(self):
        self.canvas.delete(self.tag)
        self.tk_images = [] 
        self.create_rectangle(start_x, start_y, start_x+850, start_y+180, fill=color_backgrount, alpha=alpha_channel)

        total_wins = len(self.windows_data)
        
        # Вычисляем диапазон видимости для карусели
        if total_wins <= display_count:
            start_idx = 0
            end_idx = total_wins
        else:
            start_idx = max(0, min(self.selected_index - 2, total_wins - display_count))
            end_idx = start_idx + display_count

        for display_pos, i in enumerate(range(start_idx, end_idx)):
            win = self.windows_data[i]
            tk_img = ImageTk.PhotoImage(win['img'])
            self.tk_images.append(tk_img)
            
            x = start_x + 20 + display_pos * (size[0]+15)
            y = start_y + 20
            # Рамка и изображение
            color = color_active_rectangle if i == self.selected_index else color_passve_rectangle
            width = 4 if i == self.selected_index else 1
            
            self.canvas.create_rectangle(x-5, y-5, x+5+size[0], y+5+size[1], 
                                       outline=color, width=width, tags=self.tag)
            self.canvas.create_image(x, y, anchor="nw", image=tk_img, tags=self.tag)

            # Добавляем заголовок окна
            title = win['title']
            if len(title) > 20: title = title[:17] + "..." # Обрезка длинного текста
            
            self.canvas.create_text(x + 75, y + 120, 
                                    text=title, 
                                    fill="white", 
                                    font=("Segoe UI", 10),
                                    anchor="n",
                                    width=150, # Автоперенос, если текст не влезет
                                    justify="center",
                                    tags=self.tag)
    def activate_selected(self):
        if self.windows_data:
            title=self.windows_data[self.selected_index]['title']
            win=pygetwindow.getWindowsWithTitle(title)
            hwnd,tit,imgs = self.windows_data[self.selected_index].items()
            for i in win:
                if hwnd[1] == i._hWnd:
                    try:
                        while i.isActive==False:
                            log.info(f'{tit[1]}-{i.isActive}')
                            force_activate(i._hWnd)
                        break
                    except Exception as e:    
                        log.error(e)
    def run(self):  
        self.root.after(100, lambda: self.run())


