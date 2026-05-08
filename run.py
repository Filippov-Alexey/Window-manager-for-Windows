import threading
import time
import subprocess
import sys
import os
import socket
import winreg
import ctypes
import logger
import display_server
import windows_server
import windows_controle
import space_server
import keyboard_server
import keyboard_manager
import panel
from variable import *
import variable
log=logger.setup_logging()
log.info('run')
ORIGINAL_STICKY_FLAGS = None
venv_path = 'venv'
python_path = os.path.join(venv_path, 'Scripts', 'python.exe')
p = {}
TIMEOUT = 10
RESTART_COOLDOWN = 2
watched_files = {}

JOBS_MAP = {
    "display_server.py": display_server.run_mouse_and_read_output,
    "keyboard_server.py": keyboard_server.run_mouse_and_read_output,
    "windows_server.py": windows_server.c_plus_plus_listener,
    "windows_controle.py": windows_controle.runmouse,
    "space_server.py": space_server.start_desktop_manager,
    "keyboard_manager.py": keyboard_manager.start_client,
    "panel.py": panel.main_func
}

PORT_MAP = {
    "display_server.py": ports.get('get_display'),
    "windows_server.py": ports.get('get_win'),
    "space_server.py": ports.get('get_space'),
    "keyboard_server.py": ports.get('get_key')
}

def get_hb_path(script):
    return os.path.join(os.getcwd(), "heartbeats", f"{script}.hb")

def is_port_open(port):
    if not port: return True
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.3):
            return True
    except:
        return False


def manage_sticky_keys(disable=True):
    global ORIGINAL_STICKY_FLAGS
    key_path = r"Control Panel\Accessibility\StickyKeys"
    
    class STICKYKEYS(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwFlags", ctypes.c_uint)]

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        if disable:
            ORIGINAL_STICKY_FLAGS, _ = winreg.QueryValueEx(key, "Flags")
            new_flags = "506" 
        else:
            new_flags = ORIGINAL_STICKY_FLAGS if ORIGINAL_STICKY_FLAGS else "510"
            
        winreg.SetValueEx(key, "Flags", 0, winreg.REG_SZ, new_flags)
        winreg.CloseKey(key)
        sk = STICKYKEYS(cbSize=ctypes.sizeof(STICKYKEYS), dwFlags=int(new_flags))
        ctypes.windll.user32.SystemParametersInfoW(0x003B, sk.cbSize, ctypes.byref(sk), 0)
        log.info(f"Настройки залипания клавиш: {new_flags}")
    except Exception as e:
        log.error(f"Ошибка настройки клавиш: {e}")

def restart_explorer():
    subprocess.run("taskkill /f /im explorer.exe & start explorer.exe", shell=True)

def get_hb_path(script):
    return f"hb_{script}.tmp"

def get_variable_files():
    found_files = []
    for root, dirs, files in os.walk("."):
        if "variable.py" in files:
            found_files.append(os.path.join(root, "variable.py"))
    return found_files

current_files = get_variable_files()
def check_for_config_changes():
    global watched_files
    changed = False

    for file_path in current_files:
        mtime = os.path.getmtime(file_path)
        if file_path not in watched_files:
            watched_files[file_path] = mtime
        elif watched_files[file_path] != mtime:
            watched_files[file_path] = mtime
            changed = True
            log.info(f"Обнаружено изменение в: {file_path}")

    return changed

manage_sticky_keys(disable=True)
for f in get_variable_files():
    watched_files[f] = os.path.getmtime(f)

from socket_client import BaseSocketClient
last_restart_time=0
restart_lock = threading.Lock()

import time
import threading


def restart_panel():
    global p, JOBS_STOP_EVENTS
    name = 'panel.py'
    
    log.info(f"🔄 Рестарт модуля {name}...")

    if name in JOBS_STOP_EVENTS:
        JOBS_STOP_EVENTS[name].set()
    
    if name in PORT_MAP:
        force_release_port(PORT_MAP[name])

    try:
        tools = components.get('tools', {})
        for _, path in tools.items():
            process_name = path.split('\\')[-1]
            log.info(f"🔨 Принудительный taskkill: {process_name}")
            subprocess.run(['taskkill', '/f', '/t', '/im', process_name], capture_output=True)
    except Exception as e:
        log.error(f"❌ Ошибка очистки процессов: {e}")

    if name in p:
        p[name].join(timeout=0.5)
        if p[name].is_alive():
            log.warning(f"⏳ {name} не ответил, удаляем ссылку")
        del p[name]

    if name in JOBS_STOP_EVENTS:
        del JOBS_STOP_EVENTS[name]

    log.info(f"✅ Модуль {name} очищен. Перезапуск...")
    start_module([name])
last_display_data = None 

def handle_display_event(data=None): 
    global last_restart_time, last_display_data
    
    if data is None:
        log.warning("🔔 Событие получено, но данных нет")
        return
    
    if data == last_display_data:
        log.info("🔔 Событие дисплея: данные не изменились, игнорируем.")
        return

    log.info(f"🔔 Данные дисплея изменились: {data}")
    
    with restart_lock:
        current_time = time.time()
        diff = current_time - last_restart_time
        
        if diff > RESTART_COOLDOWN:
            log.info(f"🖥️ Выполнение restart_panel... (Пауза: {diff:.1f}с)")
            try:
                start=True
                if not last_display_data is None:
                    restart_panel()
                    start=False
                variable.display = data
                last_display_data = data 
                last_restart_time = current_time
                log.debug('start')
                if start:
                    start_module()
            except Exception as e:
                log.error(f"❌ Ошибка рестарта: {e}")
        else:
            log.warning(f"⏳ Кулдаун активен: осталось {RESTART_COOLDOWN - diff:.1f}с")
def display_worker(stop_event):
    global last_restart_time
    try:
        client = BaseSocketClient(ports['get_display'], "Watchdog-Display", is_json=True)
        log.info("📡 Поток отслеживания дисплеев подключен")
        
        client.run_loop(handler=handle_display_event, stop_event=stop_event)
    except Exception as e:
        if not stop_event.is_set():
            log.error(f"❌ Ошибка сокета дисплея: {e}. Повтор через 5с...")
JOBS_STOP_EVENTS = {} 
def start_module(module_names=None):
    target_names = module_names if module_names else list(JOBS_MAP.keys())
    
    for name in target_names:
        if name in p:
            if p[name].is_alive():
                log.warning(f"⚠️ Модуль {name} уже работает. Пропускаем.")
                continue
            else:
                del p[name]
                if name in JOBS_STOP_EVENTS: del JOBS_STOP_EVENTS[name]

        if name not in JOBS_MAP:
            log.error(f"❌ Ошибка: Модуль {name} отсутствует в JOBS_MAP")
            continue

        stop_event = threading.Event()
        JOBS_STOP_EVENTS[name] = stop_event
        t = threading.Thread(
            target=JOBS_MAP[name], 
            name=name, 
            kwargs={'stop_event': stop_event}, 
            daemon=True
        )
        
        try:
            t.start()
            p[name] = t
            log.info(f"✅ {name} запущен")
        except Exception as e:
            log.error(f"❌ Не удалось запустить {name}: {e}")
def force_release_port(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            s.connect(('127.0.0.1', port))
    except:
        pass
def stop_module(module_names=None):
    target_names = module_names if module_names else list(p.keys())
    
    for name in list(target_names):
        if name not in JOBS_STOP_EVENTS:
            continue
            
        log.info(f"🛑 Останавливаю {name}...")
        JOBS_STOP_EVENTS[name].set()
        if name in PORT_MAP:
            force_release_port(PORT_MAP[name])

        if name in p:
            if p[name]=='panel.py':
                for i, k in components.get('tools', {}).items():
                    process_name = k.split('\\')[-1]
                    log.info(f"🔨 Taskkill: {process_name}")
                    subprocess.run(['taskkill', '/f', '/im', process_name], capture_output=True)
            p[name].join(timeout=3) 
            if p[name].is_alive():
                log.error(f"⚠️ {name} не завершился вовремя, будет убит при выходе программы")

            
            del p[name]
            
        del JOBS_STOP_EVENTS[name]
        log.info(f"🚮 Модуль {name} полностью удален из памяти")

log.info("🏁 Все модули успешно запущены.")
log.info('strt')


def start_all_threads():

    stop_event_t9 = threading.Event()
    t9 = threading.Thread(target=display_worker, args=(stop_event_t9,), daemon=True)
    t9.start()

def main():
    try:
        start_all_threads()
        time.sleep(5)

        start_module()
        
        from manager import win_manager
        win_manager.start()
        while True:
            if check_for_config_changes():
                log.info("⚙️ Файлы изменены! Полная очистка и перезапуск...")
                
                restart_panel()        
            for name in list(JOBS_MAP.keys()):
                thread = p.get(name)
                hb_file = get_hb_path(name)
                
                is_dead = thread is None or not thread.is_alive()

                if is_dead:
                    reason = "МЕРТВ" if is_dead else "ЗАВИС"
                    log.warning(f"⚠️ Модуль {name} {reason}. Перезапуск только этого модуля...")
                    
                    if os.path.exists(hb_file): 
                        try: os.remove(hb_file)
                        except: pass
                    
                    if name in p: del p[name]
                    start_module([name])

            time.sleep(2)
          
    except KeyboardInterrupt:
        log.info("Прервано пользователем")
    finally:
        stop_module()
        sys.exit(0)

if __name__ == "__main__":
    main()