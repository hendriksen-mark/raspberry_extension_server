from typing import Any
import configManager
from ServerObjects.thermostat_object import ThermostatObject
from ServerObjects.dht_object import DHTObject

class SystemService:

    def _get_dht_service(self):
        """Get the DHT service from server config"""
        return configManager.serverConfig.yaml_config["dht"]

    def _get_all_thermostats_status(self) -> dict[str, Any]:
        """Get status of all thermostats from server config"""
        thermostats_status = {}
        thermostats: dict[str, Any] = configManager.serverConfig.yaml_config["thermostats"]

        for thermostat_id, thermostat in thermostats.items():
            try:
                # Get the status from each thermostat
                thermostat: ThermostatObject = thermostat
                thermostats_status[thermostat_id] = thermostat.get_status()
            except Exception as e:
                # If there's an error getting status, include error info
                thermostats_status[thermostat_id] = {
                    "error": str(e),
                    "connected": False
                }
        
        return thermostats_status

    def get_all_status(self) -> dict[str, Any]:
        """Get all thermostat status and system information"""
        dht_service: DHTObject = self._get_dht_service()
        temp, humidity = dht_service.get_data()
        
        message = {
            "thermostats": self._get_all_thermostats_status(),
            "dht": {
                "pin": dht_service.get_pin(),
                "temperature": temp,
                "humidity": humidity,
                "active": dht_service.get_pin() is not None
            }
        }
        
        try:
            from services.utils import get_pi_temp
            message["pi_temp"] = get_pi_temp()
        except RuntimeError:
            message["pi_temp"] = None
            
        return message