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

def create_klok(postDict: dict[str, Any] = None) -> KlokObject:
    """
    Create a new klok object
    """
    return KlokObject(postDict) if postDict else KlokObject({})

class KlokRoute(Resource):
    def get(self, request_type: str, value: str = None) -> Any:
        """
        Handle GET requests for klok resources
        URL patterns:
        - /klok/on
        - /klok/off  
        - /klok/status
        - /klok/Bri/<value>
        - /klok/infoBri
        """
        # Validate request type
        valid_request_types = ["on", "off", "status", "Bri", "infoBri"]
        if request_type not in valid_request_types:
            return {"error": "Invalid request type. Valid types are: " + ", ".join(valid_request_types)}, 400
        
        # Get value from URL parameter or query string
        if value is None:
            value: str = request.args.get("value")

        logger.info(f"Klok request: request_type={request_type}, value={value}")
        
        # Get the klok service (assuming it's a single service like DHT)
        klok: KlokObject = find_klok()

        if klok is None:
            return {"error": "Klok service not found in server configuration"}, 404

        if request_type == "on":
            klok.set_power(True)
            return {"status": "on"}, 200
            
        elif request_type == "off":
            klok.set_power(False)
            return {"status": "off"}, 200
            
        elif request_type == "status":
            state: int = 1 if klok.power_state else 0
            return str(state), 200
            
        elif request_type == "Bri":
            if value is not None:
                try:
                    brightness_value: int = int(value)
                    klok.set_brightness(brightness_value)
                    return {"status": "done"}, 200
                except ValueError:
                    return {"error": "Invalid brightness value"}, 400
            else:
                return {"error": "Brightness value is required"}, 400
                
        elif request_type == "infoBri":
            bri_percent: int = klok.get_brightness_percent()
            return str(bri_percent), 200
        
    def post(self) -> Any:
        """
        Handle POST requests for klok resources
        URL: /klok
        """
        postDict = request.get_json(force=True) if request.get_data(as_text=True) != "" else {}
        logger.info(f"POST data received: {postDict}")

        # Validate required data for creating klok
        if not postDict:
            return {"error": "JSON data required"}, 400

        klok: KlokObject = find_klok()

        if klok:
            logger.info(f"Klok already exists, updating configuration")
            # Only allow updating certain safe attributes
            allowed_attributes = {'CLK_pin', 'DIO_pin', 'brightness', 'power_state', 'doublepoint'}
            for key, value in postDict.items():
                if key in allowed_attributes and hasattr(klok, key):
                    setattr(klok, key, value)
                elif key not in allowed_attributes:
                    logger.warning(f"Attempted to set non-allowed attribute: {key}")
        else:
            logger.info(f"Klok not found, creating a new one")
            try:
                klok = create_klok(postDict)
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

    def delete(self) -> Any:
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
                return {"status": "klok service deleted"}, 200
            except Exception as e:
                logger.error(f"Failed to delete klok service: {e}")
                return {"error": "Failed to delete klok service"}, 500
        else:
            return {"error": "Klok service not found"}, 404
