import subprocess
import time
import logger  # Предполагается наличие вашего логгера
log=logger.setup_logging()
class BaseSubprocessServer:
    def __init__(self, server_instance, cmd, stop_event, label="Server"):
        self.server = server_instance
        self.cmd = cmd
        self.stop_event = stop_event
        self.label = label
        self.process = None

    def parse_line(self, line):
        """Переопределите этот метод для трансформации данных перед отправкой"""
        return line.strip()

    def handle_data(self, data):
        """Переопределите, если данные нужно не только транслировать (broadcast)"""
        if data:
            self.server.broadcast(data)

    def run(self):
        self.server.start()
        try:
            log.info(f"🚀 {self.label} запущен: {self.cmd}")
            self.process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                bufsize=1
            )

            while not self.stop_event.is_set():
                line = self.process.stdout.readline()
                
                if not line:
                    if self.process.poll() is not None:
                        break
                    time.sleep(0.01)
                    continue

                parsed_data = self.parse_line(line)
                if parsed_data:
                    self.handle_data(parsed_data)

        except Exception as e:
            log.error(f"❌ Ошибка в {self.label}: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        if self.process:
            self.process.kill()
            log.info(f"🛑 Процесс {self.label} остановлен")
