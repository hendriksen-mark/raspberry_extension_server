"""
DHT sensor related routes
"""
from math import pi
from flask import Blueprint, jsonify
from flask_restful import Resource
import logManager
import configManager

logging = logManager.logger.get_logger(__name__)

dht_bp = Blueprint('dht', __name__)

serverConfig = configManager.serverConfig.yaml_config

dht = serverConfig["DHT"]

class DHTRoute(Resource):
    def get(self, resource):
        pin = dht.get_pin()
        # If no pin is set at all, return default values
        if pin is None:
            logging.warning("DHT_PIN is not set, returning default values.")
            return jsonify({
                "temperature": 22.0,  # Default temperature
                "humidity": 50.0,     # Default humidity
                "warning": "DHT sensor not configured"
            }), 200

        # Get current sensor values
        temp, hum = dht.get_data()

        if temp is None or hum is None:
            logging.warning("DHT sensor data not available, returning default values")
            return jsonify({
                "temperature": 22.0,  # Default temperature
                "humidity": 50.0,     # Default humidity
                "warning": "DHT sensor data not available"
            }), 200
        
        logging.info(f"Returning DHT data")
        logging.debug(f"Temperature: {temp}°C, Humidity: {hum}%, Pin: {pin}")

        return jsonify({
            "temperature": temp,
            "humidity": hum,
            "pin": pin
        }), 200
