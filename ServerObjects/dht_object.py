"""
DHT sensor service for temperature and humidity monitoring
"""
from threading import Lock
import logging
import logManager
from typing import Any
import sys
import platform

logger: logging.Logger = logManager.logger.get_logger(__name__)

# Platform detection
IS_RASPBERRY_PI = platform.machine().startswith(('arm', 'aarch64')) and sys.platform == 'linux'
IS_DEVELOPMENT = sys.platform == 'darwin' or sys.platform == 'win32'

# Log platform information
logger.debug(f"Platform: {sys.platform}, Machine: {platform.machine()}")
logger.debug(f"Detected as Raspberry Pi: {IS_RASPBERRY_PI}, Development: {IS_DEVELOPMENT}")

try:
    import board
    import adafruit_dht
    BOARD_AVAILABLE = True
    if IS_DEVELOPMENT:
        logger.info("Running on development platform - DHT sensor will use mock data")
    elif IS_RASPBERRY_PI:
        logger.info("Running on Raspberry Pi - DHT sensor will use real hardware")
    else:
        logger.info("Running on unknown platform - attempting to use real DHT hardware")
except (ImportError, NotImplementedError, Exception) as e:
    logger.warning(f"Board/DHT libraries not available: {e}. DHT functionality will be disabled.")
    BOARD_AVAILABLE = False
    board = None
    adafruit_dht = None


class MockDHTDevice:
    """Mock DHT device for development/testing purposes"""
    def __init__(self, sensor_type="DHT22"):
        self.sensor_type = sensor_type
        import random
        self._base_temp = 22.0
        self._base_humidity = 45.0
        
    @property
    def temperature(self):
        """Return mock temperature with some variation"""
        import random
        return self._base_temp + random.uniform(-2.0, 2.0)
    
    @property 
    def humidity(self):
        """Return mock humidity with some variation"""
        import random
        return self._base_humidity + random.uniform(-5.0, 5.0)


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
        self.temperature_callbacks: list = []
        self.humidity_callbacks: list = []
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
        
        # Validate pin is provided
        if self.dht_pin is None:
            raise ValueError("DHT pin must be specified in configuration")
        
        # Check if board is available or if we're in development mode
        if not BOARD_AVAILABLE:
            if IS_DEVELOPMENT:
                logger.info(f"Using mock DHT{self.sensor_type} device for development")
                self.dhtDevice = MockDHTDevice(self.sensor_type)
            else:
                logger.error("Board/DHT libraries not available. DHT sensor will not function.")
                logger.error("On Raspberry Pi, ensure you have installed: pip install adafruit-circuitpython-dht")
                logger.error("And that GPIO is enabled in raspi-config")
                self.dhtDevice = None
            return
        
        # Additional Raspberry Pi checks
        if IS_RASPBERRY_PI:
            try:
                # Test if we can access GPIO
                import os
                if not os.path.exists('/dev/gpiomem'):
                    logger.warning("GPIO access may be limited. Ensure GPIO is enabled and user has permissions.")
            except Exception as e:
                logger.warning(f"Could not check GPIO access: {e}")
        
        # Get the pin from board using the pin number
        try:
            pin = getattr(board, f"D{self.dht_pin}")
            logger.debug(f"Successfully mapped pin D{self.dht_pin} to board pin")
        except AttributeError:
            logger.error(f"Pin D{self.dht_pin} not available on this board")
            available_pins = [attr for attr in dir(board) if attr.startswith('D') and attr[1:].isdigit()]
            logger.error(f"Available pins: {available_pins}")
            self.dhtDevice = None
            return
        
        # Dynamically create the DHT sensor based on sensor type
        try:
            if self.sensor_type == "DHT22":
                self.dhtDevice = adafruit_dht.DHT22(pin)
            elif self.sensor_type == "DHT11":
                self.dhtDevice = adafruit_dht.DHT11(pin)
            else:
                # Fallback to DHT22 if sensor type is not recognized
                logger.warning(f"Unknown sensor type {self.sensor_type}, defaulting to DHT22")
                self.dhtDevice = adafruit_dht.DHT22(pin)
            logger.info(f"DHT{self.sensor_type} sensor initialized on pin D{self.dht_pin}")
        except Exception as e:
            logger.error(f"Failed to initialize DHT sensor: {e}")
            if IS_RASPBERRY_PI:
                logger.error("Common Raspberry Pi DHT issues:")
                logger.error("1. Check wiring connections")
                logger.error("2. Ensure DHT sensor is working")
                logger.error("3. Try a different GPIO pin")
                logger.error("4. Check if another process is using the pin")
            self.dhtDevice = None
    
    def get_pin(self) -> int | None:
        """Get current DHT pin"""
        return self.dht_pin
    
    def is_available(self) -> bool:
        """Check if DHT sensor is available and properly initialized"""
        return self.dhtDevice is not None
    
    def get_data(self) -> tuple[float | None, float | None]:
        """Get current temperature and humidity data"""
        with self.dht_lock:
            return self.latest_temperature, self.latest_humidity
    
    def register_temperature_callback(self, callback) -> None:
        """Register a callback function to be called when temperature changes significantly"""
        self.temperature_callbacks.append(callback)
    
    def register_humidity_callback(self, callback) -> None:
        """Register a callback function to be called when humidity changes significantly"""
        self.humidity_callbacks.append(callback)
    
    def _notify_temperature_callbacks(self, temperature: float) -> None:
        """Notify all registered temperature callbacks"""
        for callback in self.temperature_callbacks:
            try:
                callback(temperature)
            except Exception as e:
                logger.error(f"Error in temperature callback: {e}")
    
    def _notify_humidity_callbacks(self, humidity: float) -> None:
        """Notify all registered humidity callbacks"""
        for callback in self.humidity_callbacks:
            try:
                callback(humidity)
            except Exception as e:
                logger.error(f"Error in humidity callback: {e}")
    
    def _read_dht_temperature(self) -> None:
        """
        Read the temperature and humidity from the DHT sensor once
        and update the global variables.
        If the sensor returns invalid values (None or out of range), do not update globals.
        """
        
        # Check if DHT device is available
        if self.dhtDevice is None:
            logger.debug("DHT device not available, skipping reading")
            return
        
        # DHT sensors often fail on first attempt, so we retry
        max_retries = 3 if IS_RASPBERRY_PI else 1
        temperature = None
        humidity = None
        
        for attempt in range(max_retries):
            try:
                temperature = self.dhtDevice.temperature
                humidity = self.dhtDevice.humidity
                
                # If we got valid readings, break out of retry loop
                if temperature is not None and humidity is not None:
                    logger.debug(f"DHT read successful on attempt {attempt + 1}")
                    break
                    
            except Exception as e:
                error_str = str(e).lower()
                
                # These are normal DHT sensor errors that should trigger a retry
                if ("checksum did not validate" in error_str or 
                    "full buffer was not returned" in error_str or
                    "try again" in error_str):
                    if attempt < max_retries - 1:
                        logger.debug(f"DHT read attempt {attempt + 1} failed (normal), retrying...")
                        import time
                        time.sleep(0.1)  # Small delay before retry
                        continue
                    else:
                        logger.debug(f"DHT sensor failed after {max_retries} attempts: {e}")
                        return
                        
                # For other errors, don't retry
                elif IS_RASPBERRY_PI:
                    if "timed out" in error_str or "timeout" in error_str:
                        logger.warning(f"DHT sensor timeout - check wiring and power: {e}")
                    elif "permission" in error_str:
                        logger.error(f"Permission denied accessing GPIO - run as root or add user to gpio group: {e}")
                    elif "device or resource busy" in error_str:
                        logger.warning(f"GPIO pin busy - another process may be using it: {e}")
                    else:
                        logger.warning(f"DHT sensor read failed: {e}")
                else:
                    logger.error(f"Error reading DHT sensor: {e}")
                return
        
        # Process the readings if we got them
        if temperature is None and humidity is None:
            logger.debug("No valid DHT readings obtained after retries")
            return
            
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
                            # Notify callbacks about temperature change
                            self._notify_temperature_callbacks(rounded_temp)
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
                            # Notify callbacks about humidity change
                            self._notify_humidity_callbacks(rounded_humidity)
                            logged_info = True
                    
                    # Always log current humidity for debugging (unless we just logged at info level)
                    if not logged_info:
                        logger.debug(f"Humidity: {rounded_humidity}%")
                else:
                    logger.error("Humidity value not updated (None or out of range)")

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
