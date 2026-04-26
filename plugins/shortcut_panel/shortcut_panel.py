from plugins.shortcut_panel.variable import *
from windows_server import *
import os
import subprocess
import win32com.client
from PIL import Image, ImageTk
from pathlib import Path
import logger
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


from socket_client import BaseSocketClient

def on_icon_click_factory(exe_path):
    # 🟢 Создаем клиент один раз для всех вызовов handler
    # Настраиваем на JSON + Zlib
    win_client = BaseSocketClient(ports['get_win'], "ShortCut-Click", is_zlib=True)

    def handler(event, _exe=exe_path):
        if not _exe: return
        
        target_path = os.path.normpath(_exe).lower()
        restricted_paths = [os.path.normpath(p).lower() for p in open_one]
        window_found = False

        # Если путь в списке ограничений — ищем уже открытое окно
        if target_path in restricted_paths:
            log.info(f"🔍 Поиск окна для: {target_path}")
            
            # 🟢 Получаем список окон одной командой
            tit = win_client.request()
            
            if tit:
                for win in tit:
                    win_exe = os.path.normpath(win[2]).lower()
                    if win_exe == target_path:
                        log.info(f"✅ Найдено! Переключаюсь на HWND: {win[0]}")
                        bring_window_to_front(win[0])
                        window_found = True
                        break

        # Если окно не найдено или путь не в списке — запускаем приложение
        if not window_found:
            try:
                if os.path.exists(_exe):
                    log.info(f"🚀 Запуск: {_exe}")
                    subprocess.Popen(_exe)
                else:
                    log.error(f"❌ Путь не существует: {_exe}")
            except Exception as e:
                log.error(f"Ошибка запуска: {e}")

    return handler
class shortcut_panel:
    def __init__(self, canvas, root, shortcuts, w):
        self.canvas = canvas
        self.root = root
        self.w = w
        self.shortcuts_config = SHORTCUTS_DIR 
        self.fs_val = 0
        self.icons_loaded = False 
        
        if not hasattr(self.canvas, 'images'):
            self.canvas.images = []

        self.shortcut_panel()

    def shortcut_panel(self):
            global full_screen_prev, paused_for_fullscreen
        
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
        
    def run(self):
        self.root.after(UPDATE_GRAPMS, self.run)