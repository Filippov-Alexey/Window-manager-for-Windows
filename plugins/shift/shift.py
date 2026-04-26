from socket_client import BaseSocketClient
import time
from variable import *
import socket, threading,json,subprocess,queue
import ctypes
from ctypes import wintypes
import logger
log=logger.setup_logging()

user32 = ctypes.windll.user32

def get_layout_string(hkl_hex):
    hkl = int(hkl_hex, 16)
    chars = ""
    for shift_state in [0, 1]:
        keystate = (wintypes.BYTE * 256)()
        if shift_state:
            keystate[0x10] = 0x80  
        for vk in range(0x20, 0xDF):
            buf = ctypes.create_unicode_buffer(5)
            scancode = user32.MapVirtualKeyExW(vk, 0, hkl)
            res = user32.ToUnicodeEx(vk, scancode, keystate, buf, len(buf), 0, hkl)
            if res > 0:
                chars += buf.value
    return chars



class shift:
    def __init__(self, canvas, root, w, rect):
        self.root = root
        self.canvas = canvas
        self.string = ''
        self.last_shift_time = 0
        self.double_tap_timeout = 8
        
        # 🟢 Ограничиваем очередь, чтобы избежать накопления задач в ОЗУ
        self.task_queue = queue.Queue(maxsize=100) 

        # 🟢 Инициализируем клиент (порт get_key, работа с JSON)
        self.client = BaseSocketClient(ports['get_key'], "Shift-Key")

        # Запускаем потоки
        threading.Thread(target=self.run_listener, daemon=True).start()
        threading.Thread(target=self.process_tasks, daemon=True).start()

    def run_listener(self):
        """
        Использует универсальный цикл. 
        При переполнении очереди старые события будут вытесняться.
        """
        def safe_put(msg):
            try:
                if self.task_queue.full():
                    self.task_queue.get_nowait()
                self.task_queue.put_nowait(msg)
            except Exception:
                pass

        self.client.run_loop(handler=safe_put)

    def process_tasks(self):
        while True:
            try:
                # Извлекаем сообщение из очереди (блокирующее ожидание)
                msg = self.task_queue.get()
                key = msg.get('key_name')
                chars = msg.get('key', '')
                status = msg.get('status')
                layout = msg.get('layout')

                if status == 'Up':
                    if key.lower().endswith('shift'):
                        current_time = time.time()
                        if current_time - self.last_shift_time < self.double_tap_timeout:
                            self.handle_double_shift(layout)
                            self.last_shift_time = 0
                        else:
                            self.last_shift_time = current_time
                    else:
                        self.last_shift_time = 0
                else:
                    if len(chars) > 0:
                        if chars in [' ', 'return']:
                            self.string = ''
                        else:
                            self.string += chars
            except Exception as e:
                log.error(f"Ошибка при обработке задачи: {e}")

    def handle_double_shift(self, layout):
        with subprocess.Popen([tools["buffer"]], stdout=subprocess.PIPE, text=True, encoding='utf-8') as proc:
            subprocess.run([tools['press'], '_ctrl+x'])
            raw_output = proc.stdout.read().strip('\x00')
        if not raw_output:
            raw_output = self.string
            for _ in self.string:
                subprocess.run([tools['press'], 'backspace'])
        buf = raw_output[:-1].replace('\n', '\xf9').replace('    ', '\xf8').rstrip('\n')
        eng_chars = get_layout_string(layout.get('HKL'))
        rus_chars = get_layout_string(get_next_layout_hkl(layout.get('HKL'))[0])
        text = buf.translate(str.maketrans(eng_chars, rus_chars))
        subprocess.run([tools['write'], text])
    def run(self):
        pass
