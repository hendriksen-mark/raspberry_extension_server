"""
API module with Flask app factory and resource registration
Following diyHue architectural patterns
"""

from flask import Flask, Request
from flask_cors import CORS
from flask_restful import Api
import os
import logging
import logManager
import flask_login
from flaskUI.core import User  # dummy import for flask_login module
import configManager

logger: logging.Logger = logManager.logger.get_logger(__name__)


def create_app(serverConfig) -> Flask:
    """
    App factory function following diyHue pattern
    """
    root_dir: str = configManager.serverConfig.runningDir

    template_dir: str = os.path.join(root_dir, 'flaskUI', 'templates')
    static_dir: str = os.path.join(root_dir, 'flaskUI', 'assets')

    if not os.path.exists(template_dir):
        logger.error(f"Template directory {template_dir} does not exist.")
        raise FileNotFoundError(f"Template directory {template_dir} does not exist.")
    if not os.path.exists(static_dir):
        logger.error(f"Static directory {static_dir} does not exist.")
        raise FileNotFoundError(f"Static directory {static_dir} does not exist.")
    if "index.html" not in os.listdir(template_dir):
        logger.error(f"index.html not found in {template_dir}.")
        raise FileNotFoundError(f"index.html not found in {template_dir}.")

    app: Flask = Flask(__name__,
                       template_folder=template_dir,
                       static_url_path="/assets",
                       static_folder=static_dir)

    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
    app.config['RESTFUL_JSON'] = {'ensure_ascii': False}

    # CORS setup
    cors: CORS = CORS(app, resources={r"*": {"origins": "*"}})

    # Flask-Login setup
    login_manager: flask_login.LoginManager = flask_login.LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "core.login"

    @login_manager.user_loader
    def user_loader(email: str) -> User | None:
        if email not in serverConfig["config"]["users"]:
            return None
        user: User = User()
        user.id = email
        return user

    @login_manager.request_loader
    def request_loader(request: Request) -> User | None:
        from werkzeug.security import check_password_hash

        email: str = request.form.get('email')
        if email not in serverConfig["config"]["users"]:
            return None
        user: User = User()
        user.id = email
        logger.info(f"Authentication attempt for user: {email}")
        user.is_authenticated = check_password_hash(
            request.form['password'],
            serverConfig["config"]["users"][email]["password"]
        )
        return user

    # Flask-RESTful API setup
    api: Api = Api(app)

    # Register other routes
    from .system_routes import SystemRoute
    from .dht_routes import DHTRoute
    from .thermostat_routes import ThermostatRoute
    from .klok_routes import KlokRoute
    from .config_routes import ConfigRoute
    from .fan_routes import FanRoute
    from .powerbutton_routes import PowerButtonRoute

    # Register routes with both optional and required resource patterns
    api.add_resource(SystemRoute,       '/system/',
                                        '/system/<string:resource>',                        strict_slashes=False)
    api.add_resource(DHTRoute,          '/dht/',
                                        '/dht/<string:resource>',                           strict_slashes=False)
    api.add_resource(ThermostatRoute,   '/<string:mac>/',
                                        '/<string:mac>/<string:resource>',
                                        '/<string:mac>/<string:resource>/<string:value>',   strict_slashes=False)
    api.add_resource(KlokRoute,         '/klok/',
                                        '/klok/<string:resource>',
                                        '/klok/<string:resource>/<string:value>',           strict_slashes=False)
    api.add_resource(ConfigRoute,       '/config/',
                                        '/config/<string:resource>',                        strict_slashes=False)
    api.add_resource(FanRoute,          '/fan/',
                                        '/fan/<string:resource>',                           strict_slashes=False)
    api.add_resource(PowerButtonRoute,  '/powerbutton/',
                                        '/powerbutton/<string:resource>',                   strict_slashes=False)

    # Register web interface blueprints
    from flaskUI.core.views import core
    from flaskUI.error_pages.handlers import error_pages
    app.register_blueprint(core)
    app.register_blueprint(error_pages)

    return app
