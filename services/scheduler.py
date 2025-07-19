from datetime import datetime
from time import sleep
from typing import Any

import configManager
import logging
import logManager
from services import updateManager

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config
logger: logging.Logger = logManager.logger.get_logger(__name__)

def runScheduler() -> None:
    """
    Run the scheduler to process schedules, behavior instances, and smart scenes.
    """
    while True:

        if "updatetime" not in serverConfig["config"]["swupdate2"]["autoinstall"]:
            serverConfig["config"]["swupdate2"]["autoinstall"]["updatetime"] = "T14:00:00"
        if datetime.now().strftime("T%H:%M:%S") == serverConfig["config"]["swupdate2"]["autoinstall"]["updatetime"]:
            updateManager.githubCheck()
            if serverConfig["config"]["swupdate2"]["autoinstall"]["on"]:
                updateManager.githubInstall()
        if datetime.now().strftime("%M:%S") == "00:10":
            configManager.serverConfig.save_config()
            if datetime.now().strftime("%H") == "23" and datetime.now().strftime("%A") == "Sunday":
                configManager.serverConfig.save_config(backup=True)
        sleep(1)
