import socket
import json
import zlib
import threading
import logger

log = logger.setup_logging()

class BaseServer:
    def __init__(self, port, name, is_json=True, is_zlib=False):
        self.port = port
        self.name = name
        self.is_json = is_json
        self.is_zlib = is_zlib
        self.clients = set()
        self.clients_lock = threading.Lock()
        # 🚩 Хранилище для последнего успешно подготовленного пакета
        self.last_packet = None 

    def broadcast(self, data):
        """Рассылка данных и сохранение их как последних актуальных."""
        packet = self._prepare_packet(data)
        if not packet: return

        # 🚩 Сохраняем пакет для будущих клиентов
        self.last_packet = packet 

        with self.clients_lock:
            disconnected = []
            for conn in list(self.clients):
                try:
                    conn.sendall(packet)
                except:
                    disconnected.append(conn)
            
            for conn in disconnected:
                if conn in self.clients: self.clients.remove(conn)

    def _handle_client(self, conn, addr):
        log.info(f"[{self.name}] Новый клиент: {addr}")
        
        # 🚩 ОТПРАВКА ПОСЛЕДНИХ ДАННЫХ ПРИ ПОДКЛЮЧЕНИИ
        if self.last_packet:
            try:
                conn.sendall(self.last_packet)
                log.info(f"[{self.name}] Кэшированные данные отправлены клиенту {addr}")
            except Exception as e:
                log.error(f"[{self.name}] Ошибка отправки кэша: {e}")
                conn.close()
                return

        with self.clients_lock:
            self.clients.add(conn)
        
        try:
            while True:
                # Держим соединение
                if not conn.recv(1024): break
        except:
            pass
        finally:
            log.info(f"[{self.name}] Клиент отключен: {addr}")
            with self.clients_lock:
                if conn in self.clients: self.clients.remove(conn)
            conn.close()

    def _prepare_packet(self, data):
        try:
            # Если мы передали уже готовую строку (наш JSON-ready-line)
            if isinstance(data, str):
                payload = data.encode('utf-8')
            # Если передан объект (список/словарь) и нужен JSON
            elif self.is_json:
                payload = json.dumps(data).encode('utf-8')
            else:
                payload = data # уже байты
            
            if self.is_zlib:
                payload = zlib.compress(payload)

            return len(payload).to_bytes(4, 'big') + payload
        except Exception as e:
            log.error(f"Ошибка подготовки пакета: {e}")
            return None
    def start(self):
        """Запуск TCP сервера в отдельном потоке"""
        def run():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('localhost', self.port))
                s.listen(10)
                log.info(f"🚀 {self.name} запущен на порту {self.port}")
                while True:
                    conn, addr = s.accept()
                    threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
        
        threading.Thread(target=run, daemon=True).start()
