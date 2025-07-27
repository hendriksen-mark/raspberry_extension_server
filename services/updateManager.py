import requests
import subprocess
from datetime import datetime, timezone
from typing import Any, List

import configManager
import logging
import logManager
from .github_installer import install_github_updates

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config
logger: logging.Logger = logManager.logger.get_logger(__name__)

def githubCheck() -> None:
    """
    Check for updates on GitHub for both the main server repository and the UI repository.
    Update the server configuration based on the availability of updates.
    """
    creation_time: str = get_file_creation_time("api.py")
    publish_time: str = get_github_publish_time(f"https://api.github.com/repos/hendriksen-mark/raspberry_extension_server/branches/{serverConfig['config']['system']['branch']}")

    logger.debug(f"creation_time server : {creation_time}")
    logger.debug(f"publish_time  server : {publish_time}")

    if publish_time > creation_time:
        logger.info("update on github")
        serverConfig["config"]["swupdate2"]["state"] = "allreadytoinstall"
    elif githubUICheck():
        logger.info("UI update on github")
        serverConfig["config"]["swupdate2"]["state"] = "anyreadytoinstall"
    else:
        logger.info("no update for server or UI on github")
        serverConfig["config"]["swupdate2"]["state"] = "noupdates"

    serverConfig["config"]["swupdate2"]["checkforupdate"] = False

def githubUICheck() -> bool:
    """
    Check for updates on the GitHub UI repository.
    
    Returns:
        bool: True if there is a new update available, False otherwise.
    """
    creation_time: str = get_file_creation_time("flaskUI/templates/index.html")
    publish_time: str = get_github_publish_time("https://api.github.com/repos/hendriksen-mark/raspberry_extension_server_ui/releases/latest")

    logger.debug(f"creation_time UI : {creation_time}")
    logger.debug(f"publish_time  UI : {publish_time}")

    return publish_time > creation_time

def get_file_creation_time(filepath: str) -> str:
    """
    Get the creation time of a file.
    
    Args:
        filepath (str): The path to the file.
    
    Returns:
        str: The creation time of the file in the format "%Y-%m-%d %H".
    """
    try:
        creation_time = subprocess.run(f"stat -c %y {filepath}", shell=True, capture_output=True, text=True)
        creation_time_arg1: list[str] = creation_time.stdout.replace(".", " ").split(" ") if creation_time.stdout else "2999-01-01 01:01:01 000000000 +0100\n".split(" ")
        return parse_creation_time(creation_time_arg1)
    except subprocess.SubprocessError as e:
        logger.error(f"Error getting file creation time: {e}")
        return "2999-01-01 01:01:01"

def get_github_publish_time(url: str) -> str:
    """
    Get the publish time of the latest commit or release from a GitHub repository.
    
    Args:
        url (str): The API URL to fetch the publish time from.
    
    Returns:
        str: The publish time in the format "%Y-%m-%d %H".
    """
    try:
        response: requests.Response = requests.get(url)
        response.raise_for_status()
        device_data: dict[str, Any] = response.json()
        if "commit" in device_data:
            return datetime.strptime(device_data["commit"]["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H")
        elif "published_at" in device_data:
            return datetime.strptime(device_data["published_at"], "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d %H")
    except requests.RequestException as e:
        logger.error(f"No connection to GitHub: {e}")
        # Set state to unknown when there's no connection to update server
        serverConfig["config"]["swupdate2"]["state"] = "unknown"
        return "1970-01-01 00:00:00"

def parse_creation_time(creation_time_arg1: List[str]) -> str:
    """
    Parse the creation time from the output of the stat command.
    
    Args:
        creation_time_arg1 (List[str]): The list of strings representing the creation time.
    
    Returns:
        str: The parsed creation time in the format "%Y-%m-%d %H".
    """
    try:
        if len(creation_time_arg1) < 4:
            creation_time: str = f"{creation_time_arg1[0]} {creation_time_arg1[1]}".replace('\n', '')
            return datetime.strptime(creation_time, "%Y-%m-%d %H:%M:%S").astimezone(timezone.utc).strftime("%Y-%m-%d %H")
        else:
            creation_time: str = f"{creation_time_arg1[0]} {creation_time_arg1[1]} {creation_time_arg1[3]}".replace('\n', '')
            return datetime.strptime(creation_time, "%Y-%m-%d %H:%M:%S %z").astimezone(timezone.utc).strftime("%Y-%m-%d %H")
    except ValueError as e:
        logger.error(f"Error parsing creation time: {e}")
        return "2999-01-01 01:01:01"

def update_swupdate2_timestamps() -> None:
    """
    Update the timestamps for the last change and last install in the server configuration.
    """
    current_time: str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    serverConfig["config"]["swupdate2"]["lastchange"] = current_time

def githubInstall() -> None:
    """
    Install updates from GitHub if they are ready to be installed.
    """
    if serverConfig["config"]["swupdate2"]["state"] in ["allreadytoinstall", "anyreadytoinstall"]:
        configManager.serverConfig.save_config()
        state = serverConfig['config']['swupdate2']['state']
        branch = serverConfig['config']['system']['branch']
        try:
            success = install_github_updates(state, branch)
            if success:
                logger.info("Update installation successful, restarting server")
                serverConfig["config"]["swupdate2"]["state"] = "noupdates"
                serverConfig["config"]["swupdate2"]["install"] = False
                configManager.serverConfig.restart_python()
                # Code after restart_python() will not execute
            else:
                logger.error("Update installation failed")
                serverConfig["config"]["swupdate2"]["state"] = "unknown"
        except Exception as e:
            logger.error(f"Error during update installation: {e}")
            serverConfig["config"]["swupdate2"]["state"] = "unknown"

def startupCheck() -> None:
    """
    Perform a startup check for updates.
    """
    if serverConfig["config"]["swupdate2"]["install"]:
        serverConfig["config"]["swupdate2"]["install"] = False
        update_swupdate2_timestamps()
    githubCheck()
