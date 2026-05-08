import re
from variable import ports, components
import variable
import ujson
import logger
from socket_server import BaseServer
log=logger.setup_logging()


def parse_broken_layout(raw_string):
    raw_string = raw_string.replace('\n', '')
    if '"layout":' in raw_string and not re.search(r'"layout":\s*\{', raw_string):
        raw_string = re.sub(r'("layout":\s*)(.*?)(\s*})$', r'\1{\2}\3', raw_string)

    try:
        return ujson.loads(raw_string)
    except ujson.JSONDecodeError:
        raw_string = raw_string.replace('"', '\\"')
        try:
            return ujson.loads(raw_string)
        except Exception as e:
            return f"Error: {e}"
from subprocess_server import BaseSubprocessServer
def run_mouse_and_read_output(stop_event):
    log.info(variable.display)
    key_server = BaseServer(ports['get_key'], "KeyboardServer", is_json=True)
    
    cmd = ["cmd.exe", "/c", components['services']["blocking"], 
           'alt+arrow_left', 'pause', 'left_win', 'left_shift+pause', 'insert']

    class KeyboardHandler(BaseSubprocessServer):
        def parse_line(self, line):
            return parse_broken_layout(line)

    handler = KeyboardHandler(
        server_instance=key_server,
        cmd=cmd,
        stop_event=stop_event, 
        label="KeyboardServer"
    )
    
    handler.run()

if __name__ == "__main__":
    run_mouse_and_read_output()
