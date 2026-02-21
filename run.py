import time
import subprocess
import sys
import os
import winreg
import ctypes
import logger
log=logger.setup_logging()
log.info('run')
ORIGINAL_STICKY_FLAGS = None
MAIN_SCRIPTS = ["windows_server.py", "windows_controle.py", "keyboard_server.py", "keyboard_manager.py", "windows_is_full_server.py", "panel.py"]
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
                process.wait(timeout=2)
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
    subprocess.run('taskkill /im blocking.exe /f'.split(), capture_output=True)
    manage_sticky_keys(disable=False)
    subprocess.run('taskkill /im win.exe /f'.split(), capture_output=True)
    # restart_explorer()

# --- Инициализация ---
manage_sticky_keys(disable=True)
# Инициализируем список отслеживаемых файлов перед запуском
for f in get_variable_files():
    watched_files[f] = os.path.getmtime(f)

start_all_scripts()

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
