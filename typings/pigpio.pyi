"""Stub for pigpio - interface to the pigpio daemon."""

from typing import Any, Callable

class pi:
    """Connection to pigpio daemon."""
    
    connected: bool
    
    def set_PWM_frequency(self, gpio: int, frequency: int) -> None:
        """Set PWM frequency for a GPIO pin."""
        ...
    
    def set_PWM_dutycycle(self, gpio: int, duty_cycle: int) -> None:
        """Set PWM duty cycle (0-255) for a GPIO pin."""
        ...
    
    def stop(self) -> None:
        """Stop the connection to pigpio daemon."""
        ...
