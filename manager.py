import threading
import logger
from socket_client import BaseSocketClient 
from variable import ports 

log = logger.setup_logging()

class WindowDataManager:
    def __init__(self, port):
        self.port = port
        log.info(f"🚀 [Manager] Инициализация на порту: {self.port}")
        self.client = BaseSocketClient(port, "Global-Win-Manager", is_zlib=True)
        self.subscribers = [] 
        self.last_data = None 
    def subscribe(self, callback):
        if callback not in self.subscribers:
            self.subscribers.append(callback)
            if self.last_data is not None:
                try:
                    callback(self.last_data)
                except Exception as e:
                    log.error(f"❌ [Manager] Ошибка при первичной отправке: {e}")
        else:
            log.warning("⚠️ [Manager] Подписчик уже существует")

    def _broadcast(self, data):
        if not data:
            return
        self.last_data = data
        for callback in self.subscribers:
            try:
                callback(data)
            except Exception as e:
                log.error(f"❌ [Manager] Ошибка в подписчике: {e}")

    def start(self):
        t = threading.Thread(
            target=self.client.run_loop, 
            args=(self._broadcast,), 
            kwargs={'init_msg': b"a"}, 
            daemon=True
        )
        t.start()

win_manager = WindowDataManager(ports['get_win'])
