from typing import Any
try:
    import pigpio  # type: ignore
except ImportError:
    from services.dummy_import import DummyPigpio as pigpio  # Import a dummy pigpio class for testing

import logging
import logManager
from services.utils import get_pi_temp

logger: logging.Logger = logManager.logger.get_logger(__name__)

class FanObject:
    def __init__(self, data: dict[str, Any]) -> None:
        self.gpio_pin = data.get("gpio_pin", 18)
        self.pwm_frequency = data.get("pwm_frequency", 25000)  # Default PWM frequency
        self.min_temperature = data.get("min_temperature", 25)  # Minimum temperature setting
        self.max_temperature = data.get("max_temperature", 80)  # Maximum temperature setting
        self.min_speed = data.get("min_speed", 0)  # Minimum speed setting
        self.max_speed = data.get("max_speed", 255)  # Maximum speed setting
        self.cleanup_done = False
        self.last_logged_temp = None
        self.temp_change_threshold = 0.5  # Only log when temperature changes by more than 0.5°C
        self.pi = pigpio.pi()
        if not self.pi.connected:
            raise RuntimeError("Could not connect to pigpio daemon. Make sure pigpiod is running.")
        # Set PWM frequency and start with 0% duty cycle
        self.pi.set_PWM_frequency(self.gpio_pin, self.pwm_frequency)
        self.pi.set_PWM_dutycycle(self.gpio_pin, 0)

    def renormalize(self, n, range1, range2) -> float:
        """Scale n from range1 to range2."""
        delta1: float = range1[1] - range1[0]
        delta2: float = range2[1] - range2[0]
        return (delta2 * (n - range1[0]) / delta1) + range2[0]

    def cleanup(self) -> None:
        if not self.cleanup_done and self.pi.connected:
            self.pi.set_PWM_dutycycle(self.gpio_pin, 0)
            self.pi.stop()
            self.cleanup_done = True

    def run(self) -> None:
        temp: float = get_pi_temp()
        temp = max(self.min_temperature, min(self.max_temperature, temp))
        # Convert temp to pigpio duty cycle (0-255)
        duty_cycle: float = self.renormalize(temp, [self.min_temperature, self.max_temperature], [self.min_speed, self.max_speed])
        self.pi.set_PWM_dutycycle(self.gpio_pin, duty_cycle)
        
        # Only log when temperature changes significantly or this is the first reading
        if self.last_logged_temp is None or abs(temp - self.last_logged_temp) >= self.temp_change_threshold:
            logger.info(f"Fan: Temperature {temp}°C, Duty Cycle {duty_cycle}")
            self.last_logged_temp = temp

    def save(self) -> dict[str, Any]:
        """Save the fan service configuration"""
        return {
            "gpio_pin": self.gpio_pin,
            "pwm_frequency": self.pwm_frequency,
            "min_temperature": self.min_temperature,
            "max_temperature": self.max_temperature,
            "min_speed": self.min_speed,
            "max_speed": self.max_speed
        }


