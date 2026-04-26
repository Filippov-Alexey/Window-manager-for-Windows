import socket, json, zlib, time, gc
import logger

log=logger.setup_logging()

class BaseSocketClient:
    def __init__(self, port, name, is_json=True, is_zlib=False):
        self.port = port
        self.name = name
        self.is_json = is_json
        self.is_zlib = is_zlib

    def _recv_full(self, sock, length):
        data = bytearray() 
        while len(data) < length:
            chunk = sock.recv(min(length - len(data), 65536))
            if not chunk: return None
            data.extend(chunk)
        return data

    def run_loop(self, handler, init_msg=None):
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('localhost', self.port))
                    if init_msg: s.sendall(init_msg)
                    while True:
                        head = self._recv_full(s, 4)
                        if not head: break
                        size = int.from_bytes(head, 'big')
                        
                        body = self._recv_full(s, size)
                        if not body: break
                        
                        if self.is_zlib:
                            body = zlib.decompress(body)
                        
                        if self.is_json:
                            try:
                                decoded_body = body.decode('utf-8', errors='replace')
                                if not decoded_body: continue
                                
                                res = json.loads(decoded_body)
                                handler(res)
                            except json.JSONDecodeError as je:
                                log.error(f"[{self.name}] JSON Error: {je} | Data snippet: {decoded_body[:100]}")
                        else:
                            handler(body)

                        body = None
                        res = None
                        
            except Exception as e:
                log.error(f"[{self.name}] Error: {e}")
                time.sleep(2)
            finally:
                gc.collect()

    def request(self, init_msg=None):
        res = None
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
                res = json.loads(body.decode('utf-8', errors='replace')) if self.is_json else body
                return res
        except Exception:
            return None
        finally:
            body = None
            gc.collect()
