import time
import subprocess
import sys

p = {}
MAIN_SCRIPTS = ["windows_server.py", "windows_controle.py", "keyboard_server.py", "keyboard_manager.py", "windows_is_full_server.py", "panel.py"]

# Функция для завершения всех процессов
def terminate_processes():
    for script, process in p.items():
        if process.poll() is None:  # Если процесс ещё активен
            print(f"Terminating {script} with PID {process.pid}")
            process.terminate()  # Завершить процесс
            process.wait()  # Дождаться завершения процесса

# Запуск процессов
for script in MAIN_SCRIPTS:
    p[script] = subprocess.Popen(['python', script])

try:
    while True:
        # Проверка каждого процесса
        for script in MAIN_SCRIPTS:
            process = p[script]
            # print(f'{process}-{script}')
            if process.poll() is not None:  # Процесс завершился
                print(f"{script} has stopped, restarting...")
                p[script] = subprocess.Popen(['python', script])  # Перезапуск процесса
        time.sleep(1)

except KeyboardInterrupt:
    print("Interrupt received, terminating all scripts...")
    terminate_processes()  # Завершить все процессы
    sys.exit(0)

finally:
    terminate_processes()  # Завершить все процессы в любом случае
