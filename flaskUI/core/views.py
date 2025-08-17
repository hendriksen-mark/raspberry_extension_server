from flask import render_template, request, Blueprint, redirect, url_for, send_file, Response
from werkzeug.security import generate_password_hash, check_password_hash
from flaskUI.core.forms import LoginForm
import flask_login
import configManager
from flaskUI.core import User
import os
import logging
import logManager
import subprocess
from typing import Any, Union

logger: logging.Logger = logManager.logger.get_logger(__name__)
serverConfig: dict[str, str | int | float | dict] = configManager.serverConfig.yaml_config
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


@core.route('/login', methods=['GET', 'POST'])
def login() -> Union[str, Response]:
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
    email: str = form.email.data
    if email not in serverConfig["config"]["users"]:
        return 'User don\'t exist\n'
    if check_password_hash(serverConfig["config"]["users"][email]['password'], form.password.data):
        user: User = User()
        user.id = email
        flask_login.login_user(user)
        return redirect(url_for('core.index'))

    logger.info(f"Hashed pass: {generate_password_hash(form.password.data)}")
    return 'Bad login\n'

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
