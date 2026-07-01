from datetime import datetime
from time import sleep
from typing import Any
import logging

import logManager

import config_manager
from services import update_manager

SERVER_CONFIG: dict[str, Any] = config_manager.SERVER_CONFIG.yaml_config
logger: logging.Logger = logManager.logger.get_logger(__name__)

# Global variable to control scheduler state
_SCHEDULER_RUNNING: bool = False

def run_scheduler() -> None:
    """
    Run the scheduler to process schedules, behavior instances, and smart scenes.
    """
    global _SCHEDULER_RUNNING
    _SCHEDULER_RUNNING = True

    while _SCHEDULER_RUNNING:

        if "updatetime" not in SERVER_CONFIG["config"]["swupdate2"]["autoinstall"]:
            SERVER_CONFIG["config"]["swupdate2"]["autoinstall"]["updatetime"] = "T14:00:00"
        if datetime.now().strftime("T%H:%M:%S") == SERVER_CONFIG["config"]["swupdate2"]["autoinstall"]["updatetime"]:
            update_manager.github_check()
            if SERVER_CONFIG["config"]["swupdate2"]["autoinstall"]["on"]:
                update_manager.github_install()
        if datetime.now().strftime("%M:%S") == "00:10":
            config_manager.SERVER_CONFIG.save_config()
            if datetime.now().strftime("%H") == "23" and datetime.now().strftime("%A") == "Sunday":
                config_manager.SERVER_CONFIG.save_config(backup=True)
        sleep(1)

def stop_scheduler() -> None:
    """
    Stop the scheduler gracefully.
    """
    global _SCHEDULER_RUNNING
    logger.info("Stopping scheduler...")
    _SCHEDULER_RUNNING = False
