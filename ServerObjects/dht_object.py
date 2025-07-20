"""
DHT sensor service for temperature and humidity monitoring
"""
from threading import Lock
import logging
import logManager
from typing import Any
from ServerObjects.thermostat_object import ThermostatObject

import configManager

logger: logging.Logger = logManager.logger.get_logger(__name__)

try:
    import Adafruit_DHT  # type: ignore
except ImportError:
    from services.dummy_import import DummyDHT as Adafruit_DHT  # Import a dummy DHT class for testing


class DHTObject:
    """DHT sensor service for reading temperature and humidity"""
    
    def __init__(self, data: dict[str, Any]) -> None:
        self.sensor_type: str = data.get("sensor_type", "DHT22").upper()
        if self.sensor_type not in ["DHT22", "DHT11"]:
            logger.error(f"Unsupported DHT sensor type: {self.sensor_type}. Defaulting to DHT22.")
            self.sensor_type = "DHT22"
        self.dht_pin: int = data.get("dht_pin", None)
        self.latest_temperature: float = data.get("latest_temperature", None)
        self.latest_humidity: float = data.get("latest_humidity", None)
        self.MIN_DHT_TEMP: float = data.get("MIN_DHT_TEMP", -40.0)
        self.MAX_DHT_TEMP: float = data.get("MAX_DHT_TEMP", 80.0)
        self.MIN_HUMIDITY: float = data.get("MIN_HUMIDITY", 0.0)
        self.MAX_HUMIDITY: float = data.get("MAX_HUMIDITY", 100.0)
        self.DHT_TEMP_CHANGE_THRESHOLD: float = data.get("DHT_TEMP_CHANGE_THRESHOLD", 0.5)
        self.DHT_HUMIDITY_CHANGE_THRESHOLD: float = data.get("DHT_HUMIDITY_CHANGE_THRESHOLD", 5.0)
        self.dht_lock = Lock()
        self.last_logged_dht_temp: float | None = None
        self.last_logged_dht_humidity: float | None = None
        self._thread_started = False

        if self.sensor_type == "DHT22":
            logger.info("Using DHT22 sensor")
            self.sensor = Adafruit_DHT.DHT22
        elif self.sensor_type == "DHT11":
            logger.info("Using DHT11 sensor")
            self.sensor = Adafruit_DHT.DHT11
        else:
            logger.error(f"Unsupported DHT sensor type: {self.sensor_type}. Defaulting to DHT22.")
            self.sensor = Adafruit_DHT.DHT22
    
    def get_pin(self) -> int | None:
        """Get current DHT pin"""
        return self.dht_pin
    
    def get_data(self) -> tuple[float | None, float | None]:
        """Get current temperature and humidity data"""
        with self.dht_lock:
            return self.latest_temperature, self.latest_humidity
    
    def _read_dht_temperature(self) -> None:
        """
        Read the temperature and humidity from the DHT sensor once
        and update the global variables.
        If the sensor returns invalid values (None or out of range), do not update globals.
        """
        try:
            humidity, temperature = Adafruit_DHT.read_retry(self.sensor, self.dht_pin)
            serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config
            MIN_DHT_TEMP: float = self.MIN_DHT_TEMP
            MAX_DHT_TEMP: float = self.MAX_DHT_TEMP
            MIN_HUMIDITY: float = self.MIN_HUMIDITY
            MAX_HUMIDITY: float = self.MAX_HUMIDITY
            DHT_TEMP_CHANGE_THRESHOLD: float = self.DHT_TEMP_CHANGE_THRESHOLD
            DHT_HUMIDITY_CHANGE_THRESHOLD: float = self.DHT_HUMIDITY_CHANGE_THRESHOLD
            logger.debug(f"Raw DHT read: temperature={temperature}, humidity={humidity}")
            
            with self.dht_lock:
                # Only update if values are valid
                if temperature is not None and MIN_DHT_TEMP < temperature < MAX_DHT_TEMP:
                    rounded_temp: float = round(float(temperature), 1)
                    logged_info = False
                    if self.latest_temperature != rounded_temp:
                        self.latest_temperature = rounded_temp
                        # Only log when temperature changes significantly or this is the first reading
                        if (self.last_logged_dht_temp is None or 
                            abs(rounded_temp - self.last_logged_dht_temp) >= DHT_TEMP_CHANGE_THRESHOLD):
                            logger.info(f"Updated temperature: {self.latest_temperature}°C")
                            self.last_logged_dht_temp = rounded_temp
                            for thermostat in serverConfig["thermostats"].values():
                                thermostat: ThermostatObject = thermostat
                                thermostat.update_dht_related_status(temperature=rounded_temp)
                            logged_info = True
                    
                    # Always log current temperature for debugging (unless we just logged at info level)
                    if not logged_info:
                        logger.debug(f"Temperature: {rounded_temp}°C")
                else:
                    logger.error("Temperature value not updated (None or out of range)")

                if humidity is not None and MIN_HUMIDITY <= humidity <= MAX_HUMIDITY:
                    rounded_humidity: float = round(float(humidity), 1)
                    logged_info = False
                    if self.latest_humidity != rounded_humidity:
                        self.latest_humidity = rounded_humidity
                        # Only log when humidity changes significantly or this is the first reading
                        if (self.last_logged_dht_humidity is None or 
                            abs(rounded_humidity - self.last_logged_dht_humidity) >= DHT_HUMIDITY_CHANGE_THRESHOLD):
                            logger.info(f"Updated humidity: {self.latest_humidity}%")
                            self.last_logged_dht_humidity = rounded_humidity
                            for thermostat in serverConfig["thermostats"].values():
                                thermostat: ThermostatObject = thermostat
                                thermostat.update_dht_related_status(humidity=rounded_humidity)
                            logged_info = True
                    
                    # Always log current humidity for debugging (unless we just logged at info level)
                    if not logged_info:
                        logger.debug(f"Humidity: {rounded_humidity}%")
                else:
                    logger.error("Humidity value not updated (None or out of range)")
                    
        except Exception as e:
            logger.error(f"Error reading DHT sensor: {e}")

    def get_all_data(self) -> dict[str, Any]:
        """Get all DHT data as a dictionary"""
        with self.dht_lock:
            return {
                "sensor_type": self.sensor_type,
                "dht_pin": self.dht_pin,
                "latest_temperature": self.latest_temperature,
                "latest_humidity": self.latest_humidity,
                "MIN_DHT_TEMP": self.MIN_DHT_TEMP,
                "MAX_DHT_TEMP": self.MAX_DHT_TEMP,
                "MIN_HUMIDITY": self.MIN_HUMIDITY,
                "MAX_HUMIDITY": self.MAX_HUMIDITY,
                "DHT_TEMP_CHANGE_THRESHOLD": self.DHT_TEMP_CHANGE_THRESHOLD,
                "DHT_HUMIDITY_CHANGE_THRESHOLD": self.DHT_HUMIDITY_CHANGE_THRESHOLD
            }

    def save(self) -> dict[str, Any]:
        """Save current DHT state to a dictionary"""
        return self.get_all_data()
