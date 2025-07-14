"""
DHT sensor related routes
"""
import logManager
import configManager
from ServerObjects.dht_object import DHTObject

logging = logManager.logger.get_logger(__name__)

serverConfig = configManager.serverConfig.yaml_config

class DHTRoute():
    def get(self):
        dht: DHTObject = serverConfig["dht"]
        pin = dht.get_pin()
        # If no pin is set at all, return default values
        if pin is None:
            logging.warning("DHT_PIN is not set, returning default values.")
            return {
                "temperature": 22.0,  # Default temperature
                "humidity": 50.0,     # Default humidity
                "warning": "DHT sensor not configured"
            }, 200

        # Get current sensor values
        temp, hum = dht.get_data()

        if temp is None or hum is None:
            logging.warning("DHT sensor data not available, returning default values")
            return {
                "temperature": 22.0,  # Default temperature
                "humidity": 50.0,     # Default humidity
                "warning": "DHT sensor data not available"
            }, 200
        
        logging.info(f"Returning DHT data")
        logging.debug(f"Temperature: {temp}°C, Humidity: {hum}%, Pin: {pin}")

        return {
            "temperature": temp,
            "humidity": hum,
            "pin": pin
        }, 200
