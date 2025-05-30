# -*- coding: UTF-8 -*-
"""
Revit MCP Extension Startup
Registers all MCP routes and initializes the API
"""

from pyrevit import routes
import logging

logger = logging.getLogger(__name__)

# Initialize the main API
api = routes.API('revit_mcp')

def register_routes():
    """Register all MCP route modules"""
    try:
        # Import and register status routes
        from revit_mcp.status import register_status_routes
        register_status_routes(api)

        from revit_mcp.model_info import register_model_info_routes
        register_model_info_routes(api)

        from revit_mcp.views import register_views_routes
        register_views_routes(api)

        from revit_mcp.placement import register_placement_routes
        register_placement_routes(api)

        
        logger.info("All MCP routes registered successfully")
        
    except Exception as e:
        logger.error("Failed to register MCP routes:{}".format(str(e)))
        raise

# Register all routes when the extension loads
register_routes()