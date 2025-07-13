from flask import render_template, request, Blueprint, redirect, url_for, make_response, send_file, Response
from werkzeug.security import generate_password_hash, check_password_hash
from flaskUI.core.forms import LoginForm
import flask_login
import uuid
import json
import configManager
from flaskUI.core import User
from subprocess import check_output
from pprint import pprint
import os
import sys
import logManager
import subprocess
from typing import Dict, Any, Union

logging = logManager.logger.get_logger(__name__)
serverConfig = configManager.serverConfig.yaml_config
core = Blueprint('core', __name__)

def save_bridge_config(backup: bool = False) -> str:
    """
    Save the bridge configuration.

    Args:
        backup (bool): Whether to create a backup of the configuration.

    Returns:
        str: A message indicating whether the configuration was saved or backed up.
    """
    configManager.serverConfig.save_config(backup=backup)
    return "backup config\n" if backup else "config saved\n"

def restart_python() -> None:
    """
    Restart the Python process.

    Args:
        None

    Returns:
        None
    """
    logging.info(f"restart {sys.executable} with args: {sys.argv}")
    os.execl(sys.executable, sys.executable, *sys.argv)

@core.route('/')
@flask_login.login_required
def index() -> str:
    """
    Render the index page.

    Args:
        None

    Returns:
        str: The rendered index page.
    """
    return render_template('index.html', groups=serverConfig["groups"], lights=serverConfig["lights"])

@core.route('/save')
def save_config() -> str:
    """
    Save the bridge configuration.

    Args:
        None

    Returns:
        str: A message indicating whether the configuration was saved or backed up.
    """
    return save_bridge_config(backup=request.args.get('backup', type=str) == "True")

@core.route('/reset_config')
@flask_login.login_required
def reset_config() -> str:
    """
    Reset the bridge configuration.

    Args:
        None

    Returns:
        str: A message indicating that the configuration was reset.
    """
    configManager.serverConfig.reset_config()
    return "config reset\n"

@core.route('/restore_config')
@flask_login.login_required
def restore_config() -> str:
    """
    Restore the bridge configuration from a backup.

    Args:
        None

    Returns:
        str: A message indicating that the configuration was restored.
    """
    configManager.serverConfig.restore_backup()
    return "restore config\n"

@core.route('/download_config')
@flask_login.login_required
def download_config() -> Response:
    """
    Download the bridge configuration.

    Args:
        None

    Returns:
        Response: The bridge configuration file.
    """
    path = configManager.serverConfig.download_config()
    return send_file(path, as_attachment=True)

@core.route('/download_log')
def download_log() -> Response:
    """
    Download the log file.

    Args:
        None

    Returns:
        Response: The log file.
    """
    path = configManager.serverConfig.download_log()
    return send_file(path, as_attachment=True)

@core.route('/download_debug')
def download_debug() -> Response:
    """
    Download the debug file.

    Args:
        None

    Returns:
        Response: The debug file.
    """
    path = configManager.serverConfig.download_debug()
    return send_file(path, as_attachment=True)

@core.route('/restart')
def restart() -> str:
    """
    Restart the Python process.

    Args:
        None

    Returns:
        str: A message indicating that the process was restarted.
    """
    restart_python()
    return "restart python with args"

@core.route('/info')
def info() -> Dict[str, str]:
    """
    Get system information.

    Args:
        None

    Returns:
        Dict[str, str]: The system information.
    """
    uname = os.uname()
    return {
        "sysname": uname.sysname,
        "machine": uname.machine,
        "os_version": uname.version,
        "os_release": uname.release,
        "diyhue": subprocess.run("stat -c %y HueEmulator3.py", shell=True, capture_output=True, text=True).stdout.strip(),
        "webui": subprocess.run("stat -c %y flaskUI/templates/index.html", shell=True, capture_output=True, text=True).stdout.strip()
    }

@core.route('/login', methods=['GET', 'POST'])
def login() -> Union[str, Response]:
    """
    Handle user login.

    Args:
        None

    Returns:
        Union[str, Response]: The login page or a redirect to the index page.
    """
    form = LoginForm()
    if request.method == 'GET':
        return render_template('login.html', form=form)
    email = form.email.data
    if email not in serverConfig["config"]["users"]:
        return 'User don\'t exist\n'
    if check_password_hash(serverConfig["config"]["users"][email]['password'], form.password.data):
        user = User()
        user.id = email
        flask_login.login_user(user)
        return redirect(url_for('core.index'))

    logging.info(f"Hashed pass: {generate_password_hash(form.password.data)}")
    return 'Bad login\n'

@core.route('/description.xml')
def description_xml() -> Response:
    """
    Serve the description XML file.

    Args:
        None

    Returns:
        Response: The description XML file.
    """
    HOST_HTTP_PORT = configManager.runtimeConfig.arg["HTTP_PORT"]
    mac = configManager.runtimeConfig.arg["MAC"]
    resp = make_response(render_template('description.xml', mimetype='text/xml', port=HOST_HTTP_PORT, name=serverConfig["config"]["name"], ipaddress=serverConfig["config"]["ipaddress"], serial=mac))
    resp.headers['Content-type'] = 'text/xml'
    return resp

@core.route('/logout')
@flask_login.login_required
def logout() -> Response:
    """
    Handle user logout.

    Args:
        None

    Returns:
        Response: A redirect to the login page.
    """
    flask_login.logout_user()
    return redirect(url_for('core.login'))
