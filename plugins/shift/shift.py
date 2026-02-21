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
        
        self.task_queue = queue.Queue()

        threading.Thread(target=self.listen_keyboard, daemon=True).start()
        
        threading.Thread(target=self.process_tasks, daemon=True).start()

    def listen_keyboard(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect(('localhost', ports['get_key']))
            log.info("Соединение с клавиатурой установлено")
            try:
                while True:
                    m = s.recv(4).decode('utf-8', errors='replace')
                    data = s.recv(int(m))
                    msg = json.loads(data)
                    self.task_queue.put(msg)
            except Exception as e:
                log.error(f"Ошибка сокета клавиатуры: {e}, реконнект...")
                time.sleep(1)

    def process_tasks(self):
        """Отработка тяжелых команд: subprocess и работа с окнами"""
        while True:
            try:
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
                    # Логика накопления строки
                    if len(chars) > 0:
                        if chars in [' ', 'return']:
                            self.string = ''
                        else:
                            self.string += chars
            except Exception as e:
                log.error(f"Ошибка при обработке задачи: {e}")

    def handle_double_shift(self, layout):
        log.info("Двойной Shift! ")
        with subprocess.Popen(["buffer.exe"], stdout=subprocess.PIPE, text=True, encoding='utf-8') as proc:
            subprocess.run(['press.exe', '_ctrl+x'])
            raw_output = proc.stdout.read().strip('\x00')
        
        if not raw_output:
            raw_output = self.string
            for _ in self.string:
                subprocess.run(['press.exe', 'backspace'])
        buf = raw_output[:-1].replace('\n', '\xf9').replace('    ', '\xf8').rstrip('\n')
        eng_chars = get_layout_string(layout.get('HKL'))
        rus_chars = get_layout_string(get_next_layout_hkl(layout.get('ID')))
        text = buf.translate(str.maketrans(eng_chars, rus_chars))
        subprocess.run(['write.exe', text])

    def run(self):
        self.root.after(100, self.run)
