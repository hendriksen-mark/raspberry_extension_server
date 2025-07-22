from typing import Any
from bleak import BleakError
import asyncio
import threading

from eqiva_thermostat import EqivaException

import configManager
import logging
import logManager
from ServerObjects.dht_object import DHTObject
from ServerObjects.thermostat_object import ThermostatObject
from ServerObjects.fan_object import FanObject
from ServerObjects.klok_object import KlokObject
from ServerObjects.powerbutton_object import PowerButtonObject

logger: logging.Logger = logManager.logger.get_logger(__name__)
serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config

# Global shutdown events for immediate thread termination
_shutdown_event = threading.Event()
_thermostat_shutdown = threading.Event()
_dht_shutdown = threading.Event()
_fan_shutdown = threading.Event()
_klok_shutdown = threading.Event()
_powerbutton_shutdown = threading.Event()

# Async event for thermostat shutdown
_thermostat_shutdown_async = asyncio.Event()

def _ensure_async_event_loop():
    """Ensure async events are properly initialized for current event loop"""
    global _thermostat_shutdown_async
    try:
        # Check if event is still valid for current loop
        if _thermostat_shutdown_async._loop is not asyncio.get_running_loop():
            _thermostat_shutdown_async = asyncio.Event()
    except RuntimeError:
        # No running loop, create new event
        _thermostat_shutdown_async = asyncio.Event()

async def syncWithThermostats() -> None:
    """
    Synchronize the state of the thermostats with their actual state.
    """
    _ensure_async_event_loop()  # Ensure async event is valid for this loop
    
    while serverConfig["config"]["thermostats"]["enabled"] and not _thermostat_shutdown.is_set():
        logger.info("start thermostats sync")
        interval: int = serverConfig["config"]["thermostats"]["interval"]
        
        for thermostat in serverConfig["thermostats"].values():
            if _thermostat_shutdown.is_set():
                break
            thermostat: ThermostatObject = thermostat
            try:
                logger.debug("fetch " + thermostat.mac)
                await thermostat.poll_status()
                thermostat.failed_connection = False
            except BleakError as e:
                logger.error(f"Polling: BLE error for {thermostat.mac}: {e}")
                thermostat.failed_connection = True
                pass
            except EqivaException as e:
                logger.error(f"Polling: EqivaException for {thermostat.mac}: {e}")
                thermostat.failed_connection = True
                pass
            finally:
                try:
                    await thermostat.safe_disconnect()
                    logger.debug(f"Polling: Disconnected from {thermostat.mac}")
                except Exception as e:
                    logger.error(f"Polling: Error disconnecting from {thermostat.mac}: {e}")

        # Simple sleep with shutdown check - much more efficient
        sleep_time: float = max(10, interval)
        try:
            await asyncio.wait_for(
                _thermostat_shutdown_async.wait(),
                timeout=sleep_time
            )
            # If we get here, shutdown was requested
            break
        except asyncio.TimeoutError:
            # Timeout is expected - continue the loop
            continue


def syncWithThermostats_threaded() -> None:
    """
    Thread wrapper for the async syncWithThermostats function
    """
    loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(syncWithThermostats())
    except Exception as e:
        logger.error(f"Error in thermostat sync thread: {e}")
    finally:
        try:
            loop.close()
        except Exception as e:
            logger.error(f"Error closing sync loop: {e}")

def disconnectThermostats() -> None:
    """
    Disconnect all thermostats.
    """
    loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def cleanup_all():
        tasks: list[asyncio.Task] = []
        for thermostat in serverConfig["thermostats"].values():
            thermostat: ThermostatObject = thermostat
            try:
                # Create a timeout wrapper for each disconnect
                task: asyncio.Task = asyncio.wait_for(thermostat.safe_disconnect(), timeout=5.0)
                tasks.append(task)
            except Exception as e:
                logger.error(f"Cleanup: Error preparing disconnect for {thermostat.mac}: {e}")
        
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logger.error(f"Cleanup: Error during gather: {e}")
    
    try:
        logger.info("Disconnecting all thermostats...")
        loop.run_until_complete(cleanup_all())
    except Exception as e:
        logger.error(f"Cleanup: Error during cleanup: {e}")
    finally:
        try:
            loop.close()
        except Exception as e:
            logger.error(f"Cleanup: Error closing loop: {e}")
    
    logger.info("Cleanup: All thermostats disconnected.")

def run_dht_service() -> None:
    """
    Placeholder for DHT temperature reading logic.
    This function should be implemented to read from the DHT sensor.
    """
    while serverConfig["config"]["dht"]["enabled"] and not _dht_shutdown.is_set() and "dht" in serverConfig:
        interval: int = serverConfig["config"]["dht"]["interval"]
        logger.debug(f"Reading DHT temperature every {interval} seconds")
        try:
            dht: DHTObject = serverConfig["dht"]
            if dht:
                dht._read_dht_temperature()
        except Exception as e:
            logger.error(f"Error reading DHT temperature: {e}")
        
        # Use event.wait() instead of sleep loops for immediate shutdown
        if _dht_shutdown.wait(timeout=max(5, interval)):
            # Event was set - shutdown requested
            break

def run_fan_service() -> None:
    """
    Placeholder for fan service logic.
    This function should be implemented to control the fan based on temperature.
    """
    while serverConfig["config"]["fan"]["enabled"] and not _fan_shutdown.is_set() and "fan" in serverConfig:
        interval: int = serverConfig["config"]["fan"]["interval"]
        try:
            fan: FanObject = serverConfig["fan"]
            if fan:
                fan.run()
        except Exception as e:
            logger.error(f"Error in fan service: {e}")
        
        # Use event.wait() instead of sleep loops for immediate shutdown
        if _fan_shutdown.wait(timeout=max(5, interval)):
            # Event was set - shutdown requested
            break

def stop_fan_service() -> None:
    """
    Stop the fan service.
    This function should be implemented to clean up fan resources.
    """
    _fan_shutdown.set()  # Signal immediate shutdown
    try:
        fan: FanObject = serverConfig["fan"]
        if fan:
            fan.cleanup()
            logger.info("Fan service stopped successfully.")
    except Exception as e:
        logger.error(f"Error stopping fan service: {e}")

def run_klok_service() -> None:
    """
    Placeholder for klok service logic.
    This function should be implemented to update the klok display.
    """
    while serverConfig["config"]["klok"]["enabled"] and not _klok_shutdown.is_set() and "klok" in serverConfig:
        try:
            klok: KlokObject = serverConfig["klok"]
            if klok:
                klok.show()
        except Exception as e:
            logger.error(f"Error in klok service: {e}")
        
        # Use event.wait() with shorter timeout for responsive doublepoint updates
        if _klok_shutdown.wait(timeout=0.1):
            # Event was set - shutdown requested
            break

def stop_klok_service() -> None:
    """
    Stop the klok service.
    This function should be implemented to clean up klok resources.
    """
    _klok_shutdown.set()  # Signal immediate shutdown
    try:
        klok: KlokObject = serverConfig["klok"]
        if klok:
            klok.display.cleanup()
            logger.info("Klok service stopped successfully.")
    except Exception as e:
        logger.error(f"Error stopping klok service: {e}")

def run_powerbutton_service() -> None:
    """
    Placeholder for power button service logic.
    This function should be implemented to handle power button events.
    """
    while serverConfig["config"]["powerbutton"]["enabled"] and not _powerbutton_shutdown.is_set() and "powerbutton" in serverConfig:
        try:
            powerbutton: PowerButtonObject = serverConfig["powerbutton"]
            if powerbutton:
                powerbutton.run()
        except Exception as e:
            logger.error(f"Error in power button service: {e}")
        
        # Use event.wait() instead of sleep for immediate shutdown
        if _powerbutton_shutdown.wait(timeout=0.1):
            # Event was set - shutdown requested
            break

def stop_powerbutton_service() -> None:
    """
    Stop the power button service.
    This function should be implemented to clean up power button resources.
    """
    _powerbutton_shutdown.set()  # Signal immediate shutdown
    try:
        powerbutton: PowerButtonObject = serverConfig["powerbutton"]
        if powerbutton:
            powerbutton.cleanup()
            logger.info("Power button service stopped successfully.")
    except Exception as e:
        logger.error(f"Error stopping power button service: {e}")

def stop_dht_service() -> None:
    """
    Stop the DHT temperature reading service.
    """
    _dht_shutdown.set()  # Signal immediate shutdown
    logger.info("DHT service stopped.")

def stop_thermostat_service() -> None:
    """
    Stop the thermostat synchronization service.
    """
    _thermostat_shutdown.set()  # Signal immediate shutdown
    try:
        # Try to set async event if there's a running loop
        loop = asyncio.get_running_loop()
        loop.call_soon_threadsafe(_thermostat_shutdown_async.set)
    except RuntimeError:
        # No running loop, event will be recreated when needed
        pass
    logger.info("Thermostat service stopped.")

def stop_all_services() -> None:
    """
    Stop all services immediately by setting all shutdown events.
    """
    _shutdown_event.set()
    _thermostat_shutdown.set()
    try:
        # Try to set async event if there's a running loop
        loop = asyncio.get_running_loop()
        loop.call_soon_threadsafe(_thermostat_shutdown_async.set)
    except RuntimeError:
        # No running loop, event will be recreated when needed
        pass
    _dht_shutdown.set()
    _fan_shutdown.set()
    _klok_shutdown.set()
    _powerbutton_shutdown.set()
    logger.info("All stateFetch services shutdown events set.")
