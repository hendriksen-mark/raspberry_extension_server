from typing import Any

class SystemService:

    def _get_dht_service(self):
            from .dht_service import dht_service
            return dht_service

    def get_all_status(self) -> dict[str, Any]:
            """Get all thermostat status and system information"""
            temp, humidity = self._get_dht_service().get_data()
            
            message = {
                "thermostats": self.status_store,
                "dht": {
                    "pin": self._get_dht_service().get_pin(),
                    "temperature": temp,
                    "humidity": humidity,
                    "active": self._get_dht_service().get_pin() is not None
                }
            }
            
            try:
                from ..utils import get_pi_temp
                message["pi_temp"] = get_pi_temp()
            except RuntimeError:
                message["pi_temp"] = None
                
            return message