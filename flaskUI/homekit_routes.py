"""
HomeKit/Homebridge compatible routes
"""
from flask import request
from bleak import BleakError
from typing import Any
from flask_restful import Resource
import logManager
import configManager

from services.utils import validate_mac_address, format_mac, nextFreeId
from ServerObjects.thermostat_object import ThermostatObject

logging = logManager.logger.get_logger(__name__)

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config

def find_thermostat(mac: str) -> Any:
    """
    Find thermostat by MAC address
    """
    for thermostat in serverConfig["thermostats"].values():
        thermostat: ThermostatObject = thermostat
        if thermostat.mac.lower() == mac.lower():
            return thermostat
    data: dict[str, Any] = {"mac": mac}
    data["id"] = nextFreeId(serverConfig, "thermostats")
    serverConfig["thermostats"][data["id"]] = ThermostatObject(data)
    return serverConfig["thermostats"][data["id"]]

class ThermostatRoute(Resource):
    def get(self, mac, resource) -> tuple[dict[str, Any], int]:
        """
        Handle GET requests for thermostat resources
        URL: /MAC_ADDRESS/resource
        """
        if not validate_mac_address(mac):
            return {"error": "Invalid MAC address format"}, 400

        mac: str = format_mac(mac)

        thermostat: ThermostatObject = find_thermostat(mac)
        if not thermostat:
            return {"error": f"Thermostat with MAC {mac} not found"}, 404
        
        if resource == 'status':
            return thermostat.get_status(), 200
        

        elif resource == 'targetTemperature':
            temp_value: str = request.args.get('value')
            if not temp_value:
                return {"error": "Temperature value is required as 'value' parameter"}, 400
            
            try:
                temperature: float = float(temp_value)
                if not (thermostat.min_temperature <= temperature <= thermostat.max_temperature):
                    return {
                        "error": f"Temperature must be between {thermostat.min_temperature}°C and {thermostat.max_temperature}°C"
                    }, 400
            except ValueError:
                return {"error": "Invalid temperature value"}, 400
            try:
                result: dict[str, Any] = thermostat.set_temperature(str(temperature))
                logging.info(f"HomeKit: Set targetTemperature for {mac} to {temperature}: {result}")
                
                if result["result"] == "ok":
                    return {"success": True, "temperature": temperature}, 200
                else:
                    return result, 400
                    
            except BleakError:
                logging.error(f"Device with address {mac} was not found")
                return {"error": f"Device with address {mac} was not found"}, 404
            
    
        elif resource == 'targetHeatingCoolingState':
            mode_value: str = request.args.get('value')
            if not mode_value:
                return {"error": "Mode value is required as 'value' parameter"}, 400
            
            if mode_value not in ['0', '1', '2', '3']:
                return {"error": "Mode must be 0 (off), 1 (heat), 2 (cool), or 3 (auto)"}, 400
            
            try:
                result: dict[str, Any] = thermostat.set_mode(mode_value)
                logging.info(f"HomeKit: Set targetHeatingCoolingState for {mac} to {mode_value}: {result}")
                
                if result["result"] == "ok":
                    return {"success": True, "mode": int(mode_value)}, 200
                else:
                    return result, 400
                    
            except BleakError:
                logging.error(f"Device with address {mac} was not found")
                return {"error": f"Device with address {mac} was not found"}, 404
        else:
            return {"error": "Resource not found"}, 404
