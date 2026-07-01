import logging
from typing import Any
from datetime import datetime
import time

import logManager

from services.tm1637 import TM1637

logger: logging.Logger = logManager.logger.get_logger(__name__)

class KlokObject:
    def __init__(self, data: dict[str, Any]) -> None:
        self.clk_pin: int = data.get("CLK_pin", 24)
        self.dio_pin: int = data.get("DIO_pin", 23)  # GPIO pin for the fan
        self.brightness: float = data.get("brightness", 0.0)  # Default brightness
        self.last_brightness: float | None = None  # Track last brightness to avoid unnecessary updates
        self.last_time: list[int] | None = None
        self.last_double_point: bool | None = None
        self.double_point: bool = True  # Initialize doublepoint state
        self.power_state: bool = True
        self.last_double_point_toggle: float = time.time()  # Track when doublepoint was last toggled
        self.display: TM1637 = TM1637(self.clk_pin, self.dio_pin)

    def set_brightness(self, value: int) -> None:
        """Set the brightness of the display."""
        step: int = min(7, max(0, round((value / 100) * 7)))
        self.brightness = step / 7.0

    def show(self) -> None:
        if not self.power_state:
            if self.last_time is not None or self.last_brightness is not None or self.last_double_point is not None:
                self.display.clear()
                self.last_time = None
                self.last_brightness = None
                self.last_double_point = None
            return

        now: datetime = datetime.now()
        hour, minute = now.hour, now.minute
        current_time = [hour // 10, hour % 10, minute // 10, minute % 10]

        # Update time display only if changed
        if self.last_time != current_time:
            self.display.show(current_time)
            self.last_time = current_time

        # Update brightness only if changed
        if self.last_brightness != self.brightness:
            self.display.set_brightness(self.brightness)
            self.last_brightness = self.brightness

        # Toggle doublepoint every 0.5 seconds based on time, not call frequency
        current_time_seconds: float = time.time()
        if current_time_seconds - self.last_double_point_toggle >= 0.5:
            self.double_point = not self.double_point
            self.last_double_point_toggle = current_time_seconds

        # Update doublepoint only if changed
        if self.last_double_point != self.double_point:
            self.display.show_double_point(self.double_point)
            self.last_double_point = self.double_point

    def toggle_power(self) -> None:
        """Toggle the power state"""
        self.power_state = not self.power_state

    def set_power(self, state: bool) -> None:
        """Set the power state"""
        self.power_state = state

    def get_brightness_percent(self) -> int:
        """Get brightness as percentage"""
        return int(self.brightness * 100)

    def get_all_data(self) -> dict[str, Any]:
        """Get all klok service data"""
        return {
            "CLK_pin": self.clk_pin,
            "DIO_pin": self.dio_pin,
            "brightness": self.get_brightness_percent(),
            "power_state": self.power_state
        }

    def save(self) -> dict[str, Any]:
        """Save the klok service configuration"""
        return {
            "CLK_pin": self.clk_pin,
            "DIO_pin": self.dio_pin,
            "brightness": self.brightness
        }
