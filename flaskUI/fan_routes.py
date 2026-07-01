import logging
from typing import Any

from flask import request
from flask_restful import Resource

import logManager

import configManager
from ServerObjects.fan_object import FanObject
from services.utils import nextFreeId

logger: logging.Logger = logManager.logger.get_logger(__name__)

serverConfig: dict[str, Any] = configManager.serverConfig.yaml_config

def find_fan(fan_id: str) -> FanObject | None:
    """
    Find a fan by id in server configuration
    """
    fans = serverConfig.get("fan", {})
    fan = fans.get(fan_id)
    return fan if isinstance(fan, FanObject) else None

def create_fan(fan_id: str, postDict: dict[str, Any] = {}) -> FanObject:
    """
    Create a new fan object with the given id
    """
    if find_fan(fan_id) is not None:
        raise ValueError(f"Fan with id {fan_id} already exists")
    data: dict[str, Any] = {"id": fan_id}
    data.update(postDict)
    return FanObject(data)

class FanRoute(Resource):
    def get(self, fan_id: str | None = None, resource: str | None = None) -> tuple[dict[str, Any], int]:
        """
        Handle GET requests for fan resources
        URL patterns:
        - GET /fan/              - return all fans
        - GET /fan/<fan_id>      - return specific fan
        - GET /fan/<fan_id>/full_speed - trigger full speed
        """
        if fan_id is None:
            fans = serverConfig.get("fan", {})
            return {fid: f.get_all_data() for fid, f in fans.items() if isinstance(f, FanObject)}, 200

        fan: FanObject | None = find_fan(fan_id)
        if fan is None:
            return {"error": f"Fan {fan_id} not found"}, 404

        if resource == "full_speed":
            fan.setFull()

        return fan.get_all_data(), 200

    def post(self, fan_id: str | None = None, resource: str | None = None) -> tuple[dict[str, Any], int]:
        """
        Create or update fan configuration
        URL patterns:
        - POST /fan/         - create new fan (auto-assigns id)
        - POST /fan/<fan_id> - update existing fan or create with given id
        """
        postDict: dict[str, Any] = request.get_json(force=True) if request.get_data(as_text=True) != "" else {}
        logger.info(f"POST data received: {postDict}")

        if fan_id is None:
            new_id: str = nextFreeId(serverConfig, "fan")
            try:
                fan: FanObject = create_fan(new_id, postDict)
                serverConfig["fan"][new_id] = fan
            except ValueError as e:
                logger.error(f"Failed to create fan: {e}")
                return {"error": str(e)}, 400
        else:
            fan_or_none: FanObject | None = find_fan(fan_id)
            if fan_or_none is None:
                logger.info(f"Fan {fan_id} not found, creating a new one")
                try:
                    fan = create_fan(fan_id, postDict)
                    serverConfig["fan"][fan_id] = fan
                except ValueError as e:
                    logger.error(f"Failed to create fan: {e}")
                    return {"error": str(e)}, 400
            else:
                logger.info(f"Fan {fan_id} exists, updating configuration")
                fan = fan_or_none
                allowed: set[str] = {'gpio_pin', 'pwm_frequency', 'min_temperature', 'max_temperature', 'min_speed', 'max_speed', 'temp_change_threshold', 'full_speed_time_duration', 'name'}
                for key, value in postDict.items():
                    if key in allowed and hasattr(fan, key):
                        setattr(fan, key, value)
                    elif key not in allowed:
                        logger.warning(f"Attempted to set non-allowed attribute: {key}")

        try:
            configManager.serverConfig.save_config(backup=False, resource="fan")
            return fan.get_all_data(), 200
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return {"error": "Failed to save configuration"}, 500

    def delete(self, fan_id: str | None = None, resource: str | None = None) -> tuple[dict[str, Any], int]:
        """
        Delete a fan
        URL: DELETE /fan/<fan_id>
        """
        if fan_id is None:
            return {"error": "fan_id required for delete"}, 400

        fan: FanObject | None = find_fan(fan_id)
        if fan is None:
            return {"error": f"Fan {fan_id} not found"}, 404

        try:
            fan.cleanup()
            del serverConfig["fan"][fan_id]
            configManager.serverConfig.save_config(backup=False, resource="fan")
            return {"success": True}, 200
        except Exception as e:
            logger.error(f"Failed to delete fan: {e}")
            return {"error": "Failed to delete fan"}, 500
