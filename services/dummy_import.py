import random


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
        def setup(pin: int, mode: str, pull_up_down: str = None) -> None:
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
        def cleanup() -> None:
            """Dummy cleanup"""
            pass

class DummyDHT:
        DHT22: int = None

        def __init__(self, sensor_type="DHT22"):
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
        
        @property
        def temperature(self):
            """Return mock temperature with some variation"""
            return random.uniform(5.0, 30.0)  # Simulate a temperature reading
        
        @property 
        def humidity(self):
            """Return mock humidity with some variation"""
            return random.uniform(0.0, 100.0)  # Simulate a humidity reading

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
    
    def __init__(self):
        """Initialize dummy board"""
        pass
    
    def __getattr__(self, name):
        """Return a dummy pin object for any pin name (e.g., D18, D4, etc.)"""
        if name.startswith('D') and name[1:].isdigit():
            return DummyPin(name)
        raise AttributeError(f"DummyBoard has no attribute '{name}'")


class DummyPin:
    """Dummy pin class to simulate GPIO pins"""
    
    def __init__(self, pin_name):
        self.pin_name = pin_name
    
    def __str__(self):
        return f"DummyPin({self.pin_name})"
    
    def __repr__(self):
        return f"DummyPin({self.pin_name})"


# Create a dummy board instance that can be imported
board = DummyBoard()