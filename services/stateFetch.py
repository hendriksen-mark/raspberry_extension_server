from time import sleep
from bleak import BleakError
import asyncio

from eqiva_thermostat import EqivaException

import configManager
import logManager

logging = logManager.logger.get_logger(__name__)
serverConfig = configManager.serverConfig.yaml_config

async def syncWithThermostats() -> None:
    """
    Synchronize the state of the thermostats with their actual state.
    """
    while True:
        logging.info("start thermostats sync")
        for key, thermostat in serverConfig["thermostats"].items():
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
        while i < (serverConfig["config"]["sync_interval"] - 10 if serverConfig["config"]["sync_interval"] > 10 else 0):  # sync every x seconds
            i += 1
            sleep(1)

async def disconnectThermostats() -> None:
    """
    Disconnect all thermostats.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def cleanup_all():
        tasks = []
        for key, thermostat in serverConfig["thermostats"].items():
            try:
                # Create a timeout wrapper for each disconnect
                task = asyncio.wait_for(thermostat.safe_disconnect(), timeout=5.0)
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
    while True:
        try:
            # Assuming serverConfig["dht"] has a method to read temperature
            logging.info("Reading DHT temperature...")
            serverConfig["dht"]._read_dht_temperature()
        except Exception as e:
            logging.error(f"Error reading DHT temperature: {e}")
        finally:
            sleep(5)
        i = 0
        while i < (serverConfig["config"]["dht_interval"] - 5 if serverConfig["config"]["dht_interval"] > 5 else 0):  # sync every x seconds
            i += 1
            sleep(1)