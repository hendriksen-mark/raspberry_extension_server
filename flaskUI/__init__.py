"""
API module with Flask app factory and resource registration
Following diyHue architectural patterns
"""

from flask import Flask, Request
from flask_cors import CORS
from flask_restful import Api
import os
import logManager
import flask_login
from flaskUI.core import User  # dummy import for flask_login module

logging = logManager.logger.get_logger(__name__)


def create_app(serverConfig) -> Flask:
    """
    App factory function following diyHue pattern
    """
    root_dir: str = serverConfig["config"]["runningDir"]

    template_dir: str = os.path.join(root_dir, 'flaskUI', 'templates')
    static_dir: str = os.path.join(root_dir, 'flaskUI', 'assets')

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
        logging.info(f"Authentication attempt for user: {email}")
        user.is_authenticated = check_password_hash(
            request.form['password'], 
            serverConfig["config"]["users"][email]["password"]
        )
        return user
    
    # Flask-RESTful API setup
    api: Api = Api(app)

    # Register other routes
    from .system_routes import SystemRoute
    #from .dht_routes import DHTRoute
    from .homekit_routes import ThermostatRoute
    from .klok_routes import KlokRoute
    api.add_resource(SystemRoute, '/<string:resource>', strict_slashes=False)
    #api.add_resource(DHTRoute, '/dht', strict_slashes=False)
    api.add_resource(ThermostatRoute, '/<string:mac>/<string:resource>', strict_slashes=False)
    api.add_resource(KlokRoute, 
                    '/klok/<string:request_type>', 
                    '/klok/<string:request_type>/<string:value>', 
                    strict_slashes=False)
    #api.add_resource(ConfigRoute, '/config/<string:resource>', strict_slashes=False)  # legacy route

    # Register web interface blueprints
    from flaskUI.core.views import core
    from flaskUI.error_pages.handlers import error_pages
    app.register_blueprint(core)
    app.register_blueprint(error_pages)
    
    return app
