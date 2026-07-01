"""Core Flask blueprint views: info, login, logout."""
import os
from datetime import datetime, timezone
import logging
from typing import Any
from flask import render_template, request, Blueprint, redirect, url_for, send_file
import flask_login
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.wrappers.response import Response as WerkzeugResponse

import logManager

from flask_ui.core.forms import LoginForm
from flask_ui.core import User
import config_manager

logger: logging.Logger = logManager.logger.get_logger(__name__)
SERVER_CONFIG: dict[str, Any] = config_manager.SERVER_CONFIG.yaml_config
core = Blueprint('core', __name__)

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
    return render_template('index.html')

@core.route('/save')
def save_config() -> str:
    """
    Save the server configuration.

    Args:
        None

    Returns:
        str: A message indicating whether the configuration was saved or backed up.
    """
    backup = request.args.get('backup', type=str) == "True"
    config_manager.SERVER_CONFIG.save_config(backup=backup)
    return "backup config\n" if backup else "config saved\n"

@core.route('/reset_config')
@flask_login.login_required
def reset_config() -> str:
    """
    Reset the server configuration.

    Args:
        None

    Returns:
        str: A message indicating that the configuration was reset.
    """
    config_manager.SERVER_CONFIG.reset_config()
    return "config reset\n"

@core.route('/restore_config')
@flask_login.login_required
def restore_config() -> str:
    """
    Restore the server configuration from a backup.

    Args:
        None

    Returns:
        str: A message indicating that the configuration was restored.
    """
    config_manager.SERVER_CONFIG.restore_backup()
    return "restore config\n"

@core.route('/download_config')
@flask_login.login_required
def download_config() -> WerkzeugResponse:
    """
    Download the server configuration.

    Args:
        None

    Returns:
        Response: The server configuration file.
    """
    path: str = config_manager.SERVER_CONFIG.download_config()
    return send_file(path, as_attachment=True)

@core.route('/download_log')
def download_log() -> WerkzeugResponse:
    """
    Download the log file.

    Args:
        None

    Returns:
        Response: The log file.
    """
    path: str = config_manager.SERVER_CONFIG.download_log()
    return send_file(path, as_attachment=True)

@core.route('/download_debug')
def download_debug() -> WerkzeugResponse:
    """
    Download the debug file.

    Args:
        None

    Returns:
        Response: The debug file.
    """
    path: str = config_manager.SERVER_CONFIG.download_debug()
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
    config_manager.SERVER_CONFIG.restart_python()
    return "restart python with args"

@core.route('/info')
def info() -> dict[str, str]:
    """
    Get system information.

    Args:
        None

    Returns:
        dict[str, str]: The system information.
    """
    uname: os.uname_result = os.uname()
    return {
        "sysname": uname.sysname,
        "machine": uname.machine,
        "os_version": uname.version,
        "os_release": uname.release,
        "server": datetime.fromtimestamp(os.stat("api.py").st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "webui": datetime.fromtimestamp(os.stat("flaskUI/templates/index.html").st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    }

@core.route('/login', methods=['GET', 'POST'])
def login() -> str | WerkzeugResponse:
    """
    Handle user login.

    Args:
        None

    Returns:
        Union[str, Response]: The login page or a redirect to the index page.
    """
    form: LoginForm = LoginForm()
    if request.method == 'GET':
        return render_template('login.html', form=form)
    email: str | None = form.email.data
    password: str | None = form.password.data
    if email is None or password is None:
        return 'Bad login\n'
    if email not in SERVER_CONFIG["config"]["users"]:
        return 'User don\'t exist\n'
    if check_password_hash(SERVER_CONFIG["config"]["users"][email]['password'], password):
        user: User = User()
        setattr(user, "id", email)
        flask_login.login_user(user)
        return redirect(url_for('core.index'))

    logger.info(f"Hashed pass: {generate_password_hash(password)}")
    return 'Bad login\n'

@core.route('/logout')
@flask_login.login_required
def logout() -> WerkzeugResponse:
    """
    Handle user logout.

    Args:
        None

    Returns:
        Response: A redirect to the login page.
    """
    flask_login.logout_user()
    return redirect(url_for('core.login'))
