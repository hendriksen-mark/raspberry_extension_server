import random
import logging
import importlib
from typing import Any
import logManager

logger: logging.Logger = logManager.logger.get_logger(__name__)


class DummyGPIO:
        BCM: str = "BCM"
        OUT: str = "OUT"
        IN: str = "IN"
        HIGH: int = 1
        LOW: int = 0
        PUD_UP: str = "PUD_UP"
        PUD_DOWN: str = "PUD_DOWN"
        PUD_OFF: str = "PUD_OFF"

        @staticmethod
        def setwarnings(state: bool) -> None:
            """Dummy setwarnings"""
            pass
        
        @staticmethod
        def setmode(mode: str) -> None:
            """Dummy setmode"""
            pass
        
        @staticmethod
        def setup(pin: int, mode: str, pull_up_down: str = "") -> None:
            """Dummy setup with pull_up_down parameter"""
            pass
        
        @staticmethod
        def output(pin: int, state: int) -> None:
            """Dummy output"""
            pass
        
        @staticmethod
        def input(pin: int) -> int:
            """Dummy input"""
            return 0
        
        @staticmethod
        def cleanup(channel: int | list[int] | tuple[int, ...] = -666) -> None:
            """Dummy cleanup"""
            pass

class DummyDHT:

        def __init__(self, sensor_type="DHT22"):
            logger.warning(f"Using DummyDHT")
            self.sensor_type = sensor_type

        @staticmethod
        def read_retry(sensor: int, pin: int) -> tuple[float, float]:
            temp: float = random.uniform(5.0, 30.0)  # Simulate a temperature reading
            humidity: float = random.uniform(0.0, 100.0)  # Simulate a humidity reading
            return humidity, temp

        @staticmethod
        def read(sensor: int, pin: int) -> tuple[float, float]:
            temp: float = random.uniform(5.0, 30.0)  # Simulate a temperature reading
            humidity: float = random.uniform(0.0, 100.0)  # Simulate a humidity reading
            return humidity, temp
        
        @staticmethod
        def DHT22(pin: int) -> 'DummyDHT':
            """Return a dummy DHT22 sensor instance"""
            return DummyDHT("DHT22")

        @staticmethod
        def DHT11(pin: int) -> 'DummyDHT':
            """Return a dummy DHT11 sensor instance"""
            return DummyDHT("DHT11")

        @staticmethod
        def DHT21(pin: int) -> 'DummyDHT':
            """Return a dummy DHT21 sensor instance"""
            return DummyDHT("DHT21")
        
        @staticmethod
        def is_dummy() -> bool:
            """Check if this is a dummy DHT sensor"""
            return True

        @property
        def temperature(self):
            """Return mock temperature with some variation"""
            return random.uniform(5.0, 30.0)  # Simulate a temperature reading
        
        @property 
        def humidity(self):
            """Return mock humidity with some variation"""
            return random.uniform(0.0, 100.0)  # Simulate a humidity reading
        
        def getReal(self):
            """Return the real adafruit_dht module if available, otherwise use the dummy class"""
            try:
                return importlib.import_module("adafruit_dht")
            except ModuleNotFoundError:
                logger.warning("adafruit_dht is not installed, using DummyDHT")
                return DummyDHT

class DummyPigpioInstance:
        def __init__(self) -> None:
            self.connected = True

        def set_PWM_frequency(self, gpio: int, frequency: int) -> None:
            """Dummy PWM frequency setter"""
            pass

        def set_PWM_dutycycle(self, gpio: int, duty_cycle: int) -> None:
            """Dummy PWM duty cycle setter"""
            pass

        def stop(self) -> None:
            """Dummy stop method"""
            pass
    
class DummyPigpio:
    @staticmethod
    def pi():
        """Return a dummy pigpio instance"""
        return DummyPigpioInstance()
        
class DummyBoard:
    """Dummy board class to simulate board pin access"""
    
    def __init__(self) -> None:
        """Initialize dummy board"""
        pass
    
    def __getattr__(self, name: str) -> Any:
        raise AttributeError(f"Using DummyBoard")
    
    @property
    def DNone(self) -> None:
        """Return a dummy pin object for DNone"""
        return None
