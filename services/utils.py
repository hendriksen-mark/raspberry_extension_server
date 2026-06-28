"""
Utility functions for the API
"""
import asyncio
from functools import wraps
import subprocess
import os
from typing import Any, Callable


def async_route(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle async functions in Flask routes"""
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapper


def validate_mac_address(mac: str) -> bool:
    """Validate MAC address format"""
    if not mac:
        return False
    formatted_mac: str = format_mac(mac)
    # Basic MAC validation - should be 6 groups of 2 hex digits
    parts: list[str] = formatted_mac.split(':')
    if len(parts) != 6:
        return False
    for part in parts:
        if len(part) != 2 or not all(c in '0123456789ABCDEF' for c in part):
            return False
    return True


def format_mac(mac: str) -> str:
    """Format MAC address to standard format"""
    return mac.replace('-', ':').upper()


def get_pi_temp() -> float:
    """Read the CPU temperature and return it as a float in degrees Celsius."""
    base_path = "/sys/class/thermal"

    if os.path.exists(base_path):
        # Search for a thermal zone matching known CPU sensor type names
        for folder in os.listdir(base_path):
            if folder.startswith("thermal_zone"):
                zone_path = os.path.join(base_path, folder)
                type_file = os.path.join(zone_path, "type")
                temp_file = os.path.join(zone_path, "temp")

                if os.path.exists(type_file) and os.path.exists(temp_file):
                    with open(type_file, "r") as f:
                        zone_type = f.read().strip().lower()

                    if any(kw in zone_type for kw in ["x86_pkg_temp", "cpu-thermal", "soc_thermal", "coretemp"]):
                        with open(temp_file, "r") as tf:
                            try:
                                return round(float(tf.read().strip()) / 1000.0, 2)
                            except ValueError:
                                continue

        # Fallback: return the highest plausible temperature zone
        highest_temp = -1.0
        for folder in os.listdir(base_path):
            if folder.startswith("thermal_zone"):
                temp_file = os.path.join(base_path, folder, "temp")
                if os.path.exists(temp_file):
                    try:
                        with open(temp_file, "r") as tf:
                            t = float(tf.read().strip()) / 1000.0
                            if 5.0 < t < 100.0 and t > highest_temp:
                                highest_temp = t
                    except ValueError:
                        continue

        if highest_temp > -1.0:
            return round(highest_temp, 2)

    # Fall back to vcgencmd (works on Raspberry Pi host)
    try:
        output: subprocess.CompletedProcess = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, check=True)
        temp_str: str = output.stdout.decode()
        return float(temp_str.split('=')[1].split('\'')[0])
    except (IndexError, ValueError, subprocess.CalledProcessError, FileNotFoundError, PermissionError):
        pass

    raise RuntimeError('Could not get temperature')

def nextFreeId(serverConfig: dict[str, Any], element: str) -> str:
    """
    Find the next free ID for a given element in the server configuration.

    Args:
        serverConfig (dict[str, Any]): The server configuration.
        element (str): The element to find the next free ID for.

    Returns:
        str: The next free ID as a string.
    """
    i: int = 1
    while str(i) in serverConfig[element]:
        i += 1
    return str(i)
