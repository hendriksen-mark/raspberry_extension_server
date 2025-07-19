"""
DHT sensor related routes
"""
import logging
import logManager
from typing import Any
import configManager
from ServerObjects.dht_object import DHTObject

logger: logging.Logger = logManager.logger.get_logger(__name__)

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config

class DHTRoute():
    def get(self) -> tuple[dict[str, Any], int]:
        dht: DHTObject = serverConfig["dht"]
        pin: int = dht.get_pin()
        # If no pin is set at all, return default values
        if pin is None:
            logger.warning("DHT_PIN is not set, returning default values.")
            return {
                "temperature": 22.0,  # Default temperature
                "humidity": 50.0,     # Default humidity
                "warning": "DHT sensor not configured"
            }, 200

        # Get current sensor values
        temp, hum = dht.get_data()

        if temp is None or hum is None:
            logger.warning("DHT sensor data not available, returning default values")
            return {
                "temperature": 22.0,  # Default temperature
                "humidity": 50.0,     # Default humidity
                "warning": "DHT sensor data not available"
            }, 200
        
        logger.info(f"Returning DHT data")
        logger.debug(f"Temperature: {temp}°C, Humidity: {hum}%, Pin: {pin}")

        return {
            "temperature": temp,
            "humidity": hum,
            "pin": pin
        }, 200
