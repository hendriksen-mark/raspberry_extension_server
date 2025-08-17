"""
Helper functions to make FastAPI routing more concise, similar to Flask
"""
from fastapi import FastAPI, Response, Body
from typing import Any, Callable, Optional, List
import inspect


class FlaskLikeRoutes:
    """
    A Flask-like routing system for FastAPI
    Usage: 
        routes = FlaskLikeRoutes(app)
        routes.add_route("/api/users", UserRoute, methods=["GET", "POST"])
    """
    
    def __init__(self, app: FastAPI):
        self.app = app
    
    def add_route(self, path: str, route_class: Any, methods: List[str] = None, **kwargs):
        """Add a route with Flask-like simplicity"""
        add_resource_routes(self.app, path, route_class, methods, **kwargs)


def add_resource_routes(
    app: FastAPI, 
    base_path: str, 
    route_class: Any, 
    methods: List[str] = None,
    has_resource: bool = True,
    has_value: bool = False,
    has_mac: bool = False
):
    """
    Add routes for a resource class with GET, POST, PUT, DELETE methods
    Similar to Flask's route decorator but for FastAPI
    
    Args:
        app: FastAPI app instance
        base_path: Base path for the routes (e.g., "/dht", "/fan")
        route_class: Route class with get, post, put, delete methods
        methods: List of HTTP methods to support (defaults to all available)
        has_resource: Whether routes should include /{resource} parameter
        has_value: Whether routes should include /{value} parameter
        has_mac: Whether routes should include /{mac} parameter (for thermostat routes)
    """
    if methods is None:
        methods = []
        # Auto-detect available methods from the route class
        for method_name in ['get', 'post', 'put', 'delete']:
            if hasattr(route_class, method_name):
                methods.append(method_name.upper())
    
    # Create route instance
    route_instance = route_class()
    
    # Build path patterns based on parameters
    paths = [base_path]
    
    if has_mac:
        # Special case for thermostat routes with MAC addresses
        paths = [
            "/{mac}",
            "/{mac}/{resource}" if has_resource else "/{mac}",
        ]
        if has_value:
            paths.append("/{mac}/{resource}/{value}")
    else:
        if has_resource:
            paths.append(f"{base_path}/{{resource}}")
        if has_value and has_resource:
            paths.append(f"{base_path}/{{resource}}/{{value}}")
    
    # Register routes for each method
    for method in methods:
        method_lower = method.lower()
        if not hasattr(route_instance, method_lower):
            continue
            
        route_method = getattr(route_instance, method_lower)
        
        # Check if method is async
        is_async = inspect.iscoroutinefunction(route_method)
        
        for path in paths:
            # Create the handler function
            if method_lower == 'get':
                handler = create_get_handler(route_method, is_async, has_mac, has_resource, has_value)
            elif method_lower in ['post', 'put']:
                handler = create_post_handler(route_method, is_async, has_mac, has_resource, has_value)
            elif method_lower == 'delete':
                handler = create_delete_handler(route_method, is_async, has_mac, has_resource)
            else:
                continue
                
            # Register the route
            getattr(app, method_lower)(path)(handler)


def create_get_handler(route_method: Callable, is_async: bool, has_mac: bool, has_resource: bool, has_value: bool):
    """Create GET handler function"""
    if has_mac and has_resource and has_value:
        if is_async:
            async def handler(response: Response, mac: str, resource: str = None, value: str = None):
                response_data, response_code = await route_method(mac, resource, value)
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response, mac: str, resource: str = None, value: str = None):
                response_data, response_code = route_method(mac, resource, value)
                response.status_code = response_code
                return response_data
    elif has_mac and has_resource:
        if is_async:
            async def handler(response: Response, mac: str, resource: str = None):
                response_data, response_code = await route_method(mac, resource)
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response, mac: str, resource: str = None):
                response_data, response_code = route_method(mac, resource)
                response.status_code = response_code
                return response_data
    elif has_mac:
        if is_async:
            async def handler(response: Response, mac: str):
                response_data, response_code = await route_method(mac)
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response, mac: str):
                response_data, response_code = route_method(mac)
                response.status_code = response_code
                return response_data
    elif has_resource and has_value:
        if is_async:
            async def handler(response: Response, resource: str = None, value: str = None):
                response_data, response_code = await route_method(resource, value)
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response, resource: str = None, value: str = None):
                response_data, response_code = route_method(resource, value)
                response.status_code = response_code
                return response_data
    elif has_resource:
        if is_async:
            async def handler(response: Response, resource: str = None):
                response_data, response_code = await route_method(resource)
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response, resource: str = None):
                response_data, response_code = route_method(resource)
                response.status_code = response_code
                return response_data
    else:
        if is_async:
            async def handler(response: Response):
                response_data, response_code = await route_method()
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response):
                response_data, response_code = route_method()
                response.status_code = response_code
                return response_data
    
    return handler


def create_post_handler(route_method: Callable, is_async: bool, has_mac: bool, has_resource: bool, has_value: bool):
    """Create POST/PUT handler function"""
    if has_mac and has_resource:
        if is_async:
            async def handler(response: Response, mac: str, resource: str = None, data: dict[str, Any] = Body(default={})):
                response_data, response_code = await route_method(mac, resource, data)
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response, mac: str, resource: str = None, data: dict[str, Any] = Body(default={})):
                response_data, response_code = route_method(mac, resource, data)
                response.status_code = response_code
                return response_data
    elif has_mac:
        if is_async:
            async def handler(response: Response, mac: str, data: dict[str, Any] = Body(default={})):
                response_data, response_code = await route_method(mac, data)
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response, mac: str, data: dict[str, Any] = Body(default={})):
                response_data, response_code = route_method(mac, data)
                response.status_code = response_code
                return response_data
    elif has_resource and has_value:
        if is_async:
            async def handler(response: Response, resource: str = None, value: str = None, data: dict[str, Any] = Body(default={})):
                response_data, response_code = await route_method(resource, value, data)
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response, resource: str = None, value: str = None, data: dict[str, Any] = Body(default={})):
                response_data, response_code = route_method(resource, value, data)
                response.status_code = response_code
                return response_data
    elif has_resource:
        if is_async:
            async def handler(response: Response, resource: str = None, data: dict[str, Any] = Body(default={})):
                response_data, response_code = await route_method(resource, data)
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response, resource: str = None, data: dict[str, Any] = Body(default={})):
                response_data, response_code = route_method(resource, data)
                response.status_code = response_code
                return response_data
    else:
        if is_async:
            async def handler(response: Response, data: dict[str, Any] = Body(default={})):
                response_data, response_code = await route_method(data)
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response, data: dict[str, Any] = Body(default={})):
                response_data, response_code = route_method(data)
                response.status_code = response_code
                return response_data
    
    return handler


def create_delete_handler(route_method: Callable, is_async: bool, has_mac: bool, has_resource: bool):
    """Create DELETE handler function"""
    if has_mac and has_resource:
        if is_async:
            async def handler(response: Response, mac: str, resource: str = None):
                response_data, response_code = await route_method(mac, resource)
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response, mac: str, resource: str = None):
                response_data, response_code = route_method(mac, resource)
                response.status_code = response_code
                return response_data
    elif has_mac:
        if is_async:
            async def handler(response: Response, mac: str):
                response_data, response_code = await route_method(mac)
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response, mac: str):
                response_data, response_code = route_method(mac)
                response.status_code = response_code
                return response_data
    elif has_resource:
        if is_async:
            async def handler(response: Response, resource: str = None):
                response_data, response_code = await route_method(resource)
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response, resource: str = None):
                response_data, response_code = route_method(resource)
                response.status_code = response_code
                return response_data
    else:
        if is_async:
            async def handler(response: Response):
                response_data, response_code = await route_method()
                response.status_code = response_code
                return response_data
        else:
            async def handler(response: Response):
                response_data, response_code = route_method()
                response.status_code = response_code
                return response_data
    
    return handler
