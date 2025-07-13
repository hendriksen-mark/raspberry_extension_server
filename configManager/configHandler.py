from .argumentHandler import parse_arguments
import os
import subprocess
import logManager
import yaml
from copy import deepcopy
from typing import Any, Dict, Optional
from api.services.thermostat_service import ThermostatService
from api.services.dht_service import DHTService

try:
    from time import tzset
except ImportError:
    tzset = None

logging = logManager.logger.get_logger(__name__)

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
    yaml_config: Optional[Dict[str, Any]] = None
    argsDict: Dict[str, Any] = parse_arguments()
    configDir: str = argsDict["CONFIG_PATH"]
    runningDir: str = argsDict["RUNNING_PATH"]

    def __init__(self) -> None:
        """
        Initialize the Config class.
        """
        if not os.path.exists(self.configDir):
            os.makedirs(self.configDir)

    def _set_default_config_values(self, config: Dict[str, Any]) -> None:
        """
        Set default configuration values.

        Args:
            config (Dict[str, Any]): The configuration dictionary.
        """
        defaults = {
            "name":"DiyHue Bridge",
            "netmask":"255.255.255.0",
            "users":{"admin":{"password":"pbkdf2:sha256:150000$bqqXSOkI$199acdaf81c18f6ff2f29296872356f4eb78827784ce4b3f3b6262589c788742"}},
            "thermostats": {"enabled": False, "interval": 300},
            "dht": {"enabled": False, "interval": 5},
            "klok": {"enabled": False},
            "fan": {"enabled": False},
            "powerbutton": {"enabled": False},
            "swupdate2": {
                "autoinstall": {"on": False, "updatetime": "T14:00:00"},
                "bridge": {"lastinstall": "2020-12-11T17:08:55", "state": "noupdates"},
                "checkforupdate": False,
                "lastchange": "2020-12-13T10:30:15",
                "state": "noupdates",
                "install": False
            }
        }
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
        return config

    def _load_yaml_file(self, filename: str, default: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Load a YAML file and return its contents.

        Args:
            filename (str): The name of the YAML file.
            default (Optional[Dict[str, Any]]): The default value if the file does not exist.

        Returns:
            Optional[Dict[str, Any]]: The contents of the YAML file or the default value.
        """
        path = os.path.join(self.configDir, filename)
        if os.path.exists(path):
            return _open_yaml(path)
        return default

    def _load_thermostats(self) -> None:
        """
        Load thermostats from the YAML configuration.
        """
        thermostats = self._load_yaml_file("thermostats.yaml", {})
        for thermostat, data in thermostats.items():
            data["id"] = thermostat
            self.yaml_config["thermostats"][thermostat] = ThermostatService(data)

    def _load_dht(self) -> None:
        """
        Load DHT sensor configuration from the YAML file.
        """
        dht_data = self._load_yaml_file("dht.yaml", {})
        self.yaml_config["dht"] = DHTService(dht_data)

    def load_config(self) -> None:
        """
        Load the entire configuration from YAML files.
        """
        self.yaml_config = {"config": {}, "thermostats": {}, "dht": {}, "klok": {}, "fan": {}, "powerbutton": {}}
        try:
            config = self._load_yaml_file("config.yaml", {})
            config = self._set_default_config_values(config)
            self.yaml_config["config"] = config
            self.yaml_config["config"]["configDir"] = self.configDir
            self.yaml_config["config"]["runningDir"] = self.runningDir

            self._load_thermostats()
            self._load_dht()

            logging.info("Config loaded")
        except Exception:
            logging.exception("CRITICAL! Config file was not loaded")
            raise SystemExit("CRITICAL! Config file was not loaded")
        serverConfig = self.yaml_config

    def save_config(self, backup: bool = False, resource: str = "all") -> None:
        """
        Save the current configuration to YAML files.

        Args:
            backup (bool): Whether to save a backup of the configuration.
            resource (str): The specific resource to save or "all" to save everything.
        """
        path = self.configDir + '/'
        if backup:
            path = self.configDir + '/backup/'
            if not os.path.exists(path):
                os.makedirs(path)
        if resource in ["all", "config"]:
            config = self.yaml_config["config"]
            _write_yaml(path + "config.yaml", config)
            logging.debug("Dump config file " + path + "config.yaml")
            if resource == "config":
                return
        saveResources = []
        if resource == "all":
            saveResources = ["thermostats", "dht", "klok", "fan", "powerbutton"]
        else:
            saveResources.append(resource)
        for object in saveResources:
            filePath = path + object + ".yaml"
            dumpDict = {}
            for element in self.yaml_config[object]:
                if element != "0":
                    savedData = self.yaml_config[object][element].save()
                    if savedData:
                        dumpDict[self.yaml_config[object][element].id] = savedData
            _write_yaml(filePath, dumpDict)
            logging.debug("Dump config file " + filePath)

    def reset_config(self) -> None:
        """
        Reset the configuration to default values.
        """
        self.save_config(backup=True)
        try:
            subprocess.run(f'rm -r {self.configDir}/*.yaml', check=True)
        except subprocess.CalledProcessError:
            logging.exception("Something went wrong when deleting the config")
        self.load_config()

    def restore_backup(self) -> None:
        """
        Restore the configuration from a backup.
        """
        try:
            subprocess.run(f'rm -r {self.configDir}/*.yaml', check=True)
        except subprocess.CalledProcessError:
            logging.exception("Something went wrong when deleting the config")
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
        subprocess.run(f'tar -cvf {self.configDir}/diyhue_log.tar {self.runningDir}/*.log*', shell=True, check=True)
        return f"{self.configDir}/diyhue_log.tar"

    def download_debug(self) -> str:
        """
        Download the debug information as a tar file.

        Returns:
            str: The path to the tar file containing the debug information.
        """
        debug = deepcopy(self.yaml_config["config"])
        info = {}
        info["OS"] = os.uname().sysname
        info["Architecture"] = os.uname().machine
        info["os_version"] = os.uname().version
        info["os_release"] = os.uname().release
        info["Hue-Emulator Version"] = subprocess.run("stat -c %y api.py", shell=True, capture_output=True, text=True).stdout.replace("\n", "")
        info["WebUI Version"] = subprocess.run("stat -c %y flaskUI/templates/index.html", shell=True, capture_output=True, text=True).stdout.replace("\n", "")
        info["arguments"] = {k: str(v) for k, v in self.argsDict.items()}
        _write_yaml(f"{self.configDir}/config_debug.yaml", debug)
        _write_yaml(f"{self.configDir}/system_info.yaml", info)
        subprocess.run(f'tar --exclude=\'config.yaml\' -cvf {self.configDir}/config_debug.tar {self.configDir}/*.yaml {self.runningDir}/*.log* ', shell=True, capture_output=True, text=True)
        subprocess.run(f'rm -r {self.configDir}/config_debug.yaml', check=True)
        return f"{self.configDir}/config_debug.tar"
