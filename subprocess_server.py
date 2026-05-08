import subprocess
import logger 
log=logger.setup_logging()

class BaseSubprocessServer:
    def __init__(self, server_instance, cmd, stop_event, label="Server"):
        self.server = server_instance
        self.cmd = cmd
        self.stop_event = stop_event
        self.label = label
        self.process = None

    def handle_data(self, data):
        if data:
            self.server.broadcast(data) 

    def parse_line(self, line):
        line = line.strip()
        if not line: return None
        return line 
    
    def run(self):
        try:
            self.server.start()
            log.info(f"🚀 {self.label} запущен: {self.cmd}")
            
            self.process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, 
                text=True,
                encoding='utf-8',
                bufsize=1, 
                universal_newlines=True
            )

            while not self.stop_event.is_set():
                if self.process.poll() is not None:
                    log.warning(f"⚠️ Процесс {self.label} неожиданно завершился")
                    break
                line = self.process.stdout.readline()
                
                if line:
                    parsed_data = self.parse_line(line)
                    if parsed_data:
                        self.handle_data(parsed_data)
                
        except Exception as e:
            log.error(f"❌ Ошибка в {self.label}: {e}")
        finally:
            self.cleanup() 
    def cleanup(self):
        log.info(f"🧹 Очистка ресурсов {self.label}...")
        
        if self.process:
            if self.process.poll() is None: 
                self.process.terminate()
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            log.info(f"🛑 Процесс {self.label} остановлен")

        if hasattr(self.server, 'stop'):
            self.server.stop()
        elif hasattr(self.server, 'close'):
            self.server.close()

