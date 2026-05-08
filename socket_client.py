import socket, ujson, zlib, time, gc,threading
import logger

log = logger.setup_logging()

class BaseSocketClient:
    def __init__(self, port, name, stop_event=None, is_json=True, is_zlib=False):
        self.port = port
        self.name = name
        self.is_json = is_json
        self.is_zlib = is_zlib
        self.stop_event=stop_event
        self._last_received_data = None 
        self.stop_event = threading.Event() 

    def _recv_full(self, sock, length):
        data = bytearray() 
        while len(data) < length:
            try:
                chunk = sock.recv(min(length - len(data), 65536))
                if not chunk: return None
                data.extend(chunk)
            except socket.timeout:
                if self.stop_event.is_set(): return None
                continue
        return data

    def run_loop(self, handler, init_msg=None, stop_event=None):
        if stop_event is not None:
            self.stop_event = stop_event
        while not self.stop_event.is_set():
            try:
                self._last_received_data = None 
                
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(2.0)
                    s.connect(('localhost', self.port))
                    log.info(f"[{self.name}] Подключено")
                    
                    if init_msg: s.sendall(init_msg)
                    
                    while not self.stop_event.is_set():
                        head = self._recv_full(s, 4)
                        if not head: break
                        
                        size = int.from_bytes(head, 'big')
                        body = self._recv_full(s, size)
                        if not body: break
                        
                        if self.is_zlib:
                            body = zlib.decompress(body)
                        
                        res = None
                        if self.is_json:
                            try:
                                res = ujson.loads(body.decode('utf-8', errors='replace'))
                            except ujson.JSONDecodeError:
                                continue
                        else:
                            res = body

                        if res != self._last_received_data:
                            handler(res)
                            self._last_received_data = res
                        
                        body = None
                        res = None
                        
            except (ConnectionResetError, ConnectionRefusedError):
                time.sleep(2)
            except Exception as e:
                log.error(f"[{self.name}] Ошибка: {e}")
                time.sleep(2)
            finally:
                gc.collect()

    def request(self, init_msg=None):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect(('localhost', self.port))
                if init_msg: s.sendall(init_msg)
                head = self._recv_full(s, 4)
                if not head: return None
                size = int.from_bytes(head, 'big')
                body = self._recv_full(s, size)
                if self.is_zlib: body = zlib.decompress(body)
                return ujson.loads(body.decode('utf-8', errors='replace')) if self.is_json else body
        except: return None
        finally: gc.collect()
