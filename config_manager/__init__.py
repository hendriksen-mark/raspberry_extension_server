"""
This module initializes the configuration management system for the Raspberry Extension Server.
It imports the necessary configuration handlers and sets up the server and runtime configurations.
"""
from . import config_handler
#from . import argumentHandler
from . import runtime_config_handler

SERVER_CONFIG = config_handler.Config()
RUNTIME_CONFIG = runtime_config_handler.Config()

# Initialize runtime configuration
#RUNTIME_CONFIG.populate()
#argumentHandler.process_arguments(RUNTIME_CONFIG.arg)

# Restore configuration
SERVER_CONFIG.load_config()

# Initialize bridge config
#SERVER_CONFIG.generate_security_key()
#SERVER_CONFIG.write_args(RUNTIME_CONFIG.arg)
