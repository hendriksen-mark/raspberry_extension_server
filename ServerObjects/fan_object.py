from typing import Any
try:
    import pigpio  # type: ignore
except ImportError:
    from services.dummy_import import DummyPigpio as pigpio  # Import a dummy pigpio class for testing

import logging
import logManager
import threading
from services.utils import get_pi_temp

logger: logging.Logger = logManager.logger.get_logger(__name__)

class FanObject:
    def __init__(self, data: dict[str, Any]) -> None:
        self.gpio_pin: int = data.get("gpio_pin", 18)
        self.pwm_frequency: int = data.get("pwm_frequency", 25000)  # Default PWM frequency
        self.min_temperature: int = data.get("min_temperature", 25)  # Minimum temperature setting
        self.max_temperature: int = data.get("max_temperature", 80)  # Maximum temperature setting
        self.min_speed: int = data.get("min_speed", 0)  # Minimum speed setting
        self.max_speed: int = data.get("max_speed", 255)  # Maximum speed setting
        self.cleanup_done: bool = False
        self.last_logged_temp: float | None = None
        self.temp_change_threshold: float = data.get("temp_change_threshold", 0.5)  # Only log when temperature changes by more than 0.5°C
        self.full_speed_timer: threading.Timer | None = None
        self.is_full_speed_mode: bool = False
        self.full_speed_time_duration: int = data.get("full_speed_time_duration", 5)  # Duration for full speed mode in seconds
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
            # Cancel any pending timer
            if self.full_speed_timer:
                self.full_speed_timer.cancel()
            self.pi.set_PWM_dutycycle(self.gpio_pin, 0)
            self.pi.stop()
            self.cleanup_done = True

    def run(self) -> None:
        # Skip normal temperature control if in full speed mode
        if self.is_full_speed_mode:
            return
            
        temp: float = get_pi_temp()
        temp = max(self.min_temperature, min(self.max_temperature, temp))
        # Convert temp to pigpio duty cycle (0-255)
        duty_cycle: float = self.renormalize(temp, [self.min_temperature, self.max_temperature], [self.min_speed, self.max_speed])
        self.pi.set_PWM_dutycycle(self.gpio_pin, duty_cycle)
        
        # Only log when temperature changes significantly or this is the first reading
        if self.last_logged_temp is None or abs(temp - self.last_logged_temp) >= self.temp_change_threshold:
            logger.info(f"Fan: Temperature {temp}°C, Duty Cycle {duty_cycle}")
            self.last_logged_temp = temp

    def setFull(self) -> None:
        """Set the fan to full speed for a specified duration, then return to normal operation."""
        # Cancel any existing timer
        if self.full_speed_timer:
            self.full_speed_timer.cancel()
        
        # Set full speed mode
        self.is_full_speed_mode = True
        self.pi.set_PWM_dutycycle(self.gpio_pin, self.max_speed)
        logger.info("Fan set to full speed for 5 seconds")
        
        # Set timer to return to normal after 5 seconds
        self.full_speed_timer = threading.Timer(self.full_speed_time_duration, self._return_to_normal)
        self.full_speed_timer.start()

    def _return_to_normal(self) -> None:
        """Return fan to normal temperature-based operation."""
        self.is_full_speed_mode = False
        self.full_speed_timer = None
        logger.info("Fan returning to normal temperature-based operation")
        # Immediately run normal operation to set appropriate speed
        self.run()

    def get_all_data(self) -> dict[str, Any]:
        """Get all fan service data"""
        return {
            "gpio_pin": self.gpio_pin,
            "pwm_frequency": self.pwm_frequency,
            "min_temperature": self.min_temperature,
            "max_temperature": self.max_temperature,
            "min_speed": self.min_speed,
            "max_speed": self.max_speed,
            "temp_change_threshold": self.temp_change_threshold,
            "full_speed_time_duration": self.full_speed_time_duration,
        }

    def save(self) -> dict[str, Any]:
        """Save the fan service configuration"""
        return self.get_all_data()


