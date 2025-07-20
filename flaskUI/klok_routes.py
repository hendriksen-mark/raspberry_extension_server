from flask import request
from typing import Any
from flask_restful import Resource
import logging
import logManager
import configManager
from ServerObjects.klok_object import KlokObject

logger: logging.Logger = logManager.logger.get_logger(__name__)

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config

def find_klok() -> KlokObject:
    """
    Find klok service in server configuration
    """
    return serverConfig.get("klok")

def create_klok(postDict: dict[str, Any] = {}) -> KlokObject:
    """
    Create a new klok object
    """
    if not postDict:
        logger.warning("No POST data provided, creating default klok object")
    return KlokObject(postDict)

class KlokRoute(Resource):
    def get(self, resource: str = None, value: str = None) -> tuple[dict[str, Any], int]:
        """
        Handle GET requests for klok resources
        URL patterns:
        - /klok/
        - /klok/on
        - /klok/off  
        - /klok/status
        - /klok/Bri/<value>
        - /klok/infoBri
        """
        # If no resource specified, return available endpoints
        if resource is None:
            return {
                "available_endpoints": [
                    "on",
                    "off",
                    "status",
                    "Bri/<value>",
                    "infoBri"
                ],
                "description": "Klok (clock) control endpoints"
            }, 200
            
        # Validate request type
        valid_resources: list[str] = ["on", "off", "status", "Bri", "infoBri"]
        if resource not in valid_resources:
            return {"error": "Invalid request type. Valid types are: " + ", ".join(valid_resources)}, 400
        
        # Get value from URL parameter or query string
        if value is None:
            value: str = request.args.get("value")

        logger.info(f"Klok GET request: resource={resource}, value={value}")

        # Get the klok service (assuming it's a single service like DHT)
        klok: KlokObject = find_klok()

        if klok is None:
            logger.error("Klok service not found in server configuration")
            return {"error": "Klok service not found in server configuration"}, 404

        if resource == "on":
            klok.set_power(True)
            return {"status": "on"}, 200
            
        elif resource == "off":
            klok.set_power(False)
            return {"status": "off"}, 200
            
        elif resource == "status":
            state: int = 1 if klok.power_state else 0
            return str(state), 200
            
        elif resource == "Bri":
            if value is not None:
                try:
                    brightness_value: int = int(value)
                    klok.set_brightness(brightness_value)
                    return {"status": "done"}, 200
                except ValueError:
                    return {"error": "Invalid brightness value"}, 400
            else:
                return {"error": "Brightness value is required"}, 400
                
        elif resource == "infoBri":
            bri_percent: int = klok.get_brightness_percent()
            return str(bri_percent), 200
        
        return klok.get_all_data(), 200

    def post(self, resource: str = None, value: str = None) -> tuple[dict[str, Any], int]:
        """
        Handle POST requests for klok resources
        URL: /klok
        """
        postDict: dict[str, Any] = request.get_json(force=True) if request.get_data(as_text=True) != "" else {}
        logger.info(f"POST data received: {postDict}")

        klok: KlokObject = find_klok()

        if klok:
            logger.info(f"Klok already exists, updating configuration")
            # Only allow updating certain safe attributes
            allowed_attributes: set[str] = {'CLK_pin', 'DIO_pin', 'brightness', 'power_state', 'doublepoint'}
            for key, value in postDict.items():
                if key in allowed_attributes and hasattr(klok, key):
                    setattr(klok, key, value)
                elif key not in allowed_attributes:
                    logger.warning(f"Attempted to set non-allowed attribute: {key}")
        else:
            logger.info(f"Klok not found, creating a new one")
            try:
                klok: KlokObject = create_klok(postDict)
                serverConfig["klok"] = klok
            except ValueError as e:
                logger.error(f"Failed to create klok: {e}")
                return {"error": str(e)}, 400

        if not klok:
            return {"error": "Klok not found or failed to create klok"}, 500

        try:
            logger.info(f"Updated klok configuration: {klok.save()}")
            configManager.serverConfig.save_config(backup=False, resource="klok")
            return klok.save(), 200
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return {"error": "Failed to save configuration"}, 500
        except KeyError as e:
            logger.error(f"KeyError: {e}")
            return {"error": "Klok sensor configuration not found"}, 404

    def delete(self, resource: str = None, value: str = None) -> tuple[dict[str, Any], int]:
        """
        Handle DELETE requests for klok resources
        URL: /klok
        """ 
        klok: KlokObject = find_klok()
        if klok:
            try:
                logger.info(f"Deleting klok service")
                del serverConfig["klok"]
                configManager.serverConfig.save_config(backup=False, resource="klok")
                return {"success": True}, 200
            except Exception as e:
                logger.error(f"Failed to delete klok service: {e}")
                return {"error": "Failed to delete klok service"}, 500
        else:
            logger.error("Klok service not found in server configuration")
            return {"error": "Klok service not found in server configuration"}, 404
