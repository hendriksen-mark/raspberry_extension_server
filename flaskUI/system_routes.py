"""
System and configuration routes
"""
from flask import request
from typing import Any
from flask_restful import Resource
from werkzeug.security import generate_password_hash
from subprocess import run
import os
import logging
import logManager
from ServerObjects.fan_object import FanObject
from ServerObjects.klok_object import KlokObject
from ServerObjects.powerbutton_object import PowerButtonObject
import configManager
from services.utils import get_pi_temp
from .dht_routes import DHTRoute
from ServerObjects.dht_object import DHTObject
from services.updateManager import githubCheck, githubInstall

# Get logger with proper type hint for IDE syntax highlighting
logger: logging.Logger = logManager.logger.get_logger(__name__)

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config

class SystemRoute(Resource):
    def get(self, resource: str) -> Any:
        """
        Handle GET requests for system resources
        URL: /system/resource
        """
        if resource == 'pi_temp':
            try:
                temp: float = get_pi_temp()
                return {"temperature": temp}, 200
            except RuntimeError as e:
                logger.error(f"Error reading Pi temperature: {e}")
                return {"error": "Could not read Pi temperature"}, 503
            
        elif resource == "dht":
            return DHTRoute().get()
            
        elif resource == "all":
            try:
                getResources: list[str] = ["thermostats", "dht", "klok", "fan", "powerbutton"]
                response = {}
                
                # Handle thermostats (always a dict of objects)
                if "thermostats" in serverConfig:
                    response["thermostats"] = {key: obj.save() for key, obj in serverConfig["thermostats"].items()}
                
                # Handle single objects that might be dicts or objects
                for resource_name in ["dht", "klok", "fan", "powerbutton"]:
                    if resource_name in serverConfig:
                        resource_obj = serverConfig[resource_name]
                        if hasattr(resource_obj, 'save'):
                            response[resource_name] = resource_obj.save()
                        else:
                            # If it's still a dict, return it as is
                            response[resource_name] = resource_obj
                            
                uname = os.uname()
                response["config"] = serverConfig["config"]
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
            except Exception as e:
                logger.error(f"Error getting all system info: {e}")
                return {"error": "Failed to retrieve system information"}, 500
        
        elif resource == "health":
            return health_check()

        elif resource == "config":
            try:
                response = {
                    "config": serverConfig["config"],
                    "thermostats": {key: obj.save() for key, obj in serverConfig["thermostats"].items()} if len(serverConfig.get("thermostats", {})) > 0 else "No Thermostats Configured"
                }
                
                # Handle single objects that might be dicts or objects
                dht_obj: DHTObject = serverConfig.get("dht")
                if dht_obj:
                    response["dht"] = dht_obj.save() if hasattr(dht_obj, 'save') else dht_obj
                else:
                    response["dht"] = "Not Configured"

                klok_obj: KlokObject = serverConfig.get("klok")
                if klok_obj:
                    response["klok"] = klok_obj.save() if hasattr(klok_obj, 'save') else klok_obj
                else:
                    response["klok"] = "Not Configured"

                fan_obj: FanObject = serverConfig.get("fan")
                if fan_obj:
                    response["fan"] = fan_obj.save() if hasattr(fan_obj, 'save') else fan_obj
                else:
                    response["fan"] = "Not Configured"

                powerbutton_obj: PowerButtonObject = serverConfig.get("powerbutton")
                if powerbutton_obj:
                    response["powerbutton"] = powerbutton_obj.save() if hasattr(powerbutton_obj, 'save') else powerbutton_obj
                else:
                    response["powerbutton"] = "Not Configured"

                return response, 200
            except Exception as e:
                logger.error(f"Error getting config: {e}")
                return {"error": "Failed to retrieve configuration"}, 500
        else:
            return {"error": "Resource not found"}, 404
        
    def put(self, resource: str) -> Any:
        putDict: dict[str, Any] = request.get_json(force=True)
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
                logger.info("Change log level to: " + str(logManager.logger.get_level_name()))

def health_check() -> tuple[dict[str, Any], int]:
    """Health check endpoint"""
    dht_obj: DHTObject = serverConfig.get("dht")

    # Handle both dict and object cases for DHT
    if dht_obj and hasattr(dht_obj, 'get_data'):
        logger.info("DHT object found, retrieving data")
        temp, humidity = dht_obj.get_data()
        dht_pin = dht_obj.get_pin() if hasattr(dht_obj, 'get_pin') else None
    else:
        # If it's a dict, extract values directly
        logger.info("DHT object not found or not callable, checking dict")
        logger.debug(f"DHT object content: {dht_obj}")
        temp = dht_obj.get('temperature') if dht_obj else None
        humidity = dht_obj.get('humidity') if dht_obj else None
        dht_pin = dht_obj.get('pin') if dht_obj else None

    return {
        "status": "healthy",
        "version": "1.0.0",
        "thermostats_connected": len(serverConfig.get("thermostats", {})),
        "dht_sensor_active": dht_pin is not None,
        "temperature_available": temp is not None,
        "humidity_available": humidity is not None
    }, 200
