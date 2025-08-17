from fastapi import FastAPI
from nicegui import ui
from fastapi.middleware.cors import CORSMiddleware
import os
import configManager
from .route_helpers import FlaskLikeRoutes
from .server_routes import register_server_routes
from .system_routes import SystemRoute
from .dht_routes import DHTRoute
from .thermostat_routes import ThermostatRoute
from .klok_routes import KlokRoute
from .config_routes import ConfigRoute
from .fan_routes import FanRoute
from .powerbutton_routes import PowerButtonRoute

root_dir = configManager.serverConfig.runningDir
favicon_path = os.path.join(root_dir, 'flaskUI', 'templates', 'favicon.ico')

def create_app():
    """
    App factory function following diyHue pattern
    """
    app: FastAPI = FastAPI(title="Raspberry Extension Server API", version="1.0.0")

    # Enable CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_server_routes(app, favicon_path)

    routes = FlaskLikeRoutes(app)

    routes.add_route("/system", SystemRoute, methods=["GET"], has_resource=True)
    routes.add_route("/dht", DHTRoute, methods=["GET", "POST", "DELETE"], has_resource=True)
    routes.add_route("", ThermostatRoute, methods=["GET", "POST", "DELETE"], has_mac=True, has_resource=True, has_value=True)
    routes.add_route("/klok", KlokRoute, methods=["GET", "POST", "DELETE"], has_resource=True, has_value=True)
    routes.add_route("/config", ConfigRoute, methods=["GET", "PUT"], has_resource=True)
    routes.add_route("/fan", FanRoute, methods=["GET", "POST", "DELETE"], has_resource=True)
    routes.add_route("/powerbutton", PowerButtonRoute, methods=["GET", "POST", "DELETE"], has_resource=True)

    ui.run_with(
        app,
        mount_path='/',  # NOTE this can be omitted if you want the paths passed to @ui.page to be at the root
        storage_secret='pick your private secret here',  # NOTE setting a secret is optional but allows for persistent storage per user
        favicon=favicon_path
    )

    return app
