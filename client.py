import threading
import logging
import time
import socket
from variable import ports

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(threadName)-10s %(asctime)s - %(levelname)s - %(message)s',filename='log.log')
logger = logging.getLogger(__name__)

# Список портов для постоянного мониторинга
MONITORING_PORTS = [ports['get_win'], ports['is_full_win']]
INTERVAL_SECONDS = 1  # Интервал проверки каждые 5 секунд

def connect_and_receive(port):
    """
    Функция, которая пытается установить соединение с указанным портом,
    читает данные и регистрирует результат.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.connect(('localhost', port))
            logger.info(f"Thread-{port}: Successfully connected to localhost:{port}.")
            
            # Читаем данные от сервера
            data = sock.recv(2048).decode(encoding='Unicode Escape',errors='replace').strip()
            
            if not data:
                logger.warning(f"Thread-{port}: No valid data received.")
            else:
                logger.info(f"Thread-{port}: Received data: {data}")
                
        except OSError as err:
            logger.error(f"Thread-{port}: Connection attempt failed: {err}")

def monitor_ports():
    """
    Бесконечный цикл, который мониторит указанные порты с заданным интервалом.
    """
    while True:
        for port in MONITORING_PORTS:
            thread = threading.Thread(target=connect_and_receive, args=(port,))
            thread.start()
            thread.join()  # Ожидаем завершение текущего потока перед следующим
        time.sleep(INTERVAL_SECONDS)

def main():
    """
    Основная логика программы.
    Сначала подключаемся к порту ports['get_key'], затем запускаем мониторинг остальных портов.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        try:
            client_socket.connect(('localhost', ports['get_key']))  # Основной порт
            logger.info("Main Thread: Connected to server on port ports['get_key'].")
            
            # Запускаем постоянный мониторинг других портов
            monitoring_thread = threading.Thread(target=monitor_ports)
            monitoring_thread.daemon = True  # Устанавливаем демон-флаг, чтобы поток завершался вместе с программой
            monitoring_thread.start()
            
            # Теперь продолжаем получать данные с основного порта
            while True:
                data = client_socket.recv(1024).decode('utf-8', errors='replace').strip()
                if not data:
                    break
                logger.info(f"Received from port ports['get_key']: {data}")
            
        except OSError as err:
            logger.error(f"Main Thread: Connection failed: {err}")

if __name__ == "__main__":
    main()
