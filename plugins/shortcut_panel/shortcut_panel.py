from plugins.shortcut_panel.variable import *
from windows_server import *
import os
import subprocess
import win32com.client
from PIL import Image, ImageTk
from pathlib import Path
import logger
import queue
import threading
full_screen_prev = False
paused_for_fullscreen = False
fool = False
st=None
log=logger.setup_logging()

def get_shortcuts_from_directory(directory):
    shortcuts = []
    for item in directory.iterdir():
        if item.is_file() and item.suffix == '.lnk':
            shortcuts.append(item)
    return shortcuts

def resolve_path(path):
    return os.path.expandvars(path)

def get_executable_from_shortcut(shortcut_path):
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    return shortcut.TargetPath, shortcut.IconLocation.split(',')[0]

def save_icon(icon_image, name, SHORTCUTS_DIR):
    icon_file_path = SHORTCUTS_DIR / f"{name}.png"
    icon_image.save(icon_file_path, format='PNG')

def on_icon_click_factory(exe_path):
    def handler(event, _exe=exe_path):
        try:
            w = get_executable_paths_with_open_windows(_exe)
        except Exception as e:
            w = []

        if w and any(os.path.normcase(os.path.normpath(w[0][2])) == os.path.normcase(os.path.normpath(p)) for p in open_one):
            hwnd = w[0][0]
            try:
                bring_window_to_front(hwnd)
            except Exception as e:
                log.error('Error in bring_window_to_front:', e)
        else:
            try:
                if _exe and os.path.exists(_exe) and os.path.splitext(_exe)[1] in ['.exe', '.bat', '.cmd']:
                    subprocess.Popen(_exe)
                else:
                    log.error(f'Error: {_exe}')
            except Exception as e:
                log.error('Error launching', _exe, e)

    return handler

def fs_thread(q):
    last_status = None
    addr = ('localhost', ports['is_full_win'])
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect(addr)
                while True:
                    raw_data = sock.recv(4)
                    if not raw_data: break
                    status = int.from_bytes(raw_data, 'big')
                    if status != last_status:
                        last_status = status
                        q.put(status)
        except Exception:
            time.sleep(1)

class shortcut_panel:
    def __init__(self, canvas, root, shortcuts, w):
        self.canvas = canvas
        self.root = root
        self.w = w
        self.shortcuts_config = SHORTCUTS_DIR 
        self.fs_val = 0
        self.fs_queue = queue.Queue()
        self.icons_loaded = False 
        
        if not hasattr(self.canvas, 'images'):
            self.canvas.images = []

        threading.Thread(target=fs_thread, args=(self.fs_queue,), daemon=True).start()

    def clear_icons(self):
        """Полная очистка канваса от старых иконок и ссылок на них"""
        self.canvas.delete("icon")
        self.canvas.images = []
        self.icons_loaded = False

    def shortcut_panel(self):
        global full_screen_prev, paused_for_fullscreen
        
        # Получаем последнее состояние из очереди
        while not self.fs_queue.empty():
            self.fs_val = self.fs_queue.get_nowait()
        
        fs = self.fs_val
        
        if fs == 1:
            if not full_screen_prev:
                full_screen_prev = True
                paused_for_fullscreen = True
                self.canvas.itemconfigure("icon", state='hidden')
        else:
            if full_screen_prev:
                full_screen_prev = False
                paused_for_fullscreen = False
                self.canvas.itemconfigure("icon", state='normal')

        # Отрисовка: только если НЕ полноэкранный режим и иконки еще не созданы
        if not paused_for_fullscreen and not self.icons_loaded:
            # Если нужно перерисовать (например, обновились файлы), 
            # здесь можно вызвать self.clear_icons()
            
            for path_str, start_x, start_y in self.shortcuts_config:
                shortcut_dir = Path(path_str)
                x, y = start_x, start_y
                
                for shortcut in get_shortcuts_from_directory(shortcut_dir):
                    exe_path, icon_path = get_executable_from_shortcut(shortcut)
                    exe_path = resolve_path(exe_path)
                    
                    icon_file_path = shortcut_dir / f"{shortcut.stem}.png"
                    if icon_file_path.exists():
                        icon_image = Image.open(icon_file_path)
                    else:
                        try:
                            icon_image = extract_icon_from_exe(resolve_path(icon_path))
                            save_icon(icon_image, shortcut.stem, shortcut_dir)
                        except Exception:
                            icon_image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0,0,0,0))

                    icon_image.thumbnail((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(icon_image)
                    
                    # Создаем объект с тегом "icon"
                    item_id = self.canvas.create_image(
                        x + ICON_SIZE // 2, y + RECT // 2, 
                        image=photo, tags="icon"
                    )
                    self.canvas.tag_bind(item_id, "<Button-1>", on_icon_click_factory(exe_path))
                    self.canvas.images.append(photo)

                    if orientation: x += ICON_SIZE + GAP
                    else: y += ICON_SIZE + GAP
            
            self.icons_loaded = True
            paused_for_fullscreen = True # Логика из оригинала: блокируем повторный вход

    def run(self):
        self.shortcut_panel()
        self.root.after(UPDATE_GRAPMS, self.run)