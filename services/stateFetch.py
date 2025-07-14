from time import sleep
from aioesphomeapi import Any
from bleak import BleakError
import asyncio

from eqiva_thermostat import EqivaException

import configManager
import logManager
from ServerObjects.dht_object import DHTObject
from ServerObjects.thermostat_object import ThermostatObject
from ServerObjects.fan_object import FanObject
from ServerObjects.klok_object import KlokObject
from ServerObjects.powerbutton_object import PowerButtonObject

logging = logManager.logger.get_logger(__name__)
serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config

async def syncWithThermostats() -> None:
    """
    Synchronize the state of the thermostats with their actual state.
    """
    while serverConfig["config"]["thermostats"]["enabled"]:
        logging.info("start thermostats sync")
        interval: int = serverConfig["config"]["thermostats"]["interval"]
        for thermostat in serverConfig["thermostats"].values():
            thermostat: ThermostatObject = thermostat
            try:
                logging.debug("fetch " + thermostat.mac)
                thermostat.poll_status()
                thermostat.failed_connection = False
            except BleakError as e:
                logging.error(f"Polling: BLE error for {thermostat.mac}: {e}")
                thermostat.failed_connection = True
                raise
            except EqivaException as e:
                logging.error(f"Polling: EqivaException for {thermostat.mac}: {e}")
                thermostat.failed_connection = True
                pass
            finally:
                try:
                    await thermostat.safe_disconnect()
                    logging.debug(f"Polling: Disconnected from {thermostat.mac}")
                except Exception as e:
                    logging.error(f"Polling: Error disconnecting from {thermostat.mac}: {e}")
            break

        sleep(10)  # wait at least 10 seconds before next sync
        i = 0
        while i < (interval - 10 if interval > 10 else 0):  # sync every x seconds
            i += 1
            sleep(1)


def syncWithThermostats_threaded() -> None:
    """
    Thread wrapper for the async syncWithThermostats function
    """
    loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(syncWithThermostats())
    except Exception as e:
        logging.error(f"Error in thermostat sync thread: {e}")
    finally:
        try:
            loop.close()
        except Exception as e:
            logging.error(f"Error closing sync loop: {e}")

async def disconnectThermostats() -> None:
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
                logging.error(f"Cleanup: Error preparing disconnect for {thermostat.mac}: {e}")
        
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception as e:
                logging.error(f"Cleanup: Error during gather: {e}")
    
    try:
        logging.info("Disconnecting all thermostats...")
        loop.run_until_complete(cleanup_all())
    except Exception as e:
        logging.error(f"Cleanup: Error during cleanup: {e}")
    finally:
        try:
            loop.close()
        except Exception as e:
            logging.error(f"Cleanup: Error closing loop: {e}")
    
    logging.info("Cleanup: All thermostats disconnected.")

def read_dht_temperature():
    """
    Placeholder for DHT temperature reading logic.
    This function should be implemented to read from the DHT sensor.
    """
    while serverConfig["config"]["dht"]["enabled"]:
        interval: int = serverConfig["config"]["dht"]["interval"]
        try:
            dht: DHTObject = serverConfig["dht"]
            logging.info(f"Reading DHT temperature...")
            dht._read_dht_temperature()
        except Exception as e:
            logging.error(f"Error reading DHT temperature: {e}")
        finally:
            sleep(5)
        i = 0
        while i < (interval - 5 if interval > 5 else 0):  # sync every x seconds
            i += 1
            sleep(1)

def run_fan_service():
    """
    Placeholder for fan service logic.
    This function should be implemented to control the fan based on temperature.
    """
    while serverConfig["config"]["fan"]["enabled"]:
        interval: int = serverConfig["config"]["fan"]["interval"]
        try:
            fan: FanObject = serverConfig["fan"]
            fan.run()
        except Exception as e:
            logging.error(f"Error in fan service: {e}")
        finally:
            sleep(5)
        i = 0
        while i < (interval - 5 if interval > 5 else 0):  # sync every x seconds
            i += 1
            sleep(1)

def run_klok_service():
    """
    Placeholder for klok service logic.
    This function should be implemented to update the klok display.
    """
    while serverConfig["config"]["klok"]["enabled"]:
        try:
            klok: KlokObject = serverConfig["klok"]
            klok.show()
        except Exception as e:
            logging.error(f"Error in klok service: {e}")
        finally:
            sleep(0.5)

def run_powerbutton_service():
    """
    Placeholder for power button service logic.
    This function should be implemented to handle power button events.
    """
    while serverConfig["config"]["powerbutton"]["enabled"]:
        try:
            powerbutton: PowerButtonObject = serverConfig["powerbutton"]
            powerbutton.run()
        except Exception as e:
            logging.error(f"Error in power button service: {e}")
        finally:
            sleep(0.1)