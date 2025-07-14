class DummyGPIO:
        BCM = "BCM"
        OUT = "OUT"
        IN = "IN"
        HIGH = 1
        LOW = 0
        PUD_UP = "PUD_UP"
        PUD_DOWN = "PUD_DOWN"
        PUD_OFF = "PUD_OFF"
        
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