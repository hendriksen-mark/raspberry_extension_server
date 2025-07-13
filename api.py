#!/usr/bin/env python3
"""
Main entry point for the Eqiva Smart Radiator Thermostat API
"""

from flask import Flask
from flask_cors import CORS
from flask_restful import Api
from werkzeug.security import check_password_hash
from threading import Thread
import os
import configManager
import logManager
import flask_login
from flaskUI.core import User  # dummy import for flask_login module
from werkzeug.serving import WSGIRequestHandler
from api.routes.dht_routes import DHTRoute
from api.routes.homekit_routes import ThermostatRoute
from api import create_app, setup_signal_handlers, initialize_services, Config

serverConfig = configManager.serverConfig.yaml_config
logging = logManager.logger.get_logger(__name__)
werkzeug_logger = logManager.logger.get_logger("werkzeug")
cherrypy_logger = logManager.logger.get_logger("cherrypy")
WSGIRequestHandler.protocol_version = "HTTP/1.1"

app = Flask(__name__, template_folder='flaskUI/templates', static_url_path="/assets", static_folder='flaskUI/assets')
api = Api(app)
cors = CORS(app, resources={r"*": {"origins": "*"}})

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', os.urandom(24))  # Load from environment variable or generate a random key
api.app.config['RESTFUL_JSON'] = {'ensure_ascii': False}

login_manager = flask_login.LoginManager()
login_manager.init_app(app)
login_manager.login_view = "core.login"

@login_manager.user_loader
def user_loader(email):
    if email not in serverConfig["config"]["users"]:
        return None
    user = User()
    user.id = email
    return user

@login_manager.request_loader
def request_loader(request):
    email = request.form.get('email')
    if email not in serverConfig["config"]["users"]:
        return None
    user = User()
    user.id = email
    logging.info(f"Authentication attempt for user: {email}")
    user.is_authenticated = compare_passwords(request.form['password'], serverConfig["config"]["users"][email]["password"])
    return user

def compare_passwords(input_password, stored_password):
    return check_password_hash(stored_password, input_password)

api.add_resource(DHTRoute, '/<string:resource>', strict_slashes=False)
api.add_resource(DHTRoute, '/dht/<string:resource>', strict_slashes=False)
api.add_resource(ThermostatRoute, '/<string:mac>/<string:resource>', strict_slashes=False)


### WEB INTERFACE
from flaskUI.core.views import core
from flaskUI.error_pages.handlers import error_pages

app.register_blueprint(core)
app.register_blueprint(error_pages)

def runHttp(BIND_IP, HOST_HTTP_PORT):
    app.run(host=BIND_IP, port=HOST_HTTP_PORT)

def main():
    from services import ssdp, mdns, scheduler, stateFetch, updateManager, LogWS
    BIND_IP = configManager.runtimeConfig.arg["BIND_IP"]
    HOST_IP = configManager.runtimeConfig.arg["HOST_IP"]
    mac = configManager.runtimeConfig.arg["MAC"]
    HOST_HTTP_PORT = configManager.runtimeConfig.arg["HTTP_PORT"]
    updateManager.startupCheck()

    Thread(target=stateFetch.syncWithThermostats).start()
    Thread(target=stateFetch.read_dht_temperature).start()
    Thread(target=ssdp.ssdpSearch, args=[HOST_IP, HOST_HTTP_PORT, mac]).start()
    Thread(target=ssdp.ssdpBroadcast, args=[HOST_IP, HOST_HTTP_PORT, mac]).start()
    Thread(target=mdns.mdnsListener, args=[HOST_IP, HOST_HTTP_PORT, "BSB002", mac]).start()
    Thread(target=scheduler.runScheduler).start()
    Thread(target=LogWS.start_ws_server).start()
    runHttp(BIND_IP, HOST_HTTP_PORT)

if __name__ == '__main__':
    main()
    # Initialize services and setup signal handlers
    initialize_services()
    setup_signal_handlers()
    
    # Create and run the Flask application
    app = create_app()
    app.run(host='0.0.0.0', port=Config.HOST_HTTP_PORT)
