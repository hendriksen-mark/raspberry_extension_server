import logManager
from typing import Dict, Any
from datetime import datetime
from services.tm1637 import TM1637

logging = logManager.logger.get_logger(__name__)

class KlokService:
    def __init__(self, data: Dict[str, Any]) -> None:
        self.id = data.get("id", None)
        self.CLK_pin = data.get("CLK_pin", 24)
        self.DIO_pin = data.get("DIO_pin", 23)  # GPIO pin for the fan
        self.brightness = data.get("brightness", 0.0)  # Default brightness
        self.last_brightness = None  # Track last brightness to avoid unnecessary updates
        self.last_time = None
        self.last_doublepoint = None
        self.doublepoint = True  # Initialize doublepoint state
        self.power_state = True
        self.display = TM1637(self.CLK_pin, self.DIO_pin)

    def set_brightness(self, value: int) -> None:
        """Set the brightness of the display."""
        step = min(7, max(0, round((value / 100) * 7)))
        self.brightness = step / 7.0

    def show(self):
        if not self.power_state:
            if self.last_time is not None or self.last_brightness is not None or self.last_doublepoint is not None:
                self.display.Clear()
                self.last_time = None
                self.last_brightness = None
                self.last_doublepoint = None
            return

        now = datetime.now()
        hour, minute = now.hour, now.minute
        current_time = [hour // 10, hour % 10, minute // 10, minute % 10]

        # Update time display only if changed
        if self.last_time != current_time:
            self.display.Show(current_time)
            self.last_time = current_time

        # Update brightness only if changed
        if self.last_brightness != self.brightness:
            self.display.SetBrightness(self.brightness)
            self.last_brightness = self.brightness

        # Toggle and update doublepoint every loop
        if self.last_doublepoint != self.doublepoint:
            self.display.ShowDoublepoint(self.doublepoint)
            self.last_doublepoint = self.doublepoint

        self.doublepoint = not self.doublepoint

    def save(self) -> Dict[str, Any]:
        """Save the klok service configuration"""
        return {
            "id": self.id,
            "CLK_pin": self.CLK_pin,
            "DIO_pin": self.DIO_pin,
            "brightness": self.brightness
        }