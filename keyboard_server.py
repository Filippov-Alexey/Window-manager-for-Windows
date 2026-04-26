import re
from variable import ports, tools
import json
import subprocess
import datetime
from threading import Thread, Event
import logger
from socket_server import BaseServer
log=logger.setup_logging()

stop_event = Event()

def parse_broken_layout(raw_string):
    raw_string = raw_string.replace('\n', '')
    if '"layout":' in raw_string and not re.search(r'"layout":\s*\{', raw_string):
        raw_string = re.sub(r'("layout":\s*)(.*?)(\s*})$', r'\1{\2}\3', raw_string)

    try:
        return json.loads(raw_string)
    except json.JSONDecodeError:
        raw_string = raw_string.replace('"', '\\"')
        try:
            return json.loads(raw_string)
        except Exception as e:
            return f"Error: {e}"
import datetime
from subprocess_server import BaseSubprocessServer
def run_mouse_and_read_output():
    key_server = BaseServer(ports['get_key'], "KeyboardServer", is_json=True)
    
    cmd = ["cmd.exe", "/c", tools["blocking"], 'alt+arrow_left', 'pause', 'left_win', 'left_shift+pause', 'insert']

    class KeyboardHandler(BaseSubprocessServer):
        def parse_line(self, line):
            return parse_broken_layout(line)

        def run(self):
            with open('log.txt', 'a+') as f:
                f.write(f'{datetime.datetime.now()} => start\n')
            
            super().run()

    handler = KeyboardHandler(
        server_instance=key_server,
        cmd=cmd,
        stop_event=stop_event,
        label="KeyboardServer"
    )
    
    handler.run()

if __name__ == "__main__":
    # Thread(target=run_server).start()
    while True:
        run_mouse_and_read_output()
