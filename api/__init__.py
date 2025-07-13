"""
API module with Flask app factory and resource registration
Following diyHue architectural patterns
"""

from flask import Flask
from flask_cors import CORS
from flask_restful import Api
import os
import configManager
import logManager
import flask_login
from flaskUI.core import User  # dummy import for flask_login module

logging = logManager.logger.get_logger(__name__)


def create_app():
    """
    App factory function following diyHue pattern
    """
    app = Flask(__name__, 
                template_folder='flaskUI/templates', 
                static_url_path="/assets", 
                static_folder='flaskUI/assets')
    
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))
    app.config['RESTFUL_JSON'] = {'ensure_ascii': False}
    
    # CORS setup
    cors = CORS(app, resources={r"*": {"origins": "*"}})
    
    # Flask-Login setup
    login_manager = flask_login.LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "core.login"
    
    serverConfig = configManager.serverConfig.yaml_config
    
    @login_manager.user_loader
    def user_loader(email):
        if email not in serverConfig["config"]["users"]:
            return None
        user = User()
        user.id = email
        return user

    @login_manager.request_loader
    def request_loader(request):
        from werkzeug.security import check_password_hash
        
        email = request.form.get('email')
        if email not in serverConfig["config"]["users"]:
            return None
        user = User()
        user.id = email
        logging.info(f"Authentication attempt for user: {email}")
        user.is_authenticated = check_password_hash(
            request.form['password'], 
            serverConfig["config"]["users"][email]["password"]
        )
        return user
    
    # Flask-RESTful API setup
    api = Api(app)
    
    # Add favicon route to prevent 404 errors
    @app.route('/favicon.ico')
    def favicon():
        return '', 204  # No Content
    
    # Register other routes
    from api.routes.system_routes import SystemRoute
    from api.routes.dht_routes import DHTRoute
    from api.routes.homekit_routes import ThermostatRoute
    api.add_resource(SystemRoute, '/<string:resource>', strict_slashes=False)
    api.add_resource(DHTRoute, '/dht/<string:resource>', strict_slashes=False)
    api.add_resource(ThermostatRoute, '/<string:mac>/<string:resource>', strict_slashes=False)
    
    # Register web interface blueprints
    from flaskUI.core.views import core
    from flaskUI.error_pages.handlers import error_pages
    app.register_blueprint(core)
    app.register_blueprint(error_pages)
    
    return app
