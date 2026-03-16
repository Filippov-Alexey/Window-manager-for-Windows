import threading
import time
import subprocess
import sys
import os
import socket
import winreg
import ctypes
import logger
from variable import *
log=logger.setup_logging()
log.info('run')
ORIGINAL_STICKY_FLAGS = None
MAIN_SCRIPTS = ["windows_server.py", 
                "display_server.py",
                "windows_controle.py", 
                "keyboard_server.py", 
                "keyboard_manager.py", 
                "windows_is_full_server.py", 
                "panel.py"
                ]
venv_path = 'venv'
python_path = os.path.join(venv_path, 'Scripts', 'python.exe')
p = {}
TIMEOUT = 10

# Словарь для хранения времени изменения файлов variable.py
watched_files = {}

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
    # subprocess.run("explorer.exe")

def get_hb_path(script):
    return f"hb_{script}.tmp"

def stop_all_scripts():
    """Завершает только запущенные дочерние скрипты"""
    log.info("Остановка запущенных скриптов...")
    for script, process in p.items():
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=0)
            except:
                process.kill()
        hb = get_hb_path(script)
        if os.path.exists(hb): os.remove(hb)

def start_all_scripts():
    """Запускает все скрипты из списка"""
    log.info("Запуск всех скриптов...")
    for script in MAIN_SCRIPTS:
        hb = get_hb_path(script)
        if os.path.exists(hb): os.remove(hb)
        p[script] = subprocess.Popen([python_path, script])

def get_variable_files():
    """Ищет все файлы variable.py во всех подкаталогах"""
    found_files = []
    for root, dirs, files in os.walk("."):
        if "variable.py" in files:
            found_files.append(os.path.join(root, "variable.py"))
    return found_files

current_files = get_variable_files()
def check_for_config_changes():
    """Проверяет, изменился ли хоть один файл variable.py"""
    global watched_files
    changed = False

    # Проверка на изменение существующих или появление новых файлов
    for file_path in current_files:
        mtime = os.path.getmtime(file_path)
        if file_path not in watched_files:
            watched_files[file_path] = mtime
            # Если файл только найден, не считаем это изменением для перезапуска сразу
        elif watched_files[file_path] != mtime:
            watched_files[file_path] = mtime
            changed = True
            log.info(f"Обнаружено изменение в: {file_path}")

    return changed

def terminate_everything():
    """Полная очистка при выходе"""
    log.info("\nЗавершение работы монитора...")
    stop_all_scripts()
    manage_sticky_keys(disable=False)
    subprocess.run('taskkill /im blocking.exe /f'.split(), capture_output=True)
    subprocess.run('taskkill /im win.exe /f'.split(), capture_output=True)
    subprocess.run('taskkill /im display.exe /f'.split(), capture_output=True)
    # restart_explorer()
clients = []

def handle_client(conn, addr):
    """Обработчик для каждого клиента."""
    clients.append(conn)
    try:
        while True:
            time.sleep(1)
    except (ConnectionResetError, BrokenPipeError):
        log.error(f"Connection lost with {addr}.")
    except Exception as e:
        log.error(f"Error with client {addr}: {e}")
    finally:
        clients.remove(conn)
        log.error(f"Connection with {addr} closed.")
def send_updates(message):
    if clients and message:
        for conn in list(clients):
            try:
                conn.sendall(f'{len(message.encode('utf-8'))}\n'.encode())
                conn.sendall(message.encode('utf-8'))
            except Exception as e:
                clients.remove(conn)
                log.error(f"KS_Could not send message to client: {e}")

# --- Инициализация ---
manage_sticky_keys(disable=True)
# Инициализируем список отслеживаемых файлов перед запуском
for f in get_variable_files():
    watched_files[f] = os.path.getmtime(f)

start_all_scripts()
log.info('strt')


def recv_fixed(sock, n):
    """Вспомогательная функция: читает ровно n байт"""
    data = b''
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet: return None
        data += packet
    return data

def safe_recv(sock):
    # 1. Читаем заголовок до переноса строки (как отправляет сервер)
    header = b''
    while not header.endswith(b'\n'):
        char = sock.recv(1)
        if not char: return None
        header += char
    
    # 2. Извлекаем длину и читаем ровно столько байт payload
    length = int(header.decode().strip())
    payload = recv_fixed(sock, length)
    return payload.decode('utf-8', errors='replace')


def restart_panel():
    """Общая функция для перезапуска panel.py"""
    for script in MAIN_SCRIPTS:
        if script == 'panel.py':
            process = p.get(script)
            if process:
                log.warning('Restarting panel.py...')
                process.kill()
            break

def status_worker():
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5) # Чтобы поток не завис навечно
                s.connect(('127.0.0.1', 65438))
                data=safe_recv(s)
                if data == 'err\n':
                    restart_panel()
        except Exception as e:
            log.error(f"Status port error: {e}")
        time.sleep(2) # Пауза между попытками подключения

def display_worker():
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('localhost', ports['get_display']))
                s.settimeout(None) # Убираем таймаут, ждем данных столько, сколько нужно
                
                while True: # Внутренний цикл: читаем сообщения из одного соединения
                    data = safe_recv(s) # Используйте функцию из предыдущего ответа
                    if data is None: break # Сервер разорвал соединение
                    
                    log.info(f"Display event: {data}")
                    restart_panel() # ВНИМАНИЕ: если вызывать это тут, 
                                     # панель будет рестартить на каждое движение!
        except Exception as e:
            log.error(f"Display connection error: {e}")
            time.sleep(2) # Пауза перед переподключением при ошибке

# Запускаем фоновые потоки
threading.Thread(target=status_worker, daemon=True).start()
threading.Thread(target=display_worker, daemon=True).start()
try:
    while True:

        if check_for_config_changes():
            log.info("Конфигурация изменена. Перезапуск всех систем...")
            stop_all_scripts()
            start_all_scripts()

        # 2. Мониторинг состояния процессов (Dead/Frozen)
        for script in MAIN_SCRIPTS:
            process = p[script]
            hb_file = get_hb_path(script)
            
            is_dead = process.poll() is not None
            is_frozen = False
            
            if not is_dead and os.path.exists(hb_file):
                if time.time() - os.path.getmtime(hb_file) > TIMEOUT:
                    is_frozen = True

            if is_dead or is_frozen:
                log.info(f"Перезапуск: {script} (Причина: {'Мертв' if is_dead else 'Завис'})")
                if not is_dead:
                    process.kill()
                    process.wait()
                
                if os.path.exists(hb_file): os.remove(hb_file)
                p[script] = subprocess.Popen([python_path, script])
                
        time.sleep(2)

except KeyboardInterrupt:
    terminate_everything()
    sys.exit(0)
finally:
    terminate_everything()
