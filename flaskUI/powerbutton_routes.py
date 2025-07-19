import logging
from flask import request
from flask_restful import Resource
import logManager
from typing import Any
import configManager
from ServerObjects.powerbutton_object import PowerButtonObject

logger: logging.Logger = logManager.logger.get_logger(__name__)

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config

def find_powerbutton() -> PowerButtonObject:
    """
    Find powerbutton service in server configuration
    """
    return serverConfig.get("powerbutton")

def create_powerbutton(postDict: dict[str, Any] = {}) -> PowerButtonObject:
    """
    Create a new powerbutton object if it doesn't exist
    """
    if not postDict:
        logger.warning("No POST data provided, creating default powerbutton object")
    return PowerButtonObject(postDict)

class PowerButtonRoute(Resource):
    def get(self, resource: str) -> tuple[dict[str, Any], int]:
        """
        Handle GET requests for powerbutton resources
        """
        powerbutton: PowerButtonObject = find_powerbutton()

        if powerbutton is None:
            return {"error": "PowerButton service not found in server configuration"}, 404
            
        if resource == "info":
            return powerbutton.save(), 200

        return {"error": "Unknown powerbutton resource"}, 400

    def post(self, resource: str) -> tuple[dict[str, Any], int]:
        """
        Handle POST requests for powerbutton resources
        """
        postDict: dict[str, Any] = request.get_json(force=True) if request.get_data(as_text=True) != "" else {}
        logger.info(f"POST data received: {postDict}")

        powerButton: PowerButtonObject = find_powerbutton()

        if powerButton:
            logger.info(f"PowerButton already exists, updating it")
            # Only allow updating certain safe attributes
            allowed_attributes = {'button_pin', 'long_press_duration', 'debounce_time'}
            for key, value in postDict.items():
                if key in allowed_attributes and hasattr(powerButton, key):
                    setattr(powerButton, key, value)
                elif key not in allowed_attributes:
                    logger.warning(f"Attempted to set non-allowed attribute: {key}")
        else:
            logger.info(f"PowerButton not found, creating a new one")
            try:
                powerButton = create_powerbutton(postDict)
                serverConfig["powerbutton"] = powerButton
            except ValueError as e:
                logger.error(f"Failed to create powerbutton: {e}")
                return {"error": str(e)}, 400
        
        if not powerButton:
            return {"error": "PowerButton not found or failed to create PowerButton"}, 500
        
        try:
            logger.info(f"Updated PowerButton configuration: {powerButton.save()}")
            configManager.serverConfig.save_config(backup=False, resource="powerbutton")
            return powerButton.save(), 200
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return {"error": "Failed to save configuration"}, 500
        except KeyError as e:
            logger.error(f"KeyError: {e}")
            return {"error": "PowerButton configuration not found"}, 404
    
    def delete(self, resource: str) -> tuple[dict[str, Any], int]:
        """
        Handle DELETE requests for powerbutton resources
        """
        powerButton: PowerButtonObject = find_powerbutton()
        if powerButton:
            try:
                logger.info(f"Deleting PowerButton service")
                del serverConfig["powerbutton"]
                configManager.serverConfig.save_config(backup=False, resource="powerbutton")
                return {"success": True}, 200
            except Exception as e:
                logger.error(f"Failed to delete PowerButton service: {e}")
                return {"error": "Failed to delete PowerButton service"}, 500
        else:
            logger.error("PowerButton service not found in server configuration")
            return {"error": "PowerButton service not found in server configuration"}, 404