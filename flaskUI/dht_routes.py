"""
DHT sensor related routes
"""
import logging
from typing import Any, Optional
import logManager
import configManager
from ServerObjects.dht_object import DHTObject

logger: logging.Logger = logManager.logger.get_logger(__name__)

serverConfig: dict[str, str | int | float | dict] = configManager.serverConfig.yaml_config

def find_dht() -> DHTObject:
    """
    Find DHT service in server configuration
    """
    return serverConfig.get("dht")

def create_dht(postDict: dict[str, Any] = {}) -> DHTObject:
    """
    Create a new DHT object if it doesn't exist
    """
    if not postDict:
        logger.warning("No POST data provided, creating default DHT object")
    return DHTObject(postDict)

def get_default_sensor_data(warning_message: str) -> tuple[dict[str, Any], int]:
        """
        Return default sensor data with a warning message
        """
        return {
            "temperature": 22.0,  # Default temperature
            "humidity": 50.0,     # Default humidity
            "warning": warning_message
        }, 200

class DHTRoute():
    def get(self, resource: str = None) -> tuple[dict[str, Any], int]:
        """
            Handle GET requests for DHT sensor data
        """
        logger.info(f"DHT GET request: resource: {resource}")
        dht: DHTObject = find_dht()

        if dht is None:
            logger.error("DHT service not found in server configuration, returning default values")
            return get_default_sensor_data("DHT sensor not configured")
        
        if resource == "info":
            # Return DHT configuration info
            try:
                dht_info: dict[str, Any] = dht.get_all_data()
                logger.info(f"Returning DHT info: {dht_info}")
                return dht_info, 200
            except KeyError as e:
                logger.error(f"KeyError: {e}")
                return {"error": "DHT sensor configuration not found"}, 404
            except Exception as e:
                logger.error(f"Failed to retrieve DHT info: {e}")
                return {"error": "Failed to retrieve DHT info"}, 500
        
        else:
            pin: int | None | str = dht.get_pin()
            # If no pin is set at all, return default values
            if pin is None:
                logger.warning("DHT_PIN is not set, returning default values.")
                return get_default_sensor_data("DHT_PIN is not set")

            # Get current sensor values
            temp, hum = dht.get_data()

            if temp is None or hum is None:
                logger.warning("DHT sensor data not available, returning default values")
                return get_default_sensor_data("DHT sensor data not available")
            
            logger.info(f"Returning DHT data")
            logger.debug(f"Temperature: {temp}°C, Humidity: {hum}%, Pin: {pin}")

            return {
                "temperature": temp,
                "humidity": hum,
                "pin": pin
            }, 200

    def post(self, resource: str = None, postDict: dict[str, Any] = None) -> tuple[dict[str, Any], int]:
        """
        Update DHT sensor configuration
        """
        postDict = postDict or {}
        logger.info(f"POST data received: {postDict}")

        dht: DHTObject = find_dht()

        if dht:
            logger.info(f"DHT already exists, updating configuration")
            allowed_attributes = ["dht_pin", "sensor_type", "MIN_DHT_TEMP", "MAX_DHT_TEMP", "MIN_HUMIDITY", "MAX_HUMIDITY", "DHT_TEMP_CHANGE_THRESHOLD", "DHT_HUMIDITY_CHANGE_THRESHOLD"]
            for key, value in postDict.items():
                if key in allowed_attributes and hasattr(dht, key):
                    setattr(dht, key, value)
                elif key not in allowed_attributes:
                    logger.warning(f"Attempted to set non-allowed attribute: {key}")
        else:
            logger.info(f"DHT not found, creating a new one")
            try:
                dht: DHTObject = create_dht(postDict)
                serverConfig["dht"] = dht
            except ValueError as e:
                logger.error(f"Failed to create DHT: {e}")
                return {"error": str(e)}, 400

        if not dht:
            return {"error": "DHT not found or failed to create DHT"}, 500

        try:
            logger.info(f"Updated DHT configuration: {dht.save()}")
            configManager.serverConfig.save_config(backup=False, resource="dht")
            return dht.save(), 200
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return {"error": "Failed to save configuration"}, 500
        except KeyError as e:
            logger.error(f"KeyError: {e}")
            return {"error": "DHT sensor configuration not found"}, 404
        
    def delete(self, resource: str = None) -> tuple[dict[str, Any], int]:
        """
        Delete DHT sensor configuration
        """
        dht: DHTObject = find_dht()
        if dht:
            try:
                logger.info("Deleting DHT configuration")
                del serverConfig["dht"]
                configManager.serverConfig.save_config(backup=False, resource="dht")
                return {"success": True}, 200
            except Exception as e:
                logger.error(f"Failed to delete DHT configuration: {e}")
                return {"error": "Failed to delete DHT configuration"}, 500
        else:
            logger.error("DHT service not found in server configuration")
            return {"error": "DHT service not found in server configuration"}, 404
