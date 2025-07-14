from flask import request
from typing import Any
from flask_restful import Resource
import logManager
import configManager
from ServerObjects.klok_object import KlokObject

logging = logManager.logger.get_logger(__name__)

serverConfig = configManager.serverConfig.yaml_config

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
        # Get value from URL parameter or query string
        if value is None:
            value = request.args.get("value")
        
        logging.info(f"Klok request: request_type={request_type}, value={value}")
        
        # Get the klok service (assuming it's a single service like DHT)
        klok: KlokObject = serverConfig["klok"]

        if request_type == "on":
            klok.set_power(True)
            return {"status": "on"}, 200
            
        elif request_type == "off":
            klok.set_power(False)
            return {"status": "off"}, 200
            
        elif request_type == "status":
            state = 1 if klok.power_state else 0
            return str(state), 200
            
        elif request_type == "Bri":
            if value is not None:
                try:
                    brightness_value = int(value)
                    klok.set_brightness(brightness_value)
                    return {"status": "done"}, 200
                except ValueError:
                    return {"error": "Invalid brightness value"}, 400
            else:
                return {"error": "Brightness value is required"}, 400
                
        elif request_type == "infoBri":
            bri_percent = klok.get_brightness_percent()
            return str(bri_percent), 200
            
        else:
            return {"error": "Not found, available endpoints: /on, /off, /status, /Bri/<value>, /infoBri"}, 404