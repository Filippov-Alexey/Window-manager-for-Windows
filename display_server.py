import subprocess
from threading import Event
from variable import ports, tools
from socket_server import BaseServer
from subprocess_server import BaseSubprocessServer
import logger

log = logger.setup_logging()
stop_event = Event()

# server = BaseServer(ports['get_display'], "DisplayServer", is_json=False)

def run_mouse_and_read_output():
    # 1. Создаем сервер
    display_server = BaseServer(ports['get_display'], "DisplayServer", is_json=False)
    
    # 2. Используем базовый обработчик (он по умолчанию делает strip() и broadcast())
    handler = BaseSubprocessServer(
        server_instance=display_server,
        cmd=[tools['display']],
        stop_event=stop_event,
        label="DisplayServer"
    )
    
    # 3. Запуск (метод run уже содержит логику log.info и try/finally/kill)
    handler.run()

if __name__ == "__main__":
    # 2. СЕРВЕР ЗАПУСКАЕТСЯ ОДИН РАЗ ЗДЕСЬ
    # server.start() 
    
    # 3. Бесконечный цикл ПЕРЕЗАПУСКАЕТ только процесс, но не сервер!
    while True:
        run_mouse_and_read_output()
