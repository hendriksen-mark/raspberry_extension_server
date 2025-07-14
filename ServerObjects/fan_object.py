from typing import Dict, Any
try:
    import pigpio  # type: ignore
except ImportError:
    class DummyPigpioInstance:
        def __init__(self):
            self.connected = True
        
        def set_PWM_frequency(self, gpio, frequency):
            """Dummy PWM frequency setter"""
            pass
        
        def set_PWM_dutycycle(self, gpio, duty_cycle):
            """Dummy PWM duty cycle setter"""
            pass
        
        def stop(self):
            """Dummy stop method"""
            pass
    
    class DummyPigpio:
        @staticmethod
        def pi():
            """Return a dummy pigpio instance"""
            return DummyPigpioInstance()
    
    pigpio = DummyPigpio()

import logManager
from services.utils import get_pi_temp

logging = logManager.logger.get_logger(__name__)

class FanObject:
    def __init__(self, data: Dict[str, Any]) -> None:
        self.id = data.get("id", None)
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

    def renormalize(self, n, range1, range2):
        """Scale n from range1 to range2."""
        delta1 = range1[1] - range1[0]
        delta2 = range2[1] - range2[0]
        return (delta2 * (n - range1[0]) / delta1) + range2[0]
    
    def cleanup(self):
        if not self.cleanup_done and self.pi.connected:
            self.pi.set_PWM_dutycycle(self.gpio_pin, 0)
            self.pi.stop()
            self.cleanup_done = True

    def run(self):
        temp = get_pi_temp()
        temp = max(self.min_temperature, min(self.max_temperature, temp))
        # Convert temp to pigpio duty cycle (0-255)
        duty_cycle = self.renormalize(temp, [self.min_temperature, self.max_temperature], [self.min_speed, self.max_speed])
        self.pi.set_PWM_dutycycle(self.gpio_pin, duty_cycle)
        
        # Only log when temperature changes significantly or this is the first reading
        if self.last_logged_temp is None or abs(temp - self.last_logged_temp) >= self.temp_change_threshold:
            logging.info(f"Fan: Temperature {temp}°C, Duty Cycle {duty_cycle}")
            self.last_logged_temp = temp

    def save(self) -> Dict[str, Any]:
        """Save the fan service configuration"""
        return {
            "id": self.id,
            "gpio_pin": self.gpio_pin,
            "pwm_frequency": self.pwm_frequency,
            "min_temperature": self.min_temperature,
            "max_temperature": self.max_temperature,
            "min_speed": self.min_speed,
            "max_speed": self.max_speed
        }


