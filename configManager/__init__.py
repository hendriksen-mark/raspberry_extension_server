from . import configHandler
from . import argumentHandler
from . import runtimeConfigHandler

serverConfig = configHandler.Config()
runtimeConfig = runtimeConfigHandler.Config()

# Initialize runtime configuration
runtimeConfig.populate()
argumentHandler.process_arguments(runtimeConfig.arg)

# Restore configuration
serverConfig.load_config()

# Initialize bridge config
#serverConfig.generate_security_key()
#serverConfig.write_args(runtimeConfig.arg)
