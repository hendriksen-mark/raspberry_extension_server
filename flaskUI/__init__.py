from nicegui import app

def create_app():
    """
    App factory function following diyHue pattern
    """
    #app: FastAPI = FastAPI(title="Raspberry Extension Server API", version="1.0.0")

    # Enable CORS
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register other routes using Flask-like helper - even cleaner!
    from .route_helpers import FlaskLikeRoutes
    from .server_routes import register_server_routes
    from .system_routes import SystemRoute
    from .dht_routes import DHTRoute
    from .thermostat_routes import ThermostatRoute
    from .klok_routes import KlokRoute
    from .config_routes import ConfigRoute
    from .fan_routes import FanRoute
    from .powerbutton_routes import PowerButtonRoute

    register_server_routes(app)

    # Create Flask-like router
    routes = FlaskLikeRoutes(app)
    
    # Register routes - this is as clean as Flask now!
    routes.add_route("/system", SystemRoute, methods=["GET"], has_resource=True)
    routes.add_route("/dht", DHTRoute, methods=["GET", "POST", "DELETE"], has_resource=True)
    routes.add_route("", ThermostatRoute, methods=["GET", "POST", "DELETE"], has_mac=True, has_resource=True, has_value=True)
    routes.add_route("/klok", KlokRoute, methods=["GET", "POST", "DELETE"], has_resource=True, has_value=True)
    routes.add_route("/config", ConfigRoute, methods=["GET", "PUT"], has_resource=True)
    routes.add_route("/fan", FanRoute, methods=["GET", "POST", "DELETE"], has_resource=True)
    routes.add_route("/powerbutton", PowerButtonRoute, methods=["GET", "POST", "DELETE"], has_resource=True)

    return app
