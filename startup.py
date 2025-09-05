# -*- coding: UTF-8 -*-
"""
Revit MCP Extension Startup
Registers all MCP routes and initializes the API
"""

from pyrevit import routes
import logging

logger = logging.getLogger(__name__)

# Initialize the main API
api = routes.API("revit_mcp")


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

        from revit_mcp.colors import register_color_routes

        register_color_routes(api)

        from revit_mcp.code_execution import register_code_execution_routes

        register_code_execution_routes(api)

        from revit_mcp.floor_management import register_floor_management_routes

        register_floor_management_routes(api)

        from revit_mcp.grid_management import register_grid_management_routes

        register_grid_management_routes(api)

        from revit_mcp.column_management import register_column_management_routes

        register_column_management_routes(api)

        from revit_mcp.beam_management import register_beam_management_routes

        register_beam_management_routes(api)
        
        from revit_mcp.wall_management import register_wall_management_routes

        register_wall_management_routes(api)
        
        from revit_mcp.pipe_management import register_pipe_management_routes

        register_pipe_management_routes(api)
        
        from revit_mcp.api_mapping import register_api_mapping_routes

        register_api_mapping_routes(api)

        logger.info("All MCP routes registered successfully")

    except Exception as e:
        logger.error("Failed to register MCP routes: %s", str(e))
        raise


# Register all routes when the extension loads
register_routes()

@api.route('/state/', methods=["GET"])
def revit_state():
    """
    Health check endpoint that verifies Revit context availability
    
    Returns:
        dict: Health status with Revit document information
    """
    return routes.make_response(data={
        "status": "active",
        "health": "healthy",
        "revit_available": True,
        "api_name": "revit_mcp"
    })
