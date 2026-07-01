"""
System and configuration routes
"""
from typing import Any
import os
import logging
from datetime import datetime, timezone
from flask_restful import Resource

import logManager
from server_objects.thermostat_object import ThermostatObject
from server_objects.fan_object import FanObject
from server_objects.klok_object import KlokObject
from server_objects.powerbutton_object import PowerButtonObject
from server_objects.dht_object import DHTObject
import config_manager
from services.utils import get_pi_temp

logger: logging.Logger = logManager.logger.get_logger(__name__)

SERVER_CONFIG: dict[str, Any] = config_manager.SERVER_CONFIG.yaml_config

class SystemRoute(Resource):
    def get(self, resource: str | None = None) -> tuple[dict[str, Any], int]:
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
                response: dict[str, Any] = {}

                # Handle thermostats (always a dict of objects)
                if "thermostats" in SERVER_CONFIG:
                    response["thermostats"] = {key: obj.get_all_data() for key, obj in SERVER_CONFIG["thermostats"].items() if isinstance(obj, ThermostatObject)}

                # Handle single objects that might be dicts or objects
                for resource_name in ["dht", "klok", "powerbutton"]:
                    if resource_name in SERVER_CONFIG:
                        resource_obj: Any = SERVER_CONFIG[resource_name]
                        if hasattr(resource_obj, 'get_all_data'):
                            response[resource_name] = resource_obj.get_all_data()
                        elif hasattr(resource_obj, 'save'):
                            response[resource_name] = resource_obj.save()
                        else:
                            response[resource_name] = resource_obj

                # Handle fans (dict of FanObjects)
                if "fan" in SERVER_CONFIG:
                    response["fan"] = {fid: f.get_all_data() for fid, f in SERVER_CONFIG["fan"].items() if isinstance(f, FanObject)}

                uname = os.uname()
                response["config"] = SERVER_CONFIG["config"]
                response["pi_temp"] = get_pi_temp() if uname.sysname == "Linux" else "Unsupported OS"

                # Build stat command based on OS (unused, using os.stat directly)
                server_file = f"{config_manager.SERVER_CONFIG.runningDir}/api.py"
                webui_file = f"{config_manager.SERVER_CONFIG.runningDir}/flask_ui/templates/index.html"

                response["info"] = {
                        "sysname": uname.sysname,
                        "machine": uname.machine,
                        "os_version": uname.version,
                        "os_release": uname.release,
                        "server": datetime.fromtimestamp(os.stat(server_file).st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                        "webui": datetime.fromtimestamp(os.stat(webui_file).st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    }
                return response, 200
            except Exception as e:
                logger.error(f"Error getting all system info: {e}")
                return {"error": "Failed to retrieve system information"}, 500

        elif resource == "health":
            return health_check()

        elif resource == "config":
            try:
                response: dict[str, Any] = {
                    "config": SERVER_CONFIG["config"],
                    "thermostats": {key: obj.save() for key, obj in SERVER_CONFIG["thermostats"].items() if isinstance(obj, ThermostatObject)} if len(SERVER_CONFIG.get("thermostats", {})) > 0 else "No Thermostats Configured",
                    "fan": {fid: f.save() for fid, f in SERVER_CONFIG.get("fan", {}).items() if isinstance(f, FanObject)} if len(SERVER_CONFIG.get("fan", {})) > 0 else "No Fans Configured"
                }

                # Handle single objects that might be dicts or objects
                dht_obj: DHTObject | None = SERVER_CONFIG.get("dht")
                if dht_obj:
                    response["dht"] = dht_obj.save() if hasattr(dht_obj, 'save') else dht_obj
                else:
                    response["dht"] = "Not Configured"

                klok_obj: KlokObject | None = SERVER_CONFIG.get("klok")
                if klok_obj:
                    response["klok"] = klok_obj.save() if hasattr(klok_obj, 'save') else klok_obj
                else:
                    response["klok"] = "Not Configured"

                powerbutton_obj: PowerButtonObject | None = SERVER_CONFIG.get("powerbutton")
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
    dht_obj: DHTObject | None = SERVER_CONFIG.get("dht")

    # Handle both dict and object cases for DHT
    if hasattr(dht_obj, 'get_data'):
        logger.info("DHT object found, retrieving data")
        temp, humidity = dht_obj.get_data() if dht_obj and hasattr(dht_obj, 'get_data') else (None, None)
        dht_pin: int | None = dht_obj.get_pin() if dht_obj and hasattr(dht_obj, 'get_pin') else None
    else:
        # Fallback if object not properly initialized
        logger.info("DHT object not properly initialized")
        temp: float | None = None
        humidity: float | None = None
        dht_pin: int | None = None

    return {
        "status": "healthy",
        "version": "1.0.0",
        "thermostats_connected": len(SERVER_CONFIG.get("thermostats", {})),
        "dht_sensor_active": dht_pin is not None,
        "temperature_available": temp is not None,
        "humidity_available": humidity is not None
    }, 200
