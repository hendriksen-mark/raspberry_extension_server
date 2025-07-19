#!/usr/bin/env python3
"""
Main entry point for the Eqiva Smart Radiator Thermostat API
"""
import logging
import logManager
logManager.logger.enable_file_logging()
import configManager
from threading import Thread
import os
import signal
from typing import Any
from flask import Flask
from werkzeug.serving import WSGIRequestHandler
from flaskUI import create_app
from services import scheduler, stateFetch, updateManager, LogWS

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config
logger: logging.Logger = logManager.logger.get_logger(__name__)
werkzeug_logger: logging.Logger = logManager.logger.get_logger("werkzeug")
cherrypy_logger: logging.Logger = logManager.logger.get_logger("cherrypy")
WSGIRequestHandler.protocol_version = "HTTP/1.1"

# Create app using factory pattern (diyHue style)
app: Flask = create_app(serverConfig)

def runHttp(BIND_IP: str, HOST_HTTP_PORT: int) -> None:
    logger.debug(f"Starting Flask server on {BIND_IP}:{HOST_HTTP_PORT}")
    app.run(host=BIND_IP, port=HOST_HTTP_PORT)

def handle_exit(signum: int, frame: Any) -> None:
    """Handle exit signals"""
    logger.info(f"Received signal {signum} on {frame}, shutting down gracefully...")
    stateFetch.disconnectThermostats()
    os._exit(0)


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown"""
    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

def main():
    setup_signal_handlers()
    BIND_IP: str = configManager.runtimeConfig.arg["BIND_IP"]
    HOST_HTTP_PORT: int = configManager.runtimeConfig.arg["HTTP_PORT"]
    updateManager.startupCheck()

    Thread(target=stateFetch.syncWithThermostats_threaded).start()
    Thread(target=stateFetch.read_dht_temperature).start()
    Thread(target=stateFetch.run_fan_service).start()
    Thread(target=stateFetch.run_klok_service).start()
    Thread(target=scheduler.runScheduler).start()
    Thread(target=LogWS.start_ws_server).start()
    runHttp(BIND_IP, HOST_HTTP_PORT)

if __name__ == '__main__':
    main()
