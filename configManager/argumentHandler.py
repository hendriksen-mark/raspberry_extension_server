import argparse
import socket
import logging
import logManager
from os import getenv
from typing import Union, Optional
import pathlib

logger: logging.Logger = logManager.logger.get_logger(__name__)

def getIpAddress() -> Optional[str]:
    """
    Get the local IP address by connecting to an external server.

    Returns:
        Optional[str]: The local IP address or None if an error occurs.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except socket.error as e:
        logger.error(f"Socket error: {e}")
        return None

def get_environment_variable(var: str, boolean: bool = False) -> Union[str, bool, None]:
    """
    Retrieve the value of an environment variable.

    Args:
        var (str): The name of the environment variable.
        boolean (bool): If True, interpret the value as a boolean.

    Returns:
        str or bool or None: The value of the environment variable, or None if not found.
    """
    value: Optional[str] = getenv(var)
    if value is None:
        return None
    if boolean:
        return value.lower() == "true"
    return value

def process_arguments(args: dict[str, Union[str, bool]]) -> None:
    """
    Process the provided arguments and configure logging and certificate generation.

    Args:
        configDir (str): The directory where configuration files are stored.
        args (dict): A dictionary of arguments.
    """
    log_level = "DEBUG" if args["DEBUG"] else "INFO"
    logManager.logger.configure_logger(log_level)
    logger.info(f"Debug logging {'enabled' if args['DEBUG'] else 'disabled'}!")

def parse_arguments() -> dict[str, Union[str, int, bool]]:
    """
    Parse command-line arguments and environment variables to configure the application.

    Returns:
        dict: A dictionary containing the parsed arguments and their values.
    """
    argumentDict: dict[str, Union[str, int, bool]] = {
        "BIND_IP": '0.0.0.0', "HOST_IP": '', "HTTP_PORT": 5002,
        "FULLMAC": '', "MAC": '', "DEBUG": False, "BRANCH": '',
    }
    ap = argparse.ArgumentParser(description="Raspberry Extension Server Argument Handler")

    # Arguments can also be passed as Environment Variables.
    ap.add_argument("--debug", action='store_true', help="Enables debug output", default=False)
    ap.add_argument("--bind-ip", help="The IP address to listen on", type=str)
    ap.add_argument("--config_path", help="Set certificate and config files location", type=str)
    ap.add_argument("--ip", help="The IP address of the host system (Docker)", type=str)
    ap.add_argument("--http-port", help="The port to listen on for HTTP (Docker)", type=int)

    args: argparse.Namespace = ap.parse_args()

    argumentDict["DEBUG"] = args.debug or get_environment_variable('DEBUG', True)
    argumentDict["CONFIG_PATH"] = args.config_path or get_environment_variable('CONFIG_PATH') or '/opt/raspberry_extension_server/config'
    argumentDict["BIND_IP"] = args.bind_ip or get_environment_variable('BIND_IP') or '0.0.0.0'
    argumentDict["HOST_IP"] = args.ip or get_environment_variable('IP') or argumentDict["BIND_IP"] if argumentDict["BIND_IP"] != '0.0.0.0' else getIpAddress()
    argumentDict["HTTP_PORT"] = args.http_port or get_environment_variable('HTTP_PORT') or 5002
    argumentDict["RUNNING_PATH"] = str(pathlib.Path(__file__).parent.parent)

    return argumentDict
