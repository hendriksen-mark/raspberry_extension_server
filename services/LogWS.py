from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
import cherrypy
import threading
import time
import logging
import logManager
import configManager

logger: logging.Logger = logManager.logger.get_logger(__name__)
serverConfig = configManager.serverConfig.yaml_config

LOG_FILE = str(serverConfig["config"]["runningDir"] + "/diyhue.log")

class LogWebSocketHandler(WebSocket):
    def opened(self) -> None:
        self._running: bool = True
        self._thread: threading.Thread = threading.Thread(target=self.tail_log)
        self._thread.daemon = True
        self._thread.start()

    def closed(self, code, reason=None) -> None:
        self._running = False

    def tail_log(self) -> None:
        try:
            with open(LOG_FILE) as f:
                f.seek(0, 2)
                while self._running:
                    line: str = f.readline()
                    if line:
                        try:
                            self.send(line)
                        except Exception as e:
                            logger.error(f"Error sending log line: {e}")
                            break
                    else:
                        time.sleep(0.5)
        except Exception as e:
            logger.error(f"Error tailing log file: {e}")

cherrypy.config.update({'server.socket_host': '0.0.0.0', 'server.socket_port': 9000})
WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()

class Root(object):
    @cherrypy.expose
    def index(self) -> str:
        return "WebSocket log server running."

    @cherrypy.expose
    def ws(self) -> None:
        pass  # ws4py handles this

def start_ws_server() -> None:
    cherrypy.quickstart(Root(), '/', config={
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': LogWebSocketHandler
        }
    })
