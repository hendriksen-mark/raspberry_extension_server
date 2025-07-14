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

        @staticmethod
        def read_retry(sensor: int, pin: int) -> tuple[float, float]:
            return 22.0, 50.0
        
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
        
