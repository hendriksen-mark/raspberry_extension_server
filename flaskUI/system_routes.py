"""
System and configuration routes
"""
from flask import request
from typing import Any
from flask_restful import Resource
from werkzeug.security import generate_password_hash
from subprocess import run
import os
import logManager
import configManager
from services.utils import get_pi_temp
from .dht_routes import DHTRoute
from ServerObjects.dht_object import DHTObject
from services.updateManager import githubCheck, githubInstall

logging = logManager.logger.get_logger(__name__)

serverConfig = configManager.serverConfig.yaml_config

class SystemRoute(Resource):
    def get(self, resource: str) -> Any:
        """
        Handle GET requests for system resources
        URL: /system/resource
        """
        if resource == 'pi_temp':
            try:
                temp = get_pi_temp()
                return {"temperature": temp}, 200
            except RuntimeError as e:
                logging.error(f"Error reading Pi temperature: {e}")
                return {"error": "Could not read Pi temperature"}, 503
            
        elif resource == "dht":
            return DHTRoute().get()
            
        elif resource == "all":
            getResources = ["thermostats", "dht", "klok", "fan", "powerbutton"]
            response = {
                resource: {key: obj.save() for key, obj in serverConfig[resource].items()} for resource in getResources
            }
            uname = os.uname()
            response["config"].update(serverConfig["config"])
            response["pi_temp"] = get_pi_temp()
            response["info"] = {
                    "sysname": uname.sysname,
                    "machine": uname.machine,
                    "os_version": uname.version,
                    "os_release": uname.release,
                    "server": run("stat -c %y api.py", shell=True, capture_output=True, text=True).stdout.strip(),
                    "webui": run("stat -c %y flaskUI/templates/index.html", shell=True, capture_output=True, text=True).stdout.strip()
                }
            return response
        
        elif resource == "health":
            return health_check()
        else:
            return {"error": "Resource not found"}, 404
        
    def put(self, resource: str) -> Any:
            putDict = request.get_json(force=True)
            if resource == "config":
                if "swupdate2" in putDict:
                    if "checkforupdate" in putDict["swupdate2"] and putDict["swupdate2"]["checkforupdate"] == True:
                        githubCheck()
                    if "install" in putDict["swupdate2"] and putDict["swupdate2"]["install"] == True:
                        githubInstall()
                if "users" in putDict:
                    for key, value in putDict["users"].items():
                        for email, hash in serverConfig["config"]["users"].items():
                            if putDict["users"][key] == serverConfig["config"]["users"][email]:
                                serverConfig["config"]["users"][email]["password"] = generate_password_hash(str(value['password']))
                if "loglevel" in putDict:
                    logManager.logger.configure_logger(putDict["loglevel"])
                    logging.info("Change log level to: " + str(logManager.logger.get_level_name()))

def health_check() -> Any:
    """Health check endpoint"""
    dht: DHTObject = serverConfig["dht"]
    temp, humidity = dht.get_data()

    return {
        "status": "healthy",
        "version": "1.0.0",
        "thermostats_connected": len(serverConfig["thermostats"]),
        "dht_sensor_active": dht.get_pin() is not None,
        "temperature_available": temp is not None,
        "humidity_available": humidity is not None
    }, 200
