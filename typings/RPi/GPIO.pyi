"""Stub for RPi.GPIO - provides BCM pin naming conventions and GPIO control."""

from typing import Any, Literal

# Pin numbering modes
BCM: str
BOARD: str

# Pin modes
IN: str
OUT: str

# Pull-up/pull-down modes
PUD_OFF: str
PUD_DOWN: str
PUD_UP: str

# Pin values
LOW: int
HIGH: int

# Functions
def setwarnings(state: bool) -> None: ...
def setmode(mode: str) -> None: ...
def setup(pin: int, mode: str, pull_up_down: str = ...) -> None: ...
def output(pin: int, state: int) -> None: ...
def input(pin: int) -> int: ...
def cleanup(channel: int | list[int] | tuple[int, ...] | None = ...) -> None: ...
