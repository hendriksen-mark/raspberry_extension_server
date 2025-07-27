from .argumentHandler import parse_arguments
import os
import subprocess
import logging
import logManager
import yaml
from copy import deepcopy
from typing import Any, Optional
import sys
from ServerObjects.thermostat_object import ThermostatObject
from ServerObjects.dht_object import DHTObject
from ServerObjects.klok_object import KlokObject
from ServerObjects.fan_object import FanObject
from ServerObjects.powerbutton_object import PowerButtonObject

logger: logging.Logger = logManager.logger.get_logger(__name__)

class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data: Any) -> bool:
        return True

def _open_yaml(path: str) -> Any:
    """
    Open a YAML file and return its contents.

    Args:
        path (str): The path to the YAML file.

    Returns:
        Any: The contents of the YAML file.
    """
    with open(path, 'r', encoding="utf-8") as fp:
        return yaml.load(fp, Loader=yaml.FullLoader)

def _write_yaml(path: str, contents: Any) -> None:
    """
    Write contents to a YAML file.

    Args:
        path (str): The path to the YAML file.
        contents (Any): The contents to write to the YAML file.
    """
    with open(path, 'w', encoding="utf-8") as fp:
        yaml.dump(contents, fp, Dumper=NoAliasDumper, allow_unicode=True, sort_keys=False)

class Config:
    yaml_config: Optional[dict[str, Any]] = None
    argsDict: dict[str, Any] = parse_arguments()
    configDir: str = argsDict["CONFIG_PATH"]
    runningDir: str = argsDict["RUNNING_PATH"]
    ip: str = argsDict["HOST_IP"]
    argDebug: bool = argsDict["DEBUG"]
    bindIp: str = argsDict["BIND_IP"]
    httpPort: int = argsDict["HTTP_PORT"]

    def __init__(self) -> None:
        """
        Initialize the Config class.
        """
        if not os.path.exists(self.configDir):
            os.makedirs(self.configDir)

    def _set_default_config_values(self, config: dict[str, Any]) -> None:
        """
        Set default configuration values.

        Args:
            config (dict[str, Any]): The configuration dictionary.
        """
        defaults: dict[str, Any] = {
            "users": {
                "admin": {
                    "password": "pbkdf2:sha256:150000$bqqXSOkI$199acdaf81c18f6ff2f29296872356f4eb78827784ce4b3f3b6262589c788742"
                }
            },
            "thermostats": {
                "enabled": False,
                "interval": 300
            },
            "dht": {
                "enabled": False,
                "interval": 5
            },
            "klok": {
                "enabled": False
            },
            "fan": {
                "enabled": False,
                "interval": 5
            },
            "powerbutton": {
                "enabled": False
            },
            "webserver": {
                "interval": 2
            },
            "swupdate2": {
                "autoinstall": {
                    "on": False,
                    "updatetime": "T14:00:00"
                },
                "checkforupdate": False,
                "lastchange": "2020-12-13T10:30:15",
                "state": "noupdates",
                "install": False
            },
            "system": {
                "loglevel": "INFO",
                "branch": "main"
            },
        }
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
        return config

    def _upgrade_config(self, config: dict[str, Any]) -> None:
        """
        Upgrade the configuration if necessary.

        Args:
            config (Dict[str, Any]): The configuration dictionary.
        """
        # Only set branch to default if it's missing (new installation)
        if "branch" not in config["system"]:
            config["system"]["branch"] = "main"
        
        if "loglevel" not in config["system"] or config["system"]["loglevel"] != ("DEBUG" if self.argDebug else "INFO"):
            config["system"]["loglevel"] = "DEBUG" if self.argDebug else "INFO"
        logManager.logger.configure_logger(config["system"]["loglevel"])
        logger.info(f"Debug logging {'enabled' if self.argDebug else 'disabled'}!")
        return config

    def _load_yaml_file(self, filename: str, default: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        """
        Load a YAML file and return its contents.

        Args:
            filename (str): The name of the YAML file.
            default (Optional[dict[str, Any]]): The default value if the file does not exist.

        Returns:
            Optional[dict[str, Any]]: The contents of the YAML file or the default value.
        """
        path: str = os.path.join(self.configDir, filename)
        if os.path.exists(path):
            return _open_yaml(path)
        return default

    def _load_thermostats(self) -> None:
        """
        Load thermostats from the YAML configuration.
        """
        thermostats: dict[str, Any] = self._load_yaml_file("thermostats.yaml", {})
        for thermostat, data in thermostats.items():
            data["id"] = thermostat
            self.yaml_config["thermostats"][thermostat] = ThermostatObject(data)

    def _load_dht(self) -> None:
        """
        Load DHT sensor configuration from the YAML file.
        """
        dht_data: dict[str, Any] = self._load_yaml_file("dht.yaml", {})
        if dht_data != {}:
            self.yaml_config["dht"] = DHTObject(dht_data)

    def _load_klok(self) -> None:
        """
        Load klok configuration from the YAML file.
        """
        klok_data: dict[str, Any] = self._load_yaml_file("klok.yaml", {})
        if klok_data != {}:
            self.yaml_config["klok"] = KlokObject(klok_data)

    def _load_fan(self) -> None:
        """
        Load fan configuration from the YAML file.
        """
        fan_data: dict[str, Any] = self._load_yaml_file("fan.yaml", {})
        if fan_data != {}:
            self.yaml_config["fan"] = FanObject(fan_data)

    def _load_powerbutton(self) -> None:
        """
        Load power button configuration from the YAML file.
        """
        powerbutton_data: dict[str, Any] = self._load_yaml_file("powerbutton.yaml", {})
        if powerbutton_data != {}:
            self.yaml_config["powerbutton"] = PowerButtonObject(powerbutton_data)

    def _setup_dht_callbacks(self) -> None:
        """
        Set up DHT sensor callbacks to update thermostats when temperature/humidity changes.
        This method should be called after both DHT and thermostat objects are loaded.
        """
        dht_obj = self.yaml_config.get("dht")
        dht_obj: Optional[DHTObject] = dht_obj if isinstance(dht_obj, DHTObject) else None
        if dht_obj is None:
            logger.debug("No DHT object found, skipping callback setup")
            return
        
        def handle_temperature_update(temperature: float) -> None:
            """Handle temperature updates from DHT sensor"""
            for thermostat in self.yaml_config["thermostats"].values():
                try:
                    thermostat: ThermostatObject = thermostat
                    thermostat.update_dht_related_status(temperature=temperature)
                except Exception as e:
                    logger.error(f"Error updating thermostat with temperature {temperature}: {e}")
        
        def handle_humidity_update(humidity: float) -> None:
            """Handle humidity updates from DHT sensor"""
            for thermostat in self.yaml_config["thermostats"].values():
                try:
                    thermostat: ThermostatObject = thermostat
                    thermostat.update_dht_related_status(humidity=humidity)
                except Exception as e:
                    logger.error(f"Error updating thermostat with humidity {humidity}: {e}")
        
        # Register the callbacks
        dht_obj.register_temperature_callback(handle_temperature_update)
        dht_obj.register_humidity_callback(handle_humidity_update)

    def load_config(self) -> None:
        """
        Load the entire configuration from YAML files.
        """
        self.yaml_config: dict[str, Any] = {"config": {}, "thermostats": {}, "dht": {}, "klok": {}, "fan": {}, "powerbutton": {}}
        try:
            config: dict[str, Any] = self._load_yaml_file("config.yaml", {})
            config: dict[str, Any] = self._set_default_config_values(config)
            config = self._upgrade_config(config)
            self.yaml_config["config"] = config

            self._load_thermostats()
            self._load_dht()
            self._load_klok()
            self._load_fan()
            self._load_powerbutton()
            
            # Set up DHT callbacks after all objects are loaded
            self._setup_dht_callbacks()

            logger.info("Config loaded")
        except Exception:
            logger.exception("CRITICAL! Config file was not loaded")
            raise SystemExit("CRITICAL! Config file was not loaded")
        serverConfig = self.yaml_config

    def save_config(self, backup: bool = False, resource: str = "all") -> None:
        """
        Save the current configuration to YAML files.

        Args:
            backup (bool): Whether to save a backup of the configuration.
            resource (str): The specific resource to save or "all" to save everything.
        """
        path: str = self.configDir + '/'
        if backup:
            path: str = self.configDir + '/backup/'
            if not os.path.exists(path):
                os.makedirs(path)
        if resource in ["all", "config"]:
            config: dict[str, Any] = self.yaml_config["config"]
            _write_yaml(path + "config.yaml", config)
            logger.debug("Dump config file " + path + "config.yaml")
            if resource == "config":
                return
        saveResources: list[str] = []
        if resource == "all":
            saveResources = ["thermostats", "dht", "klok", "fan", "powerbutton"]
        else:
            saveResources.append(resource)
        for object in saveResources:
            filePath: str = path + object + ".yaml"
            dumpDict: dict[str, Any] = {}

            # Handle single service objects (not dictionaries)
            if object in ["dht", "klok", "fan", "powerbutton"]:
                if object in self.yaml_config and hasattr(self.yaml_config[object], 'save'):
                    savedData: dict[str, Any] = self.yaml_config[object].save()
                    if savedData:
                        dumpDict.update(savedData)
                # If the object doesn't exist in config (was deleted), remove the YAML file
                elif object not in self.yaml_config and os.path.exists(filePath):
                    try:
                        os.remove(filePath)
                        logger.debug(f"Removed config file {filePath}")
                        continue  # Skip writing the file since we removed it
                    except OSError as e:
                        logger.error(f"Failed to remove config file {filePath}: {e}")
            elif object in ["thermostats"]:
                # Handle other objects that are dictionaries (like thermostats)
                for element in self.yaml_config[object]:
                    if element != "0":
                        savedData: dict[str, Any] = self.yaml_config[object][element].save()
                        if savedData:
                            dumpDict[self.yaml_config[object][element].id] = savedData
            
            _write_yaml(filePath, dumpDict)
            logger.debug("Dump config file " + filePath)

    def reset_config(self) -> None:
        """
        Reset the configuration to default values.
        """
        self.save_config(backup=True)
        try:
            subprocess.run(f'rm -r {self.configDir}/*.yaml', check=True)
        except subprocess.CalledProcessError:
            logger.exception("Something went wrong when deleting the config")
        self.load_config()

    def restore_backup(self) -> None:
        """
        Restore the configuration from a backup.
        """
        try:
            subprocess.run(f'rm -r {self.configDir}/*.yaml', check=True)
        except subprocess.CalledProcessError:
            logger.exception("Something went wrong when deleting the config")
        subprocess.run(f'cp -r {self.configDir}/backup/*.yaml {self.configDir}/', shell=True, check=True)
        self.load_config()

    def download_config(self) -> str:
        """
        Download the current configuration as a tar file.

        Returns:
            str: The path to the tar file containing the configuration.
        """
        self.save_config()
        subprocess.run(f'tar --exclude=\'config_debug.yaml\' -cvf {self.configDir}/config.tar ' + self.configDir + '/*.yaml', shell=True, capture_output=True, text=True)
        return f"{self.configDir}/config.tar"

    def download_log(self) -> str:
        """
        Download the log files as a tar file.

        Returns:
            str: The path to the tar file containing the log files.
        """
        subprocess.run(f'tar -cvf {self.configDir}/server_log.tar {self.runningDir}/*.log*', shell=True, check=True)
        return f"{self.configDir}/server_log.tar"

    def download_debug(self) -> str:
        """
        Download the debug information as a tar file.

        Returns:
            str: The path to the tar file containing the debug information.
        """
        debug: dict[str, Any] = deepcopy(self.yaml_config["config"])
        info: dict[str, Any] = {}
        info["OS"] = os.uname().sysname
        info["Architecture"] = os.uname().machine
        info["os_version"] = os.uname().version
        info["os_release"] = os.uname().release
        info["Server Version"] = subprocess.run("stat -c %y api.py", shell=True, capture_output=True, text=True).stdout.replace("\n", "")
        info["WebUI Version"] = subprocess.run("stat -c %y flaskUI/templates/index.html", shell=True, capture_output=True, text=True).stdout.replace("\n", "")
        info["arguments"] = {k: str(v) for k, v in self.argsDict.items()}
        _write_yaml(f"{self.configDir}/config_debug.yaml", debug)
        _write_yaml(f"{self.configDir}/system_info.yaml", info)
        subprocess.run(f'tar --exclude=\'config.yaml\' -cvf {self.configDir}/config_debug.tar {self.configDir}/*.yaml {self.runningDir}/*.log* ', shell=True, capture_output=True, text=True)
        subprocess.run(f'rm -r {self.configDir}/config_debug.yaml', check=True)
        return f"{self.configDir}/config_debug.tar"

    def restart_python(self) -> None:
        """
        Restart the Python process.

        Args:
            None

        Returns:
            None
        """
        logger.info(f"restart {sys.executable} with args: {sys.argv}")
        try:
            subprocess.run(['systemctl', '--user', 'restart', 'raspberry_extension_server.service'], check=True)
        except Exception as e:
            logger.error(f"systemctl restart failed: {e}, falling back to os.execl")
            os.execl(sys.executable, sys.executable, *sys.argv)
