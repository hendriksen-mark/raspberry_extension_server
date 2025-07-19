from flask import request
from typing import Any
from flask_restful import Resource
import logging
import logManager
import configManager
from services.updateManager import githubCheck, githubInstall
from werkzeug.security import generate_password_hash

logger: logging.Logger = logManager.logger.get_logger(__name__)

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config

class ConfigRoute(Resource):
    def get(self, resource: str) -> tuple[dict[str, Any], int]:
        """
        Handle GET requests for configuration resources
        URL: /config/resource
        """
        return serverConfig["config"], 200

    def put(self, resource: str) -> tuple[dict[str, Any], int]:
        """
        Update configuration for a specific resource
        """
        try:
            putDict: dict[str, Any] = request.get_json(force=True)
            if not putDict:
                return {"error": "No data provided"}, 400
                
            if resource == "config":
                changes_made: list[str] = []

                # Handle software updates
                if "swupdate2" in putDict:
                    swupdate: dict[str, Any] = putDict["swupdate2"]
                    if swupdate.get("checkforupdate"):
                        githubCheck()
                        changes_made.append("checked for updates")
                    if swupdate.get("install"):
                        githubInstall()
                        changes_made.append("installed updates")
                
                # Handle user password updates
                if "users" in putDict:
                    self._update_user_passwords(putDict["users"])
                    changes_made.append("updated user passwords")
                
                # Handle log level changes
                if "loglevel" in putDict:
                    logManager.logger.configure_logger(putDict["loglevel"])
                    logger.info(f"Changed log level to: {logManager.logger.get_level_name()}")
                    changes_made.append(f"changed log level to {putDict['loglevel']}")
                
                # Handle service configuration updates
                service_configs: list[str] = ["thermostats", "dht", "klok", "fan", "powerbutton"]
                for service in service_configs:
                    if service in putDict:
                        service_changes: list[str] = self._update_service_config(service, putDict[service])
                        if service_changes:
                            changes_made.extend([f"{service}: {change}" for change in service_changes])
                
                # Save configuration if changes were made
                if changes_made:
                    try:
                        configManager.serverConfig.save_config(backup=False, resource="config")
                        logger.info(f"Configuration updated - Changes: {', '.join(changes_made)}")
                        return {
                            "message": "Configuration updated successfully",
                            "changes": changes_made,
                            "config": serverConfig["config"]
                        }, 200
                    except Exception as e:
                        logger.error(f"Failed to save configuration: {e}")
                        return {"error": "Failed to save configuration"}, 500
                else:
                    return {"message": "No changes made", "config": serverConfig["config"]}, 200
            else:
                return {"error": "Resource not found"}, 404
                
        except Exception as e:
            logger.error(f"Error processing PUT request: {e}")
            return {"error": "Failed to process request"}, 500
    
    def _update_user_passwords(self, users_data: dict[str, Any]) -> None:
        """Update user passwords"""
        for key, value in users_data.items():
            for email, user_info in serverConfig["config"]["users"].items():
                if users_data[key] == user_info:
                    if "password" in value:
                        serverConfig["config"]["users"][email]["password"] = generate_password_hash(str(value['password']))
    
    def _update_service_config(self, service: str, service_data: dict[str, Any]) -> list[str]:
        """Update service configuration and return list of changes made"""
        changes: list[str] = []
        
        # Ensure the service config exists
        if service not in serverConfig["config"]:
            serverConfig["config"][service] = {}

        # Update enabled status
        if "enable" in service_data:
            old_value: bool | None = serverConfig["config"][service].get("enabled")
            new_value: bool | None = service_data["enable"]
            if old_value != new_value:
                serverConfig["config"][service]["enabled"] = new_value
                changes.append(f"enabled: {old_value} -> {new_value}")
        
        # Update interval (if applicable)
        if "interval" in service_data and service in ["thermostats", "dht", "fan"]:
            old_value: float | None = serverConfig["config"][service].get("interval")
            new_value: float | None = service_data["interval"]
            if old_value != new_value:
                # Validate interval is a positive number
                try:
                    interval_val: float = float(new_value)
                    if interval_val > 0:
                        serverConfig["config"][service]["interval"] = new_value
                        changes.append(f"interval: {old_value} -> {new_value}")
                    else:
                        logger.warning(f"Invalid interval value for {service}: {new_value}")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid interval value for {service}: {new_value}")
        
        return changes