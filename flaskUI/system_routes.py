"""
System and configuration routes
"""
from typing import Any
from flask_restful import Resource
from subprocess import run
import os
import logging
import logManager
from ServerObjects.fan_object import FanObject
from ServerObjects.klok_object import KlokObject
from ServerObjects.powerbutton_object import PowerButtonObject
from ServerObjects.dht_object import DHTObject
import configManager
from services.utils import get_pi_temp

logger: logging.Logger = logManager.logger.get_logger(__name__)

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config

class SystemRoute(Resource):
    def get(self, resource: str = None) -> tuple[dict[str, Any], int]:
        """
        Handle GET requests for system resources
        URL: /system/ or /system/resource
        """
        if resource == 'pi_temp':
            try:
                temp: float = get_pi_temp()
                return {"temperature": temp}, 200
            except RuntimeError as e:
                logger.error(f"Error reading Pi temperature: {e}")
                return {"error": "Could not read Pi temperature"}, 503
            
        elif resource == "all":
            try:
                getResources: list[str] = ["thermostats", "dht", "klok", "fan", "powerbutton"]
                response: dict[str, Any] = {}
                
                # Handle thermostats (always a dict of objects)
                if "thermostats" in serverConfig:
                    response["thermostats"] = {key: obj.get_all_data() for key, obj in serverConfig["thermostats"].items()}
                
                # Handle single objects that might be dicts or objects
                for resource_name in ["dht", "klok", "fan", "powerbutton"]:
                    if resource_name in serverConfig:
                        resource_obj: dict[str, Any] = serverConfig[resource_name]
                        if hasattr(resource_obj, 'get_all_data'):
                            response[resource_name] = resource_obj.get_all_data()
                        elif hasattr(resource_obj, 'save'):
                            response[resource_name] = resource_obj.save()
                        else:
                            # If it's still a dict, return it as is
                            response[resource_name] = resource_obj
                            
                uname = os.uname()
                response["config"] = serverConfig["config"]
                response["pi_temp"] = get_pi_temp() if uname.sysname == "Linux" else "Unsupported OS"
                
                # Build stat command based on OS
                stat_flag = "-c %y" if uname.sysname == "Linux" else "-f %Sm"
                server_cmd = f"stat {stat_flag} {configManager.serverConfig.runningDir}/api.py"
                webui_cmd = f"stat {stat_flag} {configManager.serverConfig.runningDir}/flaskUI/templates/index.html"

                response["info"] = {
                        "sysname": uname.sysname,
                        "machine": uname.machine,
                        "os_version": uname.version,
                        "os_release": uname.release,
                        "server": run(server_cmd, shell=True, capture_output=True, text=True).stdout.strip(),
                        "webui": run(webui_cmd, shell=True, capture_output=True, text=True).stdout.strip()
                    }
                return response
            except Exception as e:
                logger.error(f"Error getting all system info: {e}")
                return {"error": "Failed to retrieve system information"}, 500
        
        elif resource == "health":
            return health_check()

        elif resource == "config":
            try:
                response: dict[str, Any] = {
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

def health_check() -> tuple[dict[str, Any], int]:
    """Health check endpoint"""
    dht_obj: DHTObject = serverConfig.get("dht")

    # Handle both dict and object cases for DHT
    if dht_obj and hasattr(dht_obj, 'get_data'):
        logger.info("DHT object found, retrieving data")
        temp, humidity = dht_obj.get_data()
        dht_pin: int | None = dht_obj.get_pin() if hasattr(dht_obj, 'get_pin') else None
    else:
        # If it's a dict, extract values directly
        logger.info("DHT object not found or not callable, checking dict")
        logger.debug(f"DHT object content: {dht_obj}")
        temp: float | None = dht_obj.get('temperature') if dht_obj else None
        humidity: float | None = dht_obj.get('humidity') if dht_obj else None
        dht_pin: int | None = dht_obj.get('pin') if dht_obj else None

    return {
        "status": "healthy",
        "version": "1.0.0",
        "thermostats_connected": len(serverConfig.get("thermostats", {})),
        "dht_sensor_active": dht_pin is not None,
        "temperature_available": temp is not None,
        "humidity_available": humidity is not None
    }, 200
