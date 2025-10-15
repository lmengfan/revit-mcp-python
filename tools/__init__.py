# -*- coding: utf-8 -*-
"""Tool registration system for Revit MCP Server"""


def register_tools(mcp_server, revit_get_func, revit_post_func, revit_image_func):
    """Register all tools with the MCP server"""
    # Import all tool modules
    from .status_tools import register_status_tools
    from .view_tools import register_view_tools
    from .family_tools import register_family_tools
    from .model_tools import register_model_tools
    from .colors_tools import register_colors_tools
    from .code_execution_tools import register_code_execution_tools
    from .floor_tools import register_floor_tools
    from .grid_tools import register_grid_tools
    from .column_tools import register_column_tools
    
    from .beam_tools import register_beam_tools
    from .wall_tools import register_wall_tools
    from .pipe_tools import register_pipe_tools
    
    from .mapping_tools import register_mapping_tools
    from .atf_tools import register_atf_tools
    from .geometry_tools import register_geometry_tools
    from .python_tools import register_python_tools

    # Register tools from each module
    register_status_tools(mcp_server, revit_get_func)
    register_view_tools(mcp_server, revit_get_func, revit_post_func, revit_image_func)
    register_family_tools(mcp_server, revit_get_func, revit_post_func)
    register_model_tools(mcp_server, revit_get_func)
    register_colors_tools(mcp_server, revit_get_func, revit_post_func)
    register_code_execution_tools(
        mcp_server, revit_get_func, revit_post_func, revit_image_func
    )
    register_floor_tools(mcp_server, revit_get_func, revit_post_func)
    register_grid_tools(mcp_server, revit_get_func, revit_post_func)
    register_column_tools(mcp_server, revit_get_func, revit_post_func)
    
    register_beam_tools(mcp_server, revit_get_func, revit_post_func)
    register_wall_tools(mcp_server, revit_get_func, revit_post_func)
    register_pipe_tools(mcp_server, revit_get_func, revit_post_func)
    
    register_mapping_tools(mcp_server, revit_get_func)
    register_atf_tools(mcp_server, revit_get_func, revit_post_func)
    register_geometry_tools(mcp_server, revit_get_func, revit_post_func)
    
    # Register Python interpreter tools (standalone, doesn't need revit_get/post)
    register_python_tools(mcp_server)
