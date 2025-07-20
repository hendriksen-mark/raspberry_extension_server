try:
    import RPi.GPIO as IO  # type: ignore
except ImportError:
    from services.dummy_import import DummyGPIO as IO  # Import a dummy GPIO class for testing
import time
import subprocess
from typing import Any
import logging
import logManager
from threading import Event

logger: logging.Logger = logManager.logger.get_logger(__name__)

class PowerButtonObject:
    def __init__(self, data: dict[str, Any]) -> None:
        self.button_pin: float = data.get("button_pin", 3)  # Default GPIO pin for the button
        self.long_press_duration: float = data.get("long_press_duration", 3.0)  # Default long press duration in seconds
        self.debounce_time: float = data.get("debounce_time", 0.05)  # Default debounce time in seconds
        self.shutdown_event: Event = Event()
        IO.setmode(IO.BCM)
        IO.setup(self.button_pin, IO.IN, pull_up_down=IO.PUD_UP)
        self.last_press_time: float = time.time()

    def cleanup(self) -> None:
        """Clean up IO resources"""
        IO.cleanup()
        logger.info("IO cleanup completed")

    def button_pressed(self) -> bool:
        """Check if button is currently pressed (LOW = pressed with pull-up)"""
        return IO.input(self.button_pin) == IO.LOW

    def wait_for_button_release(self) -> None:
        """Wait for button to be released"""
        while self.button_pressed():
            time.sleep(0.01)

    def execute_shutdown(self) -> None:
        """Execute system shutdown"""
        logger.info("Initiating system shutdown...")
        try:
            # Sync filesystem
            subprocess.run(['sync'], check=True)
            # Shutdown system
            subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Shutdown command failed: {e}")

    def blink_led(self, pin=18, times=3) -> None:
        """Blink LED to indicate shutdown (optional - requires LED on IO 18)"""
        try:
            IO.setup(pin, IO.OUT)
            for _ in range(times):
                IO.output(pin, IO.HIGH)
                time.sleep(0.2)
                IO.output(pin, IO.LOW)
                time.sleep(0.2)
        except Exception as e:
            logger.debug(f"LED blink failed (optional): {e}")

    def run(self) -> None:
        """Main button monitoring loop"""
        logger.info("Power button service started. Press and hold for shutdown...")
        
        try:
            # Wait for button press (LOW state)
            if self.button_pressed():
                # Debounce
                time.sleep(self.debounce_time)
                if not self.button_pressed():
                    return
                    
                logger.info("Button pressed")
                press_start: float = time.time()

                # Wait while button is held down
                while self.button_pressed() and not self.shutdown_event.is_set():
                    press_duration: float = time.time() - press_start

                    if press_duration >= self.long_press_duration:
                        logger.info(f"Long press detected ({press_duration:.1f}s) - shutting down")
                        self.blink_led()  # Optional LED feedback
                        self.execute_shutdown()
                        return
                        
                    time.sleep(0.1)
                
                # Button released
                press_duration: float = time.time() - press_start
                if press_duration < self.long_press_duration:
                    logger.info(f"Short press ({press_duration:.1f}s) - button event logged")
                
                # Wait for button to be fully released
                self.wait_for_button_release()
                time.sleep(self.debounce_time)
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.cleanup()

    def get_all_data(self) -> dict[str, Any]:
        """Get all power button service data"""
        return {
            "button_pin": self.button_pin,
            "long_press_duration": self.long_press_duration,
            "debounce_time": self.debounce_time
        }

    def save(self) -> dict[str, Any]:
        """Save the power button configuration"""
        return self.get_all_data()