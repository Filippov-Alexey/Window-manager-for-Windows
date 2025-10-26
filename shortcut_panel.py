from variable import *
from update_icons import *
import os
import subprocess
import win32com.client
from PIL import Image, ImageTk
from pathlib import Path
import socket

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
    print(exe_path)
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
                print('Error in bring_window_to_front:', e)
        else:
            try:
                if _exe and os.path.exists(_exe) and os.path.splitext(_exe)[1] in ['.exe', '.bat', '.cmd']:
                    subprocess.Popen(_exe)
                else:
                    print(f'Error: {_exe}')
            except Exception as e:
                print('Error launching', _exe, e)

    return handler


full_screen_prev = False
paused_for_fullscreen = False
fool = False
def create_shortcut_icons(canvas, root, shortcuts):
    global full_screen_prev, paused_for_fullscreen

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        try:
            client_socket.connect(('localhost', 65433))
            fs = int(client_socket.recv(4).decode('utf-8', errors='replace'))

        except Exception as e:
            print(f"short An error occurred while connecting to the server: {e}")
            return

    # Проверяем состояние полноэкранного режима
    if fs == 1:
        if not full_screen_prev:
            # Если мы переходим в полноэкранный режим
            full_screen_prev = True
            paused_for_fullscreen = True
            # Скрываем все иконки
            canvas.itemconfigure("icon", state='hidden')  # Скрываем элементы с тегом "icon"
            root.after(100, lambda: create_shortcut_icons(canvas, root, shortcuts))
            return
    else:
        if full_screen_prev:
            # Если мы выходим из полноэкранного режима
            full_screen_prev = False
            paused_for_fullscreen = False
            # Показываем все иконки
            canvas.itemconfigure("icon", state='normal')  # Показываем элементы с тегом "icon"

    # Отображаем иконки
    if paused_for_fullscreen==False:
        paused_for_fullscreen=True
        for shortcut_dir, start_x, y in shortcuts:
            shortcut_dir = Path(shortcut_dir)
            shortcuts_in_dir = get_shortcuts_from_directory(shortcut_dir)
            x = start_x

            for shortcut in shortcuts_in_dir:
                exe_path, icon_path = get_executable_from_shortcut(shortcut)
                exe_path = resolve_path(exe_path)
                icon_path = resolve_path(icon_path)

                icon_image = None
                icon_file_path = shortcut_dir / f"{shortcut.stem}.png"
                if icon_file_path.exists():
                    icon_image = Image.open(icon_file_path)
                else:
                    try:
                        if icon_path and not os.path.exists(icon_path):
                            icon_image = extract_icon_from_exe(icon_path)
                            save_icon(icon_image, shortcut.stem, shortcut_dir)
                    except Exception as e:
                        print(f"Error extracting icon: {e}")
                        icon_image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))

                if icon_image:
                    icon_image.thumbnail((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(icon_image)

                    item_id = canvas.create_image(x + ICON_SIZE // 2, y + RECT_HEIGHT // 2, image=photo)
                    canvas.tag_bind(item_id, "<Button-1>", on_icon_click_factory(exe_path))

                    # Добавляем тег "icon" к каждому элементу
                    canvas.addtag_withtag("icon", item_id)

                    x += ICON_SIZE + GAP

                    # Запоминаем изображения для управления памятью
                    if not hasattr(canvas, 'images'):
                        canvas.images = []
                    canvas.images.append(photo)

    root.after(100, lambda: create_shortcut_icons(canvas, root, shortcuts))
