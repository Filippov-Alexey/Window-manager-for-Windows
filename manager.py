import threading
import logger
from socket_client import BaseSocketClient # Импорт вашего класса
# Импортируйте здесь настройки портов, если они в отдельном файле
from variable import ports 

log = logger.setup_logging()

class WindowDataManager:
    def __init__(self, port):
        self.client = BaseSocketClient(port, "Global-Win-Manager", is_zlib=True)
        self.subscribers = [] 
        self.last_data = None

    def subscribe(self, callback):
        if callback not in self.subscribers:
            self.subscribers.append(callback)

    def _broadcast(self, data):
        self.last_data = data
        for callback in self.subscribers:
            try:
                callback(data)
            except Exception as e:
                log.error(f"Ошибка в подписчике: {e}")

    def start(self):
        t = threading.Thread(
            target=self.client.run_loop, 
            args=(self._broadcast,), 
            kwargs={'init_msg': b"a"}, 
            daemon=True
        )
        t.start()

# Создаем объект менеджера прямо здесь
win_manager = WindowDataManager(ports['get_win'])
