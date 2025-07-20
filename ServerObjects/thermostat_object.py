"""
Thermostat service for managing thermostat operations
"""
import asyncio
from time import localtime, strftime
from typing import Any
from bleak import BleakError

from eqiva_thermostat import Thermostat, Temperature, EqivaException
import logging
import logManager

logger: logging.Logger = logManager.logger.get_logger(__name__)


class ThermostatObject:
    """Service for managing thermostat operations"""
    
    def __init__(self, data: dict[str, Any]) -> None:
        self.id: str = data.get("id", None)  # Unique identifier for the thermostat
        self.mac: str = data.get("mac", None)  # MAC address of the thermostat
        self.failed_connection: bool = False  # Track failed connection
        self.targetHeatingCoolingState: int = data.get("targetHeatingCoolingState", 0)  # Default target state
        self.targetTemperature: float = data.get("targetTemperature", 0.0)  # Default target temperature
        self.currentHeatingCoolingState: int = data.get("currentHeatingCoolingState", 0)  # Default current state
        self.currentTemperature: float = data.get("currentTemperature", 0.0)  # Default DHT temperature
        self.currentRelativeHumidity: float = data.get("currentRelativeHumidity", 0.0)  # Default DHT humidity
        self.last_updated: str = data.get("last_updated", None)  # Last update timestamp
        self.first_seen: str = data.get("first_seen", strftime("%Y-%m-%d %H:%M:%S", localtime()))
        self.equiva_thermostat = Thermostat(self.mac)
        self.min_temperature = data.get("min_temperature", 5.0)  # Minimum temperature setting
        self.max_temperature = data.get("max_temperature", 30.0)  # Maximum
        self.DHT_connected: bool = False  # DHT connection status

    def calculate_heating_cooling_state(self, mode: dict[str, Any], valve: int = None) -> int:
        """
        Calculate the current heating/cooling state based on mode and valve position
        Possible return values:
        0 - Off
        1 - Heating
        2 - Cooling (not used in this context)
        """
        # Determine the state based on mode and valve
        if valve is not None:
            if 'OFF' in mode or (valve is not None and valve <= 0):
                return {"int": 0, "str": "Off"}  # Off
            elif valve and valve > 0:
                return {"int": 1, "str": "Heating"}  # Heating
            else:
                return {"int": 0, "str": "Off"}  # Off
        elif valve is None:
            if 'AUTO' in mode:
                return {"int": 3, "str": "Auto"}  # Auto mode
            elif 'MANUAL' in mode:
                return {"int": 1, "str": "Manual"}  # Manual mode
            else:
                return {"int": 0, "str": "Off"}  # Off
        #elif valve == 0 and 'MANUAL' in mode:
        #    return 2  # Not actively heating but in manual mode
        #elif 'AUTO' in mode:
        #    return 3  # Auto mode
        #else:
        #    return 1  # Default to heating for manual mode

    def update_dht_related_status(self, **kwargs) -> None:
        """Update DHT-related status for all MAC addresses"""
        if not self.DHT_connected:
            self.DHT_connected = True

        current_temp: float = kwargs.get('temperature')
        current_hum: float = kwargs.get('humidity')
        if current_temp is not None:
            self.currentTemperature = current_temp
        if current_hum is not None:
            self.currentRelativeHumidity = current_hum

        logger.debug(f"Updated DHT status for {self.mac} thermostat: temp={current_temp}°C, humidity={current_hum}%")

    def get_status(self) -> dict[str, Any]:
        """Get thermostat status for a given MAC address"""
        response: dict[str, Any] = {
            "targetHeatingCoolingState": self.targetHeatingCoolingState,
            "targetTemperature": self.targetTemperature,
            "currentHeatingCoolingState": self.currentHeatingCoolingState,
            "currentTemperature": self.targetTemperature
        }

        if self.DHT_connected:
            response["currentRelativeHumidity"] = self.currentRelativeHumidity
            response["currentTemperature"] = self.currentTemperature

        return response


    async def safe_connect(self) -> None:
        """Safely connect to thermostat"""
        try:
            await self.equiva_thermostat.connect()
            # Connection successful, reset failed connection flag
            if self.failed_connection:
                logger.info(f"Connection recovered for {self.mac}")
                self.failed_connection = False
        except Exception as e:
            logger.error(f"Failed to connect to {self.mac}: {e}")
            self.failed_connection = True
            raise

    async def safe_disconnect(self) -> None:
        """Safely disconnect from thermostat"""
        try:
            await self.equiva_thermostat.disconnect()
        except (TimeoutError, asyncio.CancelledError) as e:
            logger.warning(f"Disconnect timeout/cancelled for {self.equiva_thermostat.address}: {e}")
        except Exception as e:
            logger.error(f"Error disconnecting from {self.equiva_thermostat.address}: {e}")

    async def poll_status(self) -> None:
        """Poll thermostat status"""
        try:
            logger.debug(f"Polling: Attempting to connect to {self.mac}")
            await self.safe_connect()

            logger.debug(f"Polling: Connected to {self.mac}")
            await self.equiva_thermostat.requestStatus()
            logger.debug(f"Polling: Status requested from {self.mac}")
            mode: dict[str, Any] = self.equiva_thermostat.mode.to_dict()
            valve: float = self.equiva_thermostat.valve
            temp: float = self.equiva_thermostat.temperature.valueC

            target_mode_status = self.calculate_heating_cooling_state(mode)
            current_mode_status = self.calculate_heating_cooling_state(mode, valve)

            self.targetHeatingCoolingState = target_mode_status["int"]
            self.targetTemperature = temp
            self.currentHeatingCoolingState = current_mode_status["int"]
            self.last_updated = strftime("%Y-%m-%d %H:%M:%S", localtime())

            logger.debug(f"Polling: Status changed for {self.mac}: targetMode: {target_mode_status['str']}, currentMode: {current_mode_status['str']}, targetTemp: {self.targetTemperature}C")
        
        except Exception as e:
            logger.error(f"Polling failed for {self.mac}: {e}")
            self.failed_connection = True
            raise
        finally:
            try:
                await self.safe_disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from {self.mac}: {e}")

    async def set_temperature(self, temp: str) -> dict[str, Any]:
        """Set thermostat target temperature"""
        thermostat: Thermostat = self.equiva_thermostat
        mac: str = self.mac
        if not temp:
            return {"result": "error", "message": "Temperature value is required"}
        try:
            logger.info(f"Set temperature for {mac} to {temp}")
            await self.safe_connect()
            await thermostat.setTemperature(temperature=Temperature(valueC=float(temp)))
            return {"result": "ok", "temperature": float(temp)}
        except BleakError:
            logger.error(f"Device with address {mac} was not found")
            self.failed_connection = True
            return {"result": "error", "message": f"Device with address {mac} was not found"}
        except EqivaException as ex:
            logger.error(f"EqivaException for {mac}: {str(ex)}")
            self.failed_connection = True
            return {"result": "error", "message": str(ex)}
        except ValueError as ex:
            logger.error(f"Invalid temperature value for {mac}: {str(ex)}")
            return {"result": "error", "message": "Invalid temperature value"}
        except Exception as ex:
            logger.error(f"Unexpected error for {mac}: {str(ex)}")
            self.failed_connection = True
            return {"result": "error", "message": "Connection failed"}
        finally:
            try:
                await self.safe_disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from {mac}: {e}")
    
    async def set_mode(self, mode: str) -> dict[str, Any]:
        """Set thermostat heating/cooling mode"""
        thermostat: Thermostat = self.equiva_thermostat
        mac: str = self.mac
        if not mode:
            return {"result": "error", "message": "Mode value is required"}
        try:
            await self.safe_connect()
            if mode == '0':
                await thermostat.setTemperatureOff()
            elif mode in ('1', '2'):
                await thermostat.setModeManual()
            elif mode == '3':
                await thermostat.setModeAuto()
            else:
                return {"result": "error", "message": "Invalid mode value"}
            logger.info(f"Set mode for {mac} to {mode}")
            return {"result": "ok", "mode": int(mode)}
        except BleakError:
            logger.error(f"Device with address {mac} was not found")
            self.failed_connection = True
            return {"result": "error", "message": f"Device with address {mac} was not found"}
        except EqivaException as ex:
            logger.error(f"EqivaException for {mac}: {str(ex)}")
            self.failed_connection = True
            return {"result": "error", "message": str(ex)}
        except Exception as ex:
            logger.error(f"Unexpected error for {mac}: {str(ex)}")
            self.failed_connection = True
            return {"result": "error", "message": "Connection failed"}
        finally:
            try:
                await self.safe_disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from {mac}: {e}")

    def get_all_data(self) -> dict[str, Any]:
        """Get all thermostat data"""
        return {
            "mac": self.mac,
            "targetHeatingCoolingState": self.targetHeatingCoolingState,
            "targetTemperature": self.targetTemperature,
            "currentHeatingCoolingState": self.currentHeatingCoolingState,
            "currentTemperature": self.currentTemperature,
            "currentRelativeHumidity": self.currentRelativeHumidity,
            "last_updated": self.last_updated,
            "first_seen": self.first_seen,
            "DHT_connected": self.DHT_connected,
            "failed_connection": self.failed_connection,
            "min_temperature": self.min_temperature,
            "max_temperature": self.max_temperature,
        }

    def save(self) -> dict[str, Any]:
        """Save current thermostat state to a dictionary"""
        return {
            "mac": self.mac,
            "targetHeatingCoolingState": self.targetHeatingCoolingState,
            "targetTemperature": self.targetTemperature,
            "currentHeatingCoolingState": self.currentHeatingCoolingState,
            "currentTemperature": self.currentTemperature,
            "currentRelativeHumidity": self.currentRelativeHumidity,
            "first_seen": self.first_seen,
            "min_temperature": self.min_temperature,
            "max_temperature": self.max_temperature,
        }

    def is_online(self) -> bool:
        """Check if the thermostat is currently online (not failed connection)"""
        return not self.failed_connection
    
    def reset_connection_status(self) -> None:
        """Reset the failed connection status - useful for manual retry"""
        self.failed_connection = False
        logger.info(f"Connection status reset for {self.mac}")
