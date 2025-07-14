try:
    import RPi.GPIO as IO  # type: ignore
except ImportError:
    from services.dummy_gpio import DummyGPIO as IO  # Import a dummy GPIO class for testing
import time
import subprocess
from typing import Any
import logManager
from threading import Event

logging = logManager.logger.get_logger(__name__)

class PowerButtonObject:
    def __init__(self, data: dict[str, Any]) -> None:
        self.button_pin = data.get("button_pin", 3)  # Default GPIO pin for the button
        self.long_press_duration = data.get("long_press_duration", 3.0)  # Default long press duration in seconds
        self.debounce_time = data.get("debounce_time", 0.05)  # Default debounce time in seconds
        self.shutdown_event = Event()
        IO.setmode(IO.BCM)
        IO.setup(self.button_pin, IO.IN, pull_up_down=IO.PUD_UP)
        self.last_press_time = time.time()

    def cleanup(self):
        """Clean up IO resources"""
        IO.cleanup()
        logging.info("IO cleanup completed")

    def button_pressed(self):
        """Check if button is currently pressed (LOW = pressed with pull-up)"""
        return IO.input(self.button_pin) == IO.LOW

    def wait_for_button_release(self):
        """Wait for button to be released"""
        while self.button_pressed():
            time.sleep(0.01)
            
    def execute_shutdown(self):
        """Execute system shutdown"""
        logging.info("Initiating system shutdown...")
        try:
            # Sync filesystem
            subprocess.run(['sync'], check=True)
            # Shutdown system
            subprocess.run(['sudo', 'shutdown', '-h', 'now'], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f"Shutdown command failed: {e}")
            
    def blink_led(self, pin=18, times=3):
        """Blink LED to indicate shutdown (optional - requires LED on IO 18)"""
        try:
            IO.setup(pin, IO.OUT)
            for _ in range(times):
                IO.output(pin, IO.HIGH)
                time.sleep(0.2)
                IO.output(pin, IO.LOW)
                time.sleep(0.2)
        except Exception as e:
            logging.debug(f"LED blink failed (optional): {e}")

    def run(self):
        """Main button monitoring loop"""
        logging.info("Power button service started. Press and hold for shutdown...")
        
        try:
            # Wait for button press (LOW state)
            if self.button_pressed():
                # Debounce
                time.sleep(self.debounce_time)
                if not self.button_pressed():
                    return
                    
                logging.info("Button pressed")
                press_start: float = time.time()

                # Wait while button is held down
                while self.button_pressed() and not self.shutdown_event.is_set():
                    press_duration: float = time.time() - press_start

                    if press_duration >= self.long_press_duration:
                        logging.info(f"Long press detected ({press_duration:.1f}s) - shutting down")
                        self.blink_led()  # Optional LED feedback
                        self.execute_shutdown()
                        return
                        
                    time.sleep(0.1)
                
                # Button released
                press_duration: float = time.time() - press_start
                if press_duration < self.long_press_duration:
                    logging.info(f"Short press ({press_duration:.1f}s) - button event logged")
                
                # Wait for button to be fully released
                self.wait_for_button_release()
                time.sleep(self.debounce_time)
        except Exception as e:
            logging.error(f"Error in main loop: {e}")
        finally:
            self.cleanup()

    def save(self) -> dict[str, Any]:
        """Save the power button configuration"""
        return {
            "button_pin": self.button_pin,
            "long_press_duration": self.long_press_duration,
            "debounce_time": self.debounce_time
        }