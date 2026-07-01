"""Dummy hardware stubs used when running without Raspberry Pi hardware."""
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
    def setwarnings(_state: bool) -> None:
        """Dummy setwarnings"""

    @staticmethod
    def setmode(_mode: str) -> None:
        """Dummy setmode"""

    @staticmethod
    def setup(_pin: int, _mode: str, pull_up_down: str = "") -> None:
        """Dummy setup with pull_up_down parameter"""

    @staticmethod
    def output(_pin: int, _state: int) -> None:
        """Dummy output"""

    @staticmethod
    def input(_pin: int) -> int:
        """Dummy input"""
        return 0

    @staticmethod
    def cleanup(_channel: int | list[int] | tuple[int, ...] = -666) -> None:
        """Dummy cleanup"""

class DummyDHT:

    def __init__(self, sensor_type="DHT22"):
        logger.warning("Using DummyDHT")
        self.sensor_type = sensor_type

    @staticmethod
    def read_retry(_sensor: int, _pin: int) -> tuple[float, float]:
        temp: float = random.uniform(5.0, 30.0)  # Simulate a temperature reading
        humidity: float = random.uniform(0.0, 100.0)  # Simulate a humidity reading
        return humidity, temp

    @staticmethod
    def read(_sensor: int, _pin: int) -> tuple[float, float]:
        temp: float = random.uniform(5.0, 30.0)  # Simulate a temperature reading
        humidity: float = random.uniform(0.0, 100.0)  # Simulate a humidity reading
        return humidity, temp

    @staticmethod
    def DHT22(_pin: int) -> 'DummyDHT': # pylint: disable=invalid-name
        """Return a dummy DHT22 sensor instance"""
        return DummyDHT("DHT22")

    @staticmethod
    def DHT11(_pin: int) -> 'DummyDHT': # pylint: disable=invalid-name
        """Return a dummy DHT11 sensor instance"""
        return DummyDHT("DHT11")

    @staticmethod
    def DHT21(_pin: int) -> 'DummyDHT': # pylint: disable=invalid-name
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

    def getReal(self): # pylint: disable=invalid-name
        """Return the real adafruit_dht module if available, otherwise use the dummy class"""
        try:
            return importlib.import_module("adafruit_dht")
        except ModuleNotFoundError:
            logger.warning("adafruit_dht is not installed, using DummyDHT")
            return DummyDHT

class DummyPigpioInstance:
    def __init__(self) -> None:
        self.connected = True

    def set_PWM_frequency(self, gpio: int, frequency: int) -> None: # pylint: disable=invalid-name
        """Dummy PWM frequency setter"""

    def set_PWM_dutycycle(self, gpio: int, duty_cycle: int) -> None: # pylint: disable=invalid-name
        """Dummy PWM duty cycle setter"""

    def stop(self) -> None:
        """Dummy stop method"""

class DummyPigpio:
    @staticmethod
    def pi():
        """Return a dummy pigpio instance"""
        return DummyPigpioInstance()

class DummyBoard:
    """Dummy board class to simulate board pin access"""

    def __init__(self) -> None:
        """Initialize dummy board"""

    def __getattr__(self, name: str) -> Any:
        raise AttributeError("Using DummyBoard")

    @property
    def DNone(self) -> None:  # pylint: disable=invalid-name
        """Return a dummy pin object for DNone"""
        return None


def DummyColor(r: int, g: int, b: int, w: int = 0) -> int: # pylint: disable=invalid-name
    """Mimic rpi_ws281x.Color – pack WRGB into a single integer."""
    return (w << 24) | (r << 16) | (g << 8) | b


class DummyPixelStrip:
    """Mimic rpi_ws281x.PixelStrip for dev/testing without hardware."""

    def __init__(
        self,
        num: int,
        _pin: int,
        _freq_hz: int = 800_000,
        _dma: int = 5,
        _invert: bool = False,
        brightness: int = 255,
        _channel: int = 0,
    ) -> None:
        logger.warning("Using DummyPixelStrip (rpi_ws281x not available)")
        self._leds: list[int] = [0] * num
        self._brightness: int = brightness

    def begin(self) -> None:
        pass

    def setPixelColor(self, n: int, color: int) -> None: # pylint: disable=invalid-name
        if 0 <= n < len(self._leds):
            self._leds[n] = color

    def show(self) -> None:
        pass

    def setBrightness(self, brightness: int) -> None: # pylint: disable=invalid-name
        self._brightness = brightness

    def numPixels(self) -> int: # pylint: disable=invalid-name
        return len(self._leds)
