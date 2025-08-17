"""
API module with Flask app factory and resource registration
Following diyHue architectural patterns
"""

from fastapi import FastAPI, Body, Response
from fastapi.responses import FileResponse
from typing import Any
import logging
import os
from subprocess import run
import logManager
import configManager

logger: logging.Logger = logManager.logger.get_logger(__name__)

def create_app() -> FastAPI:
    """
    App factory function following diyHue pattern
    """
    app: FastAPI = FastAPI(title="Raspberry Extension Server API", version="1.0.0")

    app.logger = logger

    # Enable CORS
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add favicon handler to prevent thermostat route conflicts
    @app.get("/favicon.ico")
    async def get_favicon():
        root_dir = configManager.serverConfig.runningDir
        favicon_path = os.path.join(root_dir, 'flaskUI', 'templates', 'favicon.ico')
        
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path, media_type='image/x-icon')
        else:
            return Response(status_code=404)  # Not found
        
    @app.get("/save")
    async def save_config(backup: bool = False):
        configManager.serverConfig.save_config(backup=backup)
        return "backup config\n" if backup else "config saved\n"
    @app.get("/reset_config")
    async def reset_config():
        configManager.serverConfig.reset_config()
        return "config reset\n"
    @app.get("/restore_config")
    async def restore_config():
        configManager.serverConfig.restore_backup()
        return "restore config\n"
    @app.get("/download_config")
    async def download_config():
        path: str = configManager.serverConfig.download_config()
        return FileResponse(path)
    @app.get("/download_log")
    async def download_log():
        path: str = configManager.serverConfig.download_log()
        return FileResponse(path)
    @app.get("/download_debug")
    async def download_debug():
        path: str = configManager.serverConfig.download_debug()
        return FileResponse(path)
    @app.get("/restart")
    async def restart():
        configManager.serverConfig.restart_python()
        return "restart python with args"
    @app.get("/info")
    async def info():
        uname: os.uname_result = os.uname()
        stat_flag = "-c %y" if uname.sysname == "Linux" else "-f %Sm"
        server_cmd = f"stat {stat_flag} {configManager.serverConfig.runningDir}/api.py"
        webui_cmd = f"stat {stat_flag} {configManager.serverConfig.runningDir}/flaskUI/templates/index.html"
        return {
            "sysname": uname.sysname,
            "machine": uname.machine,
            "os_version": uname.version,
            "os_release": uname.release,
            "server": run(server_cmd, shell=True, capture_output=True, text=True).stdout.strip(),
            "webui": run(webui_cmd, shell=True, capture_output=True, text=True).stdout.strip()
        }

    # Register other routes
    from .system_routes import SystemRoute
    from .dht_routes import DHTRoute
    from .thermostat_routes import ThermostatRoute
    from .klok_routes import KlokRoute
    from .config_routes import ConfigRoute
    from .fan_routes import FanRoute
    from .powerbutton_routes import PowerButtonRoute
    
    @app.get("/system")
    @app.get("/system/{resource}")
    async def get_system(response: Response, resource: str = None):
        response_data, response_code = SystemRoute().get(resource)
        response.status_code = response_code
        return response_data

    @app.get("/dht")
    @app.get("/dht/{resource}")
    async def get_dht(response: Response, resource: str = None):
        response_data, response_code = DHTRoute().get(resource)
        response.status_code = response_code
        return response_data
    @app.post("/dht")
    @app.post("/dht/{resource}")
    async def post_dht(response: Response, resource: str = None, data: dict[str, Any] = Body(default={})):
        response_data, response_code = DHTRoute().post(resource, data)
        response.status_code = response_code
        return response_data
    @app.delete("/dht")
    @app.delete("/dht/{resource}")
    async def delete_dht(response: Response, resource: str = None):
        response_data, response_code = DHTRoute().delete(resource)
        response.status_code = response_code
        return response_data

    @app.get("/{mac}")
    @app.get("/{mac}/{resource}")
    @app.get("/{mac}/{resource}/{value}")
    async def get_thermostat(response: Response, mac: str, resource: str = None, value: str = None):
        response_data, response_code = await ThermostatRoute().get(mac, resource, value)
        response.status_code = response_code
        return response_data
    @app.post("/{mac}")
    @app.post("/{mac}/{resource}")
    async def post_thermostat(response: Response, mac: str, resource: str = None, data: dict[str, Any] = Body(default={})):
        response_data, response_code = await ThermostatRoute().post(mac, resource, data)
        response.status_code = response_code
        return response_data
    @app.delete("/{mac}")
    @app.delete("/{mac}/{resource}")
    async def delete_thermostat(response: Response, mac: str, resource: str = None):
        response_data, response_code = await ThermostatRoute().delete(mac, resource)
        response.status_code = response_code
        return response_data

    @app.get("/klok")
    @app.get("/klok/{resource}")
    @app.get("/klok/{resource}/{value}")
    async def get_klok(response: Response, resource: str = None, value: str = None):
        response_data, response_code = KlokRoute().get(resource, value)
        response.status_code = response_code
        return response_data
    @app.post("/klok")
    @app.post("/klok/{resource}")
    @app.post("/klok/{resource}/{value}")
    async def post_klok(response: Response, resource: str = None, value: str = None, data: dict[str, Any] = Body(default={})):
        response_data, response_code = KlokRoute().post(resource, value, data)
        response.status_code = response_code
        return response_data
    @app.delete("/klok")
    async def delete_klok(response: Response):
        response_data, response_code = KlokRoute().delete()
        response.status_code = response_code
        return response_data

    @app.get("/config")
    @app.get("/config/{resource}")
    async def get_config(response: Response, resource: str = None):
        response_data, response_code = ConfigRoute().get(resource)
        response.status_code = response_code
        return response_data
    @app.put("/config")
    @app.put("/config/{resource}")
    async def put_config(response: Response, resource: str = None, data: dict[str, Any] = Body(default={})):
        response_data, response_code = ConfigRoute().put(resource, data)
        response.status_code = response_code
        return response_data

    @app.get("/fan")
    @app.get("/fan/{resource}")
    async def get_fan(response: Response, resource: str = None):
        response_data, response_code = FanRoute().get(resource)
        response.status_code = response_code
        return response_data
    @app.post("/fan")
    @app.post("/fan/{resource}")
    async def post_fan(response: Response, resource: str = None, data: dict[str, Any] = Body(default={})):
        response_data, response_code = FanRoute().post(resource, data)
        response.status_code = response_code
        return response_data
    @app.delete("/fan")
    @app.delete("/fan/{resource}")
    async def delete_fan(response: Response, resource: str = None):
        response_data, response_code = FanRoute().delete(resource)
        response.status_code = response_code
        return response_data

    @app.get("/powerbutton")
    @app.get("/powerbutton/{resource}")
    async def get_powerbutton(response: Response, resource: str = None):
        response_data, response_code = PowerButtonRoute().get(resource)
        response.status_code = response_code
        return response_data
    @app.post("/powerbutton")
    @app.post("/powerbutton/{resource}")
    async def post_powerbutton(response: Response, resource: str = None, data: dict[str, Any] = Body(default={})):
        response_data, response_code = PowerButtonRoute().post(resource, data)
        response.status_code = response_code
        return response_data
    @app.delete("/powerbutton")
    @app.delete("/powerbutton/{resource}")
    async def delete_powerbutton(response: Response, resource: str = None):
        response_data, response_code = PowerButtonRoute().delete(resource)
        response.status_code = response_code
        return response_data

    return app
