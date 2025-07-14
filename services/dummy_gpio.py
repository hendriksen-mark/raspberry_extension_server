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
        def setwarnings(state):
            """Dummy setwarnings"""
            pass
        
        @staticmethod
        def setmode(mode):
            """Dummy setmode"""
            pass
        
        @staticmethod
        def setup(pin, mode, pull_up_down=None):
            """Dummy setup with pull_up_down parameter"""
            pass
        
        @staticmethod
        def output(pin, state):
            """Dummy output"""
            pass
        
        @staticmethod
        def input(pin):
            """Dummy input"""
            return 0
        
        @staticmethod
        def cleanup():
            """Dummy cleanup"""
            pass