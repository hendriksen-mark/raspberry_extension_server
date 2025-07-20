"""
HomeKit/Homebridge compatible routes
"""
from flask import request
from bleak import BleakError
from typing import Any
from flask_restful import Resource
import logging
import logManager
import configManager
from services.utils import validate_mac_address, format_mac, nextFreeId, async_route
from ServerObjects.thermostat_object import ThermostatObject

logger: logging.Logger = logManager.logger.get_logger(__name__)

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config

def find_thermostat(mac: str) -> ThermostatObject | None:
    """
    Find thermostat by MAC address
    """
    for thermostat in serverConfig["thermostats"].values():
        if thermostat.mac.lower() == mac.lower():
            return thermostat
    return None

def create_thermostat(mac: str, postDict: dict[str, Any] = None) -> ThermostatObject:
    """
    Create a new thermostat object if it doesn't exist
    """
    if find_thermostat(mac) is not None:
        raise ValueError(f"Thermostat with MAC {mac} already exists")
    
    data: dict[str, Any] = {"mac": mac}
    data["id"] = nextFreeId(serverConfig, "thermostats")
    if postDict:
        data.update(postDict)
    return ThermostatObject(data)

class ThermostatRoute(Resource):
    @async_route
    async def get(self, mac, resource = None, value: str = None) -> tuple[dict[str, Any], int]:
        """
        Handle GET requests for thermostat resources
        URL: /MAC_ADDRESS/ or /MAC_ADDRESS/resource
        """
        if not validate_mac_address(mac):
            return {"error": "Invalid MAC address format"}, 400

        mac: str = format_mac(mac)

        thermostat: ThermostatObject = find_thermostat(mac)
        if not thermostat:
            logger.info(f"Thermostat with MAC {mac} not found, creating a new one")
            try:
                thermostat = create_thermostat(mac)
                serverConfig["thermostats"][thermostat.id] = thermostat
                logger.info(f"Created new thermostat with MAC {mac}: {thermostat.save()}")
                configManager.serverConfig.save_config(backup=False, resource="thermostats")
            except ValueError as e:
                logger.error(f"Failed to create thermostat: {e}")
                return {"error": str(e)}, 400
            except Exception as e:
                logger.error(f"Failed to save configuration: {e}")
                return {"error": "Failed to save configuration"}, 500

        # If no resource specified, return available endpoints for this thermostat
        if resource is None:
            return {
                "mac": mac,
                "available_endpoints": [
                    "status", 
                    "targetTemperature", 
                    "targetHeatingCoolingState"
                ],
                "description": f"Thermostat {mac} control endpoints"
            }, 200

        if resource == 'status':
            return thermostat.get_status(), 200
        

        elif resource == 'targetTemperature':
            if value is None:
                temp_value: str = request.args.get('value')
            else:
                temp_value: str = value
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
                result: dict[str, Any] = await thermostat.set_temperature(str(temperature))
                logger.info(f"HomeKit: Set targetTemperature for {mac} to {temperature}: {result}")
                
                if result["result"] == "ok":
                    return {"success": True, "temperature": temperature}, 200
                else:
                    return result, 400
                    
            except BleakError:
                logger.error(f"Device with address {mac} was not found")
                return {"error": f"Device with address {mac} was not found"}, 404
            
    
        elif resource == 'targetHeatingCoolingState':
            if value is None:
                mode_value: str = request.args.get('value')
            else:
                mode_value: str = value
            if not mode_value:
                return {"error": "Mode value is required as 'value' parameter"}, 400
            
            if mode_value not in ['0', '1', '2', '3']:
                return {"error": "Mode must be 0 (off), 1 (heat), 2 (cool), or 3 (auto)"}, 400
            
            try:
                result: dict[str, Any] = await thermostat.set_mode(mode_value)
                logger.info(f"HomeKit: Set targetHeatingCoolingState for {mac} to {mode_value}: {result}")
                
                if result["result"] == "ok":
                    return {"success": True, "mode": int(mode_value)}, 200
                else:
                    return result, 400
                    
            except BleakError:
                logger.error(f"Device with address {mac} was not found")
                return {"error": f"Device with address {mac} was not found"}, 404
        else:
            return {"error": "Resource not found"}, 404

    @async_route
    async def post(self, mac: str, resource: str = None) -> tuple[dict[str, Any], int]:
        """
        Handle POST requests for thermostat resources
        URL: /MAC_ADDRESS/resource
        """
        if not validate_mac_address(mac):
            return {"error": "Invalid MAC address format"}, 400
        
        mac: str = format_mac(mac)

        thermostat: ThermostatObject = find_thermostat(mac)

        postDict = request.get_json(force=True) if request.get_data(as_text=True) != "" else {}
        logger.info(f"POST data received: {postDict}")

        # Validate required data for creating thermostat
        if not thermostat and not postDict:
            return {"error": "JSON data required for creating new thermostat"}, 400

        if thermostat:
            logger.info(f"Thermostat with MAC {mac} already exists, updating it")
            # Only allow updating certain safe attributes
            allowed_attributes = {'targetHeatingCoolingState', 'targetTemperature', 'min_temperature', 'max_temperature'}
            for key, value in postDict.items():
                if key in allowed_attributes and hasattr(thermostat, key):
                    setattr(thermostat, key, value)
                elif key not in allowed_attributes:
                    logger.warning(f"Attempted to set non-allowed attribute: {key}")
        else:
            logger.info(f"Thermostat with MAC {mac} not found, creating a new one")
            try:
                thermostat = create_thermostat(mac, postDict)
                serverConfig["thermostats"][thermostat.id] = thermostat
            except ValueError as e:
                logger.error(f"Failed to create thermostat: {e}")
                return {"error": str(e)}, 400

        if not thermostat:
            return {"error": f"Thermostat with MAC {mac} not found"}, 404

        try:
            logger.info(f"Updated thermostat with MAC {mac}: {thermostat.save()}")
            configManager.serverConfig.save_config(backup=False, resource="thermostats")
            return thermostat.save(), 200
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return {"error": "Failed to save configuration"}, 500

    @async_route
    async def delete(self, mac: str, resource: str = None) -> tuple[dict[str, Any], int]:
        """
        Handle DELETE requests for thermostat resources
        URL: /MAC_ADDRESS/resource
        """
        if not validate_mac_address(mac):
            return {"error": "Invalid MAC address format"}, 400

        mac: str = format_mac(mac)

        thermostat: ThermostatObject = find_thermostat(mac)

        if thermostat:
            try:
                logger.info(f"Deleting thermostat with MAC {mac}")
                del serverConfig["thermostats"][thermostat.id]
                configManager.serverConfig.save_config(backup=False, resource="thermostats")
                return {"success": True}, 200
            except Exception as e:
                logger.error(f"Failed to delete thermostat: {e}")
                return {"error": "Failed to delete thermostat"}, 500
        else:
            return {"error": f"Thermostat with MAC {mac} not found"}, 404
