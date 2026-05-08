from variable import ports, components
from socket_server import BaseServer
from subprocess_server import BaseSubprocessServer
import logger

log = logger.setup_logging()
# stop_event = Event()

def run_mouse_and_read_output(stop_event):
    display_server = BaseServer(ports['get_display'], "DisplayServer", is_json=True)
    handler = BaseSubprocessServer(
        server_instance=display_server,
        cmd=[components['services']['display']],
        stop_event=stop_event,
        label="DisplayServer"
    )
    handler.run()

if __name__ == "__main__":
    run_mouse_and_read_output()
