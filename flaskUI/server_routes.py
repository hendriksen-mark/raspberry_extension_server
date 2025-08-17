from fastapi import FastAPI, Response
from fastapi.responses import FileResponse
import os
from subprocess import run
import configManager

def register_server_routes(app: FastAPI, favicon_path: str):
    @app.get("/favicon.ico")
    async def get_favicon():
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