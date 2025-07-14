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
        def setwarnings(state) -> None:
            """Dummy setwarnings"""
            pass
        
        @staticmethod
        def setmode(mode) -> None:
            """Dummy setmode"""
            pass
        
        @staticmethod
        def setup(pin, mode, pull_up_down=None) -> None:
            """Dummy setup with pull_up_down parameter"""
            pass
        
        @staticmethod
        def output(pin, state) -> None:
            """Dummy output"""
            pass
        
        @staticmethod
        def input(pin) -> int:
            """Dummy input"""
            return 0
        
        @staticmethod
        def cleanup() -> None:
            """Dummy cleanup"""
            pass