"""
DHT sensor service for temperature and humidity monitoring
"""
from time import sleep
from threading import Lock
import logManager
from typing import Dict, Any

from ..config import Config

logging = logManager.logger.get_logger(__name__)

try:
    import Adafruit_DHT  # type: ignore
except ImportError:
    class DummyDHT:
        DHT22 = None

        @staticmethod
        def read_retry(sensor, pin):
            return 22.0, 50.0
    Adafruit_DHT = DummyDHT()


class DHTService:
    """DHT sensor service for reading temperature and humidity"""
    
    def __init__(self, data: Dict[str, Any]) -> None:
        self.id: str = data.get("id", 1)
        self.sensor_type: str = data.get("sensor_type", "DHT22").upper()
        if self.sensor_type not in ["DHT22", "DHT11"]:
            logging.error(f"Unsupported DHT sensor type: {self.sensor_type}. Defaulting to DHT22.")
            self.sensor_type = "DHT22"
        self.dht_pin: int = data.get("dht_pin", None)
        self.latest_temperature: float = data.get("latest_temperature", None)
        self.latest_humidity: float = data.get("latest_humidity", None)
        self.dht_lock = Lock()
        self.last_logged_dht_temp: float | None = None
        self.last_logged_dht_humidity: float | None = None
        self._thread_started = False

        if self.sensor_type == "DHT22":
            logging.info("Using DHT22 sensor")
            self.sensor = Adafruit_DHT.DHT22
        elif self.sensor_type == "DHT11":
            logging.info("Using DHT11 sensor")
            self.sensor = Adafruit_DHT.DHT11
        else:
            logging.error(f"Unsupported DHT sensor type: {self.sensor_type}. Defaulting to DHT22.")
            self.sensor = Adafruit_DHT.DHT22
    
    def _get_thermostat_service(self):
        """Lazy import of thermostat_service to avoid circular import"""
        from .thermostat_service import thermostat_service
        return thermostat_service
    
    def get_pin(self) -> int | None:
        """Get current DHT pin"""
        return self.dht_pin
    
    def get_data(self) -> tuple[float | None, float | None]:
        """Get current temperature and humidity data"""
        with self.dht_lock:
            return self.latest_temperature, self.latest_humidity
    
    def _read_dht_temperature(self) -> None:
        """
        Continuously read the temperature and humidity from the DHT sensor
        and update the global variables every 5 seconds.
        If the sensor returns invalid values (None or out of range), do not update globals.
        """
        while self.dht_pin is not None:
            try:
                humidity, temperature = Adafruit_DHT.read_retry(self.sensor, self.dht_pin)
                logging.debug(f"Raw DHT read: temperature={temperature}, humidity={humidity}")
                
                with self.dht_lock:
                    # Only update if values are valid
                    if temperature is not None and Config.MIN_DHT_TEMP < temperature < Config.MAX_DHT_TEMP:
                        rounded_temp = round(float(temperature), 1)
                        logged_info = False
                        if self.latest_temperature != rounded_temp:
                            self.latest_temperature = rounded_temp
                            # Only log when temperature changes significantly or this is the first reading
                            if (self.last_logged_dht_temp is None or 
                                abs(rounded_temp - self.last_logged_dht_temp) >= Config.DHT_TEMP_CHANGE_THRESHOLD):
                                logging.info(f"Updated temperature: {self.latest_temperature}°C")
                                self.last_logged_dht_temp = rounded_temp
                                self._get_thermostat_service().update_dht_related_status(temperature=rounded_temp)
                                logged_info = True
                        
                        # Always log current temperature for debugging (unless we just logged at info level)
                        if not logged_info:
                            logging.debug(f"Temperature: {rounded_temp}°C")
                    else:
                        logging.error("Temperature value not updated (None or out of range)")
                        
                    if humidity is not None and Config.MIN_HUMIDITY <= humidity <= Config.MAX_HUMIDITY:
                        rounded_humidity = round(float(humidity), 1)
                        logged_info = False
                        if self.latest_humidity != rounded_humidity:
                            self.latest_humidity = rounded_humidity
                            # Only log when humidity changes significantly or this is the first reading
                            if (self.last_logged_dht_humidity is None or 
                                abs(rounded_humidity - self.last_logged_dht_humidity) >= Config.DHT_HUMIDITY_CHANGE_THRESHOLD):
                                logging.info(f"Updated humidity: {self.latest_humidity}%")
                                self.last_logged_dht_humidity = rounded_humidity
                                self._get_thermostat_service().update_dht_related_status(humidity=rounded_humidity)
                                logged_info = True
                        
                        # Always log current humidity for debugging (unless we just logged at info level)
                        if not logged_info:
                            logging.debug(f"Humidity: {rounded_humidity}%")
                    else:
                        logging.error("Humidity value not updated (None or out of range)")
                        
            except Exception as e:
                logging.error(f"Error reading DHT sensor: {e}")
            
            sleep(Config.DHT_READ_INTERVAL)

    def save(self) -> Dict[str, Any]:
        """Save current DHT state to a dictionary"""
        return {
            "sensor_type": self.sensor_type,
            "dht_pin": self.dht_pin,
            "latest_temperature": self.latest_temperature,
            "latest_humidity": self.latest_humidity
        }


# Global DHT service instance
dht_service = DHTService()
