import logging
from flask import request
from flask_restful import Resource
import logManager
from typing import Any
import configManager
from ServerObjects.fan_object import FanObject

logger: logging.Logger = logManager.logger.get_logger(__name__)

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config

def find_fan() -> FanObject:
    """
    Find fan service in server configuration
    """
    return serverConfig.get("fan")

def create_fan(postDict: dict[str, Any] = {}) -> FanObject:
    """
    Create a new fan object if it doesn't exist
    """
    if not postDict:
        logger.warning("No POST data provided, creating default fan object")
    return FanObject(postDict)

class FanRoute(Resource):
    def get(self, resource: str = None) -> tuple[dict[str, Any], int]:
        """
        Handle GET requests for fan resources
        URL patterns:
        - /fan/
        - /fan/full_speed
        - /fan/off  
        - /fan/status
        """
        # Get the fan service
        fan: FanObject = find_fan()

        if fan is None:
            return {"error": "Fan service not found in server configuration"}, 404

        if resource == "full_speed":
            fan.setFull()

        return fan.get_all_data(), 200
    
    def post(self, resource: str = None) -> tuple[dict[str, Any], int]:
        """
        Update fan configuration
        URL: /fan/<resource>
        """
        postDict: dict[str, Any] = request.get_json(force=True) if request.get_data(as_text=True) != "" else {}
        logger.info(f"POST data received: {postDict}")

        fan: FanObject = find_fan()

        if fan:
            logger.info(f"Fan already exists, updating configuration")
            # Only allow updating certain safe attributes
            allowed_attributes: set[str] = {'gpio_pin', 'pwm_frequency', 'min_temperature', 'max_temperature', 'min_speed', 'max_speed', 'temp_change_threshold', 'full_speed_time_duration'}
            for key, value in postDict.items():
                if key in allowed_attributes and hasattr(fan, key):
                    setattr(fan, key, value)
                elif key not in allowed_attributes:
                    logger.warning(f"Attempted to set non-allowed attribute: {key}")
        else:
            logger.info(f"Fan not found, creating a new one")
            try:
                fan: FanObject = create_fan(postDict)
                serverConfig["fan"] = fan
            except ValueError as e:
                logger.error(f"Failed to create fan: {e}")
                return {"error": str(e)}, 400

        if not fan:
            return {"error": "Fan not found or failed to create fan"}, 500

        try:
            logger.info(f"Updated fan configuration: {fan.save()}")
            configManager.serverConfig.save_config(backup=False, resource="fan")
            return fan.save(), 200
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return {"error": "Failed to save configuration"}, 500
        except KeyError as e:
            logger.error(f"KeyError: {e}")
            return {"error": "Fan configuration not found"}, 404

    def delete(self, resource: str = None) -> tuple[dict[str, Any], int]:
        """
        Delete fan service
        URL: /fan/<resource>
        """
        fan: FanObject = find_fan()
        if fan:
            try:
                logger.info("Deleting fan service")
                del serverConfig["fan"]
                configManager.serverConfig.save_config(backup=False, resource="fan")
                return {"success": True}, 200
            except Exception as e:
                logger.error(f"Failed to delete fan service: {e}")
                return {"error": "Failed to delete fan service"}, 500
        else:
            logger.error("Fan service not found in server configuration")
            return {"error": "Fan service not found in server configuration"}, 404
