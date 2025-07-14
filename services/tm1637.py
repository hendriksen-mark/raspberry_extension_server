import math
try:
    import RPi.GPIO as IO  # type: ignore
except ImportError:
    from services.dummy_import import DummyGPIO as IO

from time import sleep
# IO.setwarnings(False)
IO.setmode(IO.BCM)

HexDigits: list[int] = [0x3f, 0x06, 0x5b, 0x4f, 0x66, 0x6d, 0x7d,
             0x07, 0x7f, 0x6f, 0x77, 0x7c, 0x39, 0x5e, 0x79, 0x71]

ADDR_AUTO: int = 0x40
ADDR_FIXED: int = 0x44
STARTADDR: int = 0xC0

class TM1637:
    __doublePoint: bool = False
    __Clkpin: int = 0
    __Datapin: int = 0
    __brightness: int = 0
    #1.0  # default to max brightness
    __currentData: list[int] = [0, 0, 0, 0]

    def __init__(self, CLK: int, DIO: int) -> None:
        self.__Clkpin = CLK
        self.__Datapin = DIO
        IO.setup(self.__Clkpin, IO.OUT)
        IO.setup(self.__Datapin, IO.OUT)

    def cleanup(self) -> None:
        """Stop updating clock, turn off display, and cleanup GPIO"""
        self.Clear()
        IO.cleanup()

    def Clear(self) -> None:
        b: int = self.__brightness
        point: bool = self.__doublePoint
        self.__brightness = 0
        self.__doublePoint = False
        data: list[int] = [0x7F, 0x7F, 0x7F, 0x7F]
        self.Show(data)
        # Restore previous settings:
        self.__brightness = b
        self.__doublePoint = point

    def Show(self, data: list[int]) -> None:
        for i in range(0, 4):
            self.__currentData[i] = data[i]

        self.start()
        self.writeByte(ADDR_AUTO)
        self.br()
        self.writeByte(STARTADDR)
        for i in range(0, 4):
            self.writeByte(self.coding(data[i]))
        self.br()
        self.writeByte(0x88 + int(self.__brightness))
        self.stop()

    def SetBrightness(self, percent: float) -> None:
        """Accepts percent brightness from 0 - 1"""
        max_brightness: float = 7.0
        brightness: int = math.ceil(max_brightness * percent)
        if (brightness < 0):
            brightness = 0
        if(self.__brightness != brightness):
            self.__brightness = brightness
            self.Show(self.__currentData)

    def ShowDoublepoint(self, on: bool) -> None:
        """Show or hide double point divider"""
        if(self.__doublePoint != on):
            self.__doublePoint = on
            self.Show(self.__currentData)

    def writeByte(self, data: int) -> None:
        for i in range(0, 8):
            IO.output(self.__Clkpin, IO.LOW)
            if(data & 0x01):
                IO.output(self.__Datapin, IO.HIGH)
            else:
                IO.output(self.__Datapin, IO.LOW)
            data = data >> 1
            IO.output(self.__Clkpin, IO.HIGH)

        # wait for ACK
        IO.output(self.__Clkpin, IO.LOW)
        IO.output(self.__Datapin, IO.HIGH)
        IO.output(self.__Clkpin, IO.HIGH)
        IO.setup(self.__Datapin, IO.IN)

        while(IO.input(self.__Datapin)):
            sleep(0.001)
            if(IO.input(self.__Datapin)):
                IO.setup(self.__Datapin, IO.OUT)
                IO.output(self.__Datapin, IO.LOW)
                IO.setup(self.__Datapin, IO.IN)
        IO.setup(self.__Datapin, IO.OUT)

    def start(self) -> None:
        """send start signal to TM1637"""
        IO.output(self.__Clkpin, IO.HIGH)
        IO.output(self.__Datapin, IO.HIGH)
        IO.output(self.__Datapin, IO.LOW)
        IO.output(self.__Clkpin, IO.LOW)

    def stop(self) -> None:
        IO.output(self.__Clkpin, IO.LOW)
        IO.output(self.__Datapin, IO.LOW)
        IO.output(self.__Clkpin, IO.HIGH)
        IO.output(self.__Datapin, IO.HIGH)

    def br(self) -> None:
        """terse break"""
        self.stop()
        self.start()

    def coding(self, data: int) -> int:
        if(self.__doublePoint):
            pointData: int = 0x80
        else:
            pointData: int = 0

        if(data == 0x7F):
            data: int = 0
        else:
            data: int = HexDigits[data] + pointData
        return data
