# -*- coding: UTF-8 -*-
"""
API Mapping Module for Revit MCP
Provides mapping between MCP tools and HTTP API routes
"""

from pyrevit import routes
import json
import logging

logger = logging.getLogger(__name__)


def register_api_mapping_routes(api):
    """Register API mapping routes with the API"""

    @api.route("/mcp_to_http_mapping/", methods=["GET"])
    @api.route("/mcp_to_http_mapping", methods=["GET"])
    @api.route("/revit_mcp_to_http_mapping/", methods=["GET"])
    @api.route("/revit_mcp_to_http_mapping", methods=["GET"])
    @api.route("/get_revit_mcp_to_http_mapping/", methods=["GET"])
    @api.route("/get_revit_mcp_to_http_mapping", methods=["GET"])
    def get_revit_mcp_to_http_mapping():
        """
        Provides a comprehensive mapping between MCP tools and their corresponding HTTP API routes.
        
        This endpoint helps LLMs understand how to replicate MCP workflows using HTTP calls by providing:
        - Direct mapping between MCP tool names and HTTP endpoints
        - HTTP method and URL for each operation
        - Request body examples for HTTP calls
        - Response format information
        - Code examples for both MCP and HTTP usage
        
        Returns:
            dict: Complete mapping with examples and usage patterns
        """
        try:
            base_url = "http://localhost:48884"  # Default pyRevit Routes port
            
            mapping_data = {
                "base_url": base_url,
                "description": "Mapping between MCP tools and HTTP API routes for Revit MCP Server",
                "last_updated": "2024-12-20",
                "mappings": {
                    
                    # Status Tools
                    "get_revit_status": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/status/",
                        "http_url": "{}/revit_mcp/status/".format(base_url),
                        "description": "Check if Revit MCP API is active and responding",
                        "request_body": None,
                        "mcp_example": "await get_revit_status()",
                        "http_example": "GET http://localhost:48884/revit_mcp/status/",
                        "response_format": {
                            "status": "active",
                            "health": "healthy", 
                            "revit_available": True,
                            "document_title": "project_name",
                            "api_name": "revit_mcp"
                        }
                    },
                    
                    # Model Information Tools
                    "get_revit_model_info": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/model_info/",
                        "http_url": "{}/revit_mcp/model_info/".format(base_url),
                        "description": "Get comprehensive information about the current Revit model",
                        "request_body": None,
                        "mcp_example": "await get_revit_model_info()",
                        "http_example": "GET http://localhost:48884/revit_mcp/model_info/"
                    },
                    
                    "get_selected_elements": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/selected_elements/",
                        "http_url": "{}/revit_mcp/selected_elements/".format(base_url),
                        "description": "Get information about currently selected elements in Revit",
                        "request_body": None,
                        "mcp_example": "await get_selected_elements()",
                        "http_example": "GET http://localhost:48884/revit_mcp/selected_elements/"
                    },
                    
                    "get_floor_details": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/floor_details/",
                        "http_url": "{}/revit_mcp/floor_details/".format(base_url),
                        "description": "Get comprehensive information about selected floor elements",
                        "request_body": None,
                        "mcp_example": "await get_floor_details()",
                        "http_example": "GET http://localhost:48884/revit_mcp/floor_details/"
                    },
                    
                    # View Tools
                    "list_revit_views": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/views/",
                        "http_url": "{}/revit_mcp/views/".format(base_url),
                        "description": "Get a list of all exportable views in the current Revit model",
                        "request_body": None,
                        "mcp_example": "await list_revit_views()",
                        "http_example": "GET http://localhost:48884/revit_mcp/views/"
                    },
                    
                    "get_revit_view": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/view_image/",
                        "http_url": "{}/revit_mcp/view_image/".format(base_url),
                        "description": "Export a specific Revit view as an image",
                        "request_body": None,
                        "mcp_example": "await get_revit_view(view_name='Floor Plan: Level 1')",
                        "http_example": "GET http://localhost:48884/revit_mcp/view_image/?view_name=Floor%20Plan:%20Level%201",
                        "query_parameters": {
                            "view_name": "Name of the view to export"
                        }
                    },
                    
                    "get_current_view_info": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/current_view_info/",
                        "http_url": "{}/revit_mcp/current_view_info/".format(base_url),
                        "description": "Get detailed information about the currently active view",
                        "request_body": None,
                        "mcp_example": "await get_current_view_info()",
                        "http_example": "GET http://localhost:48884/revit_mcp/current_view_info/"
                    },
                    
                    "get_current_view_elements": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/current_view_elements/",
                        "http_url": "{}/revit_mcp/current_view_elements/".format(base_url),
                        "description": "Get all elements visible in the currently active view",
                        "request_body": None,
                        "mcp_example": "await get_current_view_elements()",
                        "http_example": "GET http://localhost:48884/revit_mcp/current_view_elements/"
                    },
                    
                    # Family Tools
                    "place_family": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/place_family/",
                        "http_url": "{}/revit_mcp/place_family/".format(base_url),
                        "description": "Place a family instance at a specified location",
                        "mcp_example": """await place_family(
                            family_name="Basic Wall",
                            type_name="Generic - 200mm", 
                            x=0.0, y=0.0, z=0.0,
                            level_name="Level 1",
                            properties={"Mark": "W1"}
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/place_family/
Content-Type: application/json

{
    "family_name": "Basic Wall",
    "type_name": "Generic - 200mm",
    "location": {"x": 0.0, "y": 0.0, "z": 0.0},
    "level_name": "Level 1",
    "properties": {"Mark": "W1"}
}""",
                        "request_body": {
                            "family_name": "string (required)",
                            "type_name": "string (optional)",
                            "location": {"x": "float", "y": "float", "z": "float"},
                            "rotation": "float (optional)",
                            "level_name": "string (optional)",
                            "properties": "object (optional)"
                        }
                    },
                    
                    "list_families": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/families/",
                        "http_url": "{}/revit_mcp/families/".format(base_url),
                        "description": "Get a list of available family types",
                        "request_body": None,
                        "mcp_example": "await list_families(contains='Wall', limit=50)",
                        "http_example": "GET http://localhost:48884/revit_mcp/families/?contains=Wall&limit=50",
                        "query_parameters": {
                            "contains": "Filter families containing this text",
                            "limit": "Maximum number of results"
                        }
                    },
                    
                    "list_family_categories": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/family_categories/",
                        "http_url": "{}/revit_mcp/family_categories/".format(base_url),
                        "description": "Get a list of all family categories",
                        "request_body": None,
                        "mcp_example": "await list_family_categories()",
                        "http_example": "GET http://localhost:48884/revit_mcp/family_categories/"
                    },
                    
                    "list_levels": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/levels/",
                        "http_url": "{}/revit_mcp/levels/".format(base_url),
                        "description": "Get a list of all levels in the model",
                        "request_body": None,
                        "mcp_example": "await list_levels()",
                        "http_example": "GET http://localhost:48884/revit_mcp/levels/"
                    },
                    
                    # Floor Management Tools
                    "create_or_edit_floor": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_or_edit_floor/",
                        "http_url": "{}/revit_mcp/create_or_edit_floor/".format(base_url),
                        "description": "Create a new floor or edit an existing floor",
                        "mcp_example": """await create_or_edit_floor(
                            level_name="Level 1",
                            boundary_curves=[
                                {"type": "Line", "start_point": {"x": 0, "y": 0, "z": 0}, "end_point": {"x": 5000, "y": 0, "z": 0}},
                                {"type": "Line", "start_point": {"x": 5000, "y": 0, "z": 0}, "end_point": {"x": 5000, "y": 3000, "z": 0}},
                                {"type": "Line", "start_point": {"x": 5000, "y": 3000, "z": 0}, "end_point": {"x": 0, "y": 3000, "z": 0}},
                                {"type": "Line", "start_point": {"x": 0, "y": 3000, "z": 0}, "end_point": {"x": 0, "y": 0, "z": 0}}
                            ],
                            height_offset=100.0,
                            thickness=200.0
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_or_edit_floor/
Content-Type: application/json

{
    "level_name": "Level 1",
    "boundary_curves": [
        {"type": "Line", "start_point": {"x": 0, "y": 0, "z": 0}, "end_point": {"x": 5000, "y": 0, "z": 0}},
        {"type": "Line", "start_point": {"x": 5000, "y": 0, "z": 0}, "end_point": {"x": 5000, "y": 3000, "z": 0}},
        {"type": "Line", "start_point": {"x": 5000, "y": 3000, "z": 0}, "end_point": {"x": 0, "y": 3000, "z": 0}},
        {"type": "Line", "start_point": {"x": 0, "y": 3000, "z": 0}, "end_point": {"x": 0, "y": 0, "z": 0}}
    ],
    "height_offset": 100.0,
    "thickness": 200.0
}""",
                        "request_body": {
                            "level_name": "string (required)",
                            "boundary_curves": "array (required)",
                            "element_id": "string (optional, for editing)",
                            "height_offset": "float (optional)",
                            "transformation": "object (optional)",
                            "thickness": "float (optional)",
                            "floor_type_name": "string (optional)",
                            "properties": "object (optional)"
                        }
                    },
                    
                    "create_rectangular_floor": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_rectangular_floor/",
                        "http_url": "{}/revit_mcp/create_rectangular_floor/".format(base_url),
                        "description": "Create a rectangular floor with specified dimensions",
                        "mcp_example": """await create_rectangular_floor(
                            level_name="Level 1",
                            width=5000.0,
                            length=3000.0,
                            height_offset=100.0,
                            thickness=200.0
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_rectangular_floor/
Content-Type: application/json

{
    "level_name": "Level 1",
    "width": 5000.0,
    "length": 3000.0,
    "height_offset": 100.0,
    "thickness": 200.0
}""",
                        "request_body": {
                            "level_name": "string (required)",
                            "width": "float (required)",
                            "length": "float (required)",
                            "origin_x": "float (optional)",
                            "origin_y": "float (optional)",
                            "origin_z": "float (optional)",
                            "height_offset": "float (optional)",
                            "thickness": "float (optional)",
                            "floor_type_name": "string (optional)",
                            "properties": "object (optional)"
                        }
                    },
                    
                    # Color Tools
                    "color_splash": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/color_splash/",
                        "http_url": "{}/revit_mcp/color_splash/".format(base_url),
                        "description": "Color elements in a category based on parameter values",
                        "mcp_example": """await color_splash(
                            category_name="Walls",
                            parameter_name="Mark",
                            use_gradient=False
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/color_splash/
Content-Type: application/json

{
    "category_name": "Walls",
    "parameter_name": "Mark",
    "use_gradient": false
}""",
                        "request_body": {
                            "category_name": "string (required)",
                            "parameter_name": "string (required)",
                            "use_gradient": "boolean (optional)",
                            "custom_colors": "array (optional)"
                        }
                    },
                    
                    "clear_colors": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/clear_colors/",
                        "http_url": "{}/revit_mcp/clear_colors/".format(base_url),
                        "description": "Clear color overrides for elements in a category",
                        "mcp_example": "await clear_colors(category_name='Walls')",
                        "http_example": """POST http://localhost:48884/revit_mcp/clear_colors/
Content-Type: application/json

{
    "category_name": "Walls"
}""",
                        "request_body": {
                            "category_name": "string (required)"
                        }
                    },
                    
                    "list_category_parameters": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/category_parameters/",
                        "http_url": "{}/revit_mcp/category_parameters/".format(base_url),
                        "description": "Get available parameters for elements in a category",
                        "mcp_example": "await list_category_parameters(category_name='Walls')",
                        "http_example": "GET http://localhost:48884/revit_mcp/category_parameters/?category_name=Walls",
                        "query_parameters": {
                            "category_name": "Name of the category to check parameters for"
                        }
                    },
                    
                    # Code Execution Tools
                    "execute_revit_code": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/execute_code/",
                        "http_url": "{}/revit_mcp/execute_code/".format(base_url),
                        "description": "Execute IronPython code directly in Revit context",
                        "mcp_example": """await execute_revit_code(
                            code='print("Hello from Revit!")',
                            description="Test code execution"
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/execute_code/
Content-Type: application/json

{
    "code": "print(\\"Hello from Revit!\\")",
    "description": "Test code execution"
}""",
                        "request_body": {
                            "code": "string (required) - IronPython code to execute",
                            "description": "string (optional) - Description of the code"
                        }
                    },
                    
                    # Grid Management Tools
                    "create_or_edit_grid": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_or_edit_grid/",
                        "http_url": "{}/revit_mcp/create_or_edit_grid/".format(base_url),
                        "description": "Create a new grid or edit an existing grid in Revit",
                        "mcp_example": """await create_or_edit_grid(
                            grid_type="linear",
                            name="A",
                            start_point={"x": 0, "y": 0, "z": 0},
                            end_point={"x": 10000, "y": 0, "z": 0}
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_or_edit_grid/
Content-Type: application/json

{
    "grid_type": "linear",
    "name": "A",
    "start_point": {"x": 0, "y": 0, "z": 0},
    "end_point": {"x": 10000, "y": 0, "z": 0}
}""",
                        "request_body": {
                            "grid_type": "string (required) - 'linear' or 'radial'",
                            "element_id": "string (optional) - For editing existing grid",
                            "name": "string (optional) - Grid name/label",
                            "start_point": "object (optional) - For linear grids",
                            "end_point": "object (optional) - For linear grids",
                            "center_point": "object (optional) - For radial grids",
                            "radius": "float (optional) - For radial grids",
                            "start_angle": "float (optional) - For radial grids",
                            "end_angle": "float (optional) - For radial grids",
                            "properties": "object (optional)"
                        }
                    },
                    
                    "create_linear_grid": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_linear_grid/",
                        "http_url": "{}/revit_mcp/create_linear_grid/".format(base_url),
                        "description": "Create a linear grid with start and end points",
                        "mcp_example": """await create_linear_grid(
                            start_point={"x": 0, "y": 0, "z": 0},
                            end_point={"x": 15000, "y": 0, "z": 0},
                            name="A"
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_linear_grid/
Content-Type: application/json

{
    "start_point": {"x": 0, "y": 0, "z": 0},
    "end_point": {"x": 15000, "y": 0, "z": 0},
    "name": "A"
}""",
                        "request_body": {
                            "start_point": "object (required)",
                            "end_point": "object (required)",
                            "name": "string (optional)",
                            "properties": "object (optional)"
                        }
                    },
                    
                    "create_radial_grid": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_radial_grid/",
                        "http_url": "{}/revit_mcp/create_radial_grid/".format(base_url),
                        "description": "Create a radial (arc) grid with center point, radius, and angles",
                        "mcp_example": """await create_radial_grid(
                            center_point={"x": 5000, "y": 5000, "z": 0},
                            radius=10000.0,
                            start_angle=0.0,
                            end_angle=270.0,
                            name="R1"
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_radial_grid/
Content-Type: application/json

{
    "center_point": {"x": 5000, "y": 5000, "z": 0},
    "radius": 10000.0,
    "start_angle": 0.0,
    "end_angle": 270.0,
    "name": "R1"
}""",
                        "request_body": {
                            "center_point": "object (required)",
                            "radius": "float (required)",
                            "start_angle": "float (optional)",
                            "end_angle": "float (optional)",
                            "name": "string (optional)",
                            "properties": "object (optional)"
                        }
                    },
                    
                    "query_grid": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/query_grid/",
                        "http_url": "{}/revit_mcp/query_grid/".format(base_url),
                        "description": "Query an existing grid by ID and return its configuration",
                        "mcp_example": "await query_grid(element_id='123456')",
                        "http_example": """POST http://localhost:48884/revit_mcp/query_grid/
Content-Type: application/json

{
    "element_id": "123456"
}""",
                        "request_body": {
                            "element_id": "string (required)"
                        }
                    },
                    
                    "find_grid_intersections": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/find_grid_intersections/",
                        "http_url": "{}/revit_mcp/find_grid_intersections/".format(base_url),
                        "description": "Find intersection points between grids in the model",
                        "mcp_example": """await find_grid_intersections(
                            grid_ids=["123", "456"],
                            level_name="Level 1"
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/find_grid_intersections/
Content-Type: application/json

{
    "grid_ids": ["123", "456"],
    "level_name": "Level 1"
}""",
                        "request_body": {
                            "grid_ids": "array (optional) - Specific grid IDs",
                            "level_name": "string (optional) - Level for Z projection"
                        }
                    },
                    
                    "create_grid_system": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_grid_system/",
                        "http_url": "{}/revit_mcp/create_grid_system/".format(base_url),
                        "description": "Create a complete grid system with multiple linear and/or radial grids",
                        "mcp_example": """await create_grid_system(
                            linear_grids=[
                                {"name": "A", "start_point": {"x": 0, "y": 0, "z": 0}, "end_point": {"x": 0, "y": 20000, "z": 0}},
                                {"name": "1", "start_point": {"x": 0, "y": 0, "z": 0}, "end_point": {"x": 8000, "y": 0, "z": 0}}
                            ]
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_grid_system/
Content-Type: application/json

{
    "linear_grids": [
        {"name": "A", "start_point": {"x": 0, "y": 0, "z": 0}, "end_point": {"x": 0, "y": 20000, "z": 0}},
        {"name": "1", "start_point": {"x": 0, "y": 0, "z": 0}, "end_point": {"x": 8000, "y": 0, "z": 0}}
    ]
}""",
                        "request_body": {
                            "linear_grids": "array (required)",
                            "radial_grids": "array (optional)",
                            "vertical_extents": "object (optional)"
                        }
                    },
                    
                    "get_grid_details": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/grid_details/",
                        "http_url": "{}/revit_mcp/grid_details/".format(base_url),
                        "description": "Get comprehensive information about selected grid elements",
                        "mcp_example": "await get_grid_details()",
                        "http_example": "GET http://localhost:48884/revit_mcp/grid_details/",
                        "request_body": None
                    },
                    
                    # Column Management Tools
                    "create_or_edit_column": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_or_edit_column/",
                        "http_url": "{}/revit_mcp/create_or_edit_column/".format(base_url),
                        "description": "Create a new structural column or edit an existing column",
                        "mcp_example": """await create_or_edit_column(
                            family_name="Concrete-Rectangular-Column",
                            type_name="600 x 600mm",
                            base_level="Level 1",
                            top_level="Level 2",
                            location={"x": 5000, "y": 5000, "z": 0}
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_or_edit_column/
Content-Type: application/json

{
    "family_name": "Concrete-Rectangular-Column",
    "type_name": "600 x 600mm",
    "base_level": "Level 1",
    "top_level": "Level 2",
    "location": {"x": 5000, "y": 5000, "z": 0}
}""",
                        "request_body": {
                            "family_name": "string (required)",
                            "base_level": "string (required)",
                            "location": "object (required)",
                            "element_id": "string (optional) - For editing",
                            "type_name": "string (optional)",
                            "top_level": "string (optional)",
                            "height": "float (optional)",
                            "properties": "object (optional)"
                        }
                    },
                    
                    "create_column_at_grid_intersection": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_column_at_grid_intersection/",
                        "http_url": "{}/revit_mcp/create_column_at_grid_intersection/".format(base_url),
                        "description": "Create a structural column at a specific grid intersection point",
                        "mcp_example": """await create_column_at_grid_intersection(
                            family_name="Concrete-Rectangular-Column",
                            base_level="Level 1",
                            intersection_point={"x": 5000, "y": 8000, "z": 0}
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_column_at_grid_intersection/
Content-Type: application/json

{
    "family_name": "Concrete-Rectangular-Column",
    "base_level": "Level 1",
    "intersection_point": {"x": 5000, "y": 8000, "z": 0}
}""",
                        "request_body": {
                            "family_name": "string (required)",
                            "base_level": "string (required)",
                            "intersection_point": "object (required)",
                            "type_name": "string (optional)",
                            "properties": "object (optional)"
                        }
                    },
                    
                    "create_columns_at_grid_intersections": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_columns_at_grid_intersections/",
                        "http_url": "{}/revit_mcp/create_columns_at_grid_intersections/".format(base_url),
                        "description": "Create multiple structural columns at grid intersection points",
                        "mcp_example": """await create_columns_at_grid_intersections(
                            family_name="Steel-Wide_Flange-Column",
                            base_level="Level 1",
                            intersections=intersections_data
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_columns_at_grid_intersections/
Content-Type: application/json

{
    "family_name": "Steel-Wide_Flange-Column",
    "base_level": "Level 1",
    "intersections": [...]
}""",
                        "request_body": {
                            "family_name": "string (required)",
                            "base_level": "string (required)",
                            "intersections": "array (required)",
                            "type_name": "string (optional)",
                            "mark_prefix": "string (optional)"
                        }
                    },
                    
                    "query_column": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/query_column/",
                        "http_url": "{}/revit_mcp/query_column/".format(base_url),
                        "description": "Query an existing structural column by ID",
                        "mcp_example": "await query_column(element_id='123456')",
                        "http_example": """POST http://localhost:48884/revit_mcp/query_column/
Content-Type: application/json

{
    "element_id": "123456"
}""",
                        "request_body": {
                            "element_id": "string (required)"
                        }
                    },
                    
                    "get_column_details": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/column_details/",
                        "http_url": "{}/revit_mcp/column_details/".format(base_url),
                        "description": "Get comprehensive information about selected structural column elements",
                        "mcp_example": "await get_column_details()",
                        "http_example": "GET http://localhost:48884/revit_mcp/column_details/",
                        "request_body": None
                    },
                    
                    "create_column_layout": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_column_layout/",
                        "http_url": "{}/revit_mcp/create_column_layout/".format(base_url),
                        "description": "Create a complete column layout based on a grid system",
                        "mcp_example": """await create_column_layout(
                            family_name="Concrete-Rectangular-Column",
                            base_level="Level 1",
                            grid_layout=grid_intersections
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_column_layout/
Content-Type: application/json

{
    "family_name": "Concrete-Rectangular-Column",
    "base_level": "Level 1",
    "grid_layout": {...}
}""",
                        "request_body": {
                            "family_name": "string (required)",
                            "base_level": "string (required)",
                            "grid_layout": "object (required)",
                            "skip_intersections": "array (optional)"
                        }
                    },
                    
                    # Beam Management Tools
                    "create_or_edit_beam": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_or_edit_beam/",
                        "http_url": "{}/revit_mcp/create_or_edit_beam/".format(base_url),
                        "description": "Create a new structural beam or edit an existing one",
                        "mcp_example": """await create_or_edit_beam(
                            level_name="Level 1",
                            start_point={"x": 0, "y": 0, "z": 3000},
                            end_point={"x": 5000, "y": 0, "z": 3000},
                            family_name="W-Wide Flange",
                            type_name="W12X26"
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_or_edit_beam/
Content-Type: application/json

{
    "level_name": "Level 1",
    "start_point": {"x": 0, "y": 0, "z": 3000},
    "end_point": {"x": 5000, "y": 0, "z": 3000},
    "family_name": "W-Wide Flange",
    "type_name": "W12X26"
}""",
                        "request_body": {
                            "level_name": "string (required)",
                            "start_point": "object (required)",
                            "end_point": "object (required)",
                            "element_id": "string (optional) - For editing",
                            "family_name": "string (optional)",
                            "type_name": "string (optional)",
                            "properties": "object (optional)"
                        }
                    },
                    
                    "place_beam_between_points": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/place_beam_between_points/",
                        "http_url": "{}/revit_mcp/place_beam_between_points/".format(base_url),
                        "description": "Place a structural beam between two specific points",
                        "mcp_example": """await place_beam_between_points(
                            level_name="Level 1",
                            point1={"x": 0, "y": 0, "z": 3000},
                            point2={"x": 5000, "y": 0, "z": 3000}
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/place_beam_between_points/
Content-Type: application/json

{
    "level_name": "Level 1",
    "point1": {"x": 0, "y": 0, "z": 3000},
    "point2": {"x": 5000, "y": 0, "z": 3000}
}""",
                        "request_body": {
                            "level_name": "string (required)",
                            "point1": "object (required)",
                            "point2": "object (required)",
                            "family_name": "string (optional)",
                            "type_name": "string (optional)",
                            "mark": "string (optional)"
                        }
                    },
                    
                    "query_beam": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/query_beam/",
                        "http_url": "{}/revit_mcp/query_beam/".format(base_url),
                        "description": "Query basic information about a structural beam by element ID",
                        "mcp_example": "await query_beam(element_id='123456')",
                        "http_example": "GET http://localhost:48884/revit_mcp/query_beam/?element_id=123456",
                        "query_parameters": {
                            "element_id": "Element ID of the beam to query"
                        }
                    },
                    
                    "get_beam_details": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/get_beam_details/",
                        "http_url": "{}/revit_mcp/get_beam_details/".format(base_url),
                        "description": "Get comprehensive information about selected structural beam elements",
                        "mcp_example": "await get_beam_details()",
                        "http_example": "GET http://localhost:48884/revit_mcp/get_beam_details/",
                        "request_body": None
                    },
                    
                    "create_beam_layout": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_beam_layout/",
                        "http_url": "{}/revit_mcp/create_beam_layout/".format(base_url),
                        "description": "Create multiple structural beams in a layout pattern",
                        "mcp_example": """await create_beam_layout(
                            level_name="Level 1",
                            beam_configs=[
                                {"start_point": {"x": 0, "y": 0, "z": 3000}, "end_point": {"x": 5000, "y": 0, "z": 3000}}
                            ]
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_beam_layout/
Content-Type: application/json

{
    "level_name": "Level 1",
    "beam_configs": [
        {"start_point": {"x": 0, "y": 0, "z": 3000}, "end_point": {"x": 5000, "y": 0, "z": 3000}}
    ]
}""",
                        "request_body": {
                            "level_name": "string (required)",
                            "beam_configs": "array (required)",
                            "layout_type": "string (optional)",
                            "family_name": "string (optional)",
                            "naming_pattern": "string (optional)"
                        }
                    },
                    
                    # Wall Management Tools
                    "create_or_edit_wall": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_or_edit_wall/",
                        "http_url": "{}/revit_mcp/create_or_edit_wall/".format(base_url),
                        "description": "Create a new wall or edit an existing one",
                        "mcp_example": """await create_or_edit_wall(
                            level_name="Level 1",
                            curve_points=[
                                {"x": 0, "y": 0, "z": 0},
                                {"x": 5000, "y": 0, "z": 0}
                            ],
                            wall_type_name="Generic - 200mm"
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_or_edit_wall/
Content-Type: application/json

{
    "level_name": "Level 1",
    "curve_points": [
        {"x": 0, "y": 0, "z": 0},
        {"x": 5000, "y": 0, "z": 0}
    ],
    "wall_type_name": "Generic - 200mm"
}""",
                        "request_body": {
                            "level_name": "string (required)",
                            "curve_points": "array (required)",
                            "element_id": "string (optional) - For editing",
                            "wall_type_name": "string (optional)",
                            "height": "float (optional)",
                            "structural": "boolean (optional)",
                            "properties": "object (optional)"
                        }
                    },
                    
                    "create_rectangular_wall": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_rectangular_wall/",
                        "http_url": "{}/revit_mcp/create_rectangular_wall/".format(base_url),
                        "description": "Create a rectangular wall enclosure",
                        "mcp_example": """await create_rectangular_wall(
                            level_name="Level 1",
                            origin={"x": 0, "y": 0, "z": 0},
                            width=5000.0,
                            length=3000.0
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_rectangular_wall/
Content-Type: application/json

{
    "level_name": "Level 1",
    "origin": {"x": 0, "y": 0, "z": 0},
    "width": 5000.0,
    "length": 3000.0
}""",
                        "request_body": {
                            "level_name": "string (required)",
                            "origin": "object (required)",
                            "width": "float (required)",
                            "length": "float (required)",
                            "wall_type_name": "string (optional)",
                            "height": "float (optional)",
                            "properties": "object (optional)"
                        }
                    },
                    
                    "query_wall": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/query_wall/",
                        "http_url": "{}/revit_mcp/query_wall/".format(base_url),
                        "description": "Query basic information about a wall by element ID",
                        "mcp_example": "await query_wall(element_id='123456')",
                        "http_example": "GET http://localhost:48884/revit_mcp/query_wall/?element_id=123456",
                        "query_parameters": {
                            "element_id": "Element ID of the wall to query"
                        }
                    },
                    
                    "get_wall_details": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/get_wall_details/",
                        "http_url": "{}/revit_mcp/get_wall_details/".format(base_url),
                        "description": "Get comprehensive information about selected wall elements",
                        "mcp_example": "await get_wall_details()",
                        "http_example": "GET http://localhost:48884/revit_mcp/get_wall_details/",
                        "request_body": None
                    },
                    
                    "create_wall_layout": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_wall_layout/",
                        "http_url": "{}/revit_mcp/create_wall_layout/".format(base_url),
                        "description": "Create multiple walls in a layout pattern",
                        "mcp_example": """await create_wall_layout(
                            level_name="Level 1",
                            wall_configs=[
                                {"curve_points": [{"x": 0, "y": 0, "z": 0}, {"x": 5000, "y": 0, "z": 0}]}
                            ]
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_wall_layout/
Content-Type: application/json

{
    "level_name": "Level 1",
    "wall_configs": [
        {"curve_points": [{"x": 0, "y": 0, "z": 0}, {"x": 5000, "y": 0, "z": 0}]}
    ]
}""",
                        "request_body": {
                            "level_name": "string (required)",
                            "wall_configs": "array (required)",
                            "layout_type": "string (optional)",
                            "wall_type_name": "string (optional)",
                            "naming_pattern": "string (optional)"
                        }
                    },
                    
                    # Pipe Management Tools
                    "create_or_edit_multiple_pipes": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/create_or_edit_multiple_pipes/",
                        "http_url": "{}/revit_mcp/create_or_edit_multiple_pipes/".format(base_url),
                        "description": "Create or edit multiple pipes using a list of pipe configurations",
                        "mcp_example": """await create_or_edit_multiple_pipes(
                            pipe_configs=[
                                {
                                    "start_point": {"x": 0, "y": 0, "z": 3000},
                                    "end_point": {"x": 5000, "y": 0, "z": 3000},
                                    "inner_diameter": 100.0,
                                    "outer_diameter": 110.0,
                                    "material": "Steel"
                                }
                            ]
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/create_or_edit_multiple_pipes/
Content-Type: application/json

{
    "pipe_configs": [
        {
            "start_point": {"x": 0, "y": 0, "z": 3000},
            "end_point": {"x": 5000, "y": 0, "z": 3000},
            "inner_diameter": 100.0,
            "outer_diameter": 110.0,
            "material": "Steel"
        }
    ]
}""",
                        "request_body": {
                            "pipe_configs": "array (required) - Array of pipe configurations",
                            "naming_pattern": "string (optional)",
                            "system_type_name": "string (optional)",
                            "pipe_type_name": "string (optional)"
                        }
                    },
                    
                    # ATF Tools
                    "get_component_instances_from_urn": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/get_component_instances_from_urn/",
                        "http_url": "{}/revit_mcp/get_component_instances_from_urn/".format(base_url),
                        "description": "Get all component instances from a particular URN using ATF InteropModel",
                        "mcp_example": """await get_component_instances_from_urn(
                            urn="urn:adsk.wipstg:dm.lineage:FQVbQQouTiKcK27xRsECPg"
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/get_component_instances_from_urn/
Content-Type: application/json

{
    "urn": "urn:adsk.wipstg:dm.lineage:FQVbQQouTiKcK27xRsECPg"
}""",
                        "request_body": {
                            "urn": "string (required) - The URN to get instances from"
                        }
                    },
                    
                    "construct_exchange_url": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/construct_exchange_url/",
                        "http_url": "{}/revit_mcp/construct_exchange_url/".format(base_url),
                        "description": "Construct exchange URL from URN/exchange ID",
                        "mcp_example": """await construct_exchange_url(
                            exchange_id="urn:adsk.wipstg:dm.lineage:FQVbQQouTiKcK27xRsECPg"
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/construct_exchange_url/
Content-Type: application/json

{
    "exchange_id": "urn:adsk.wipstg:dm.lineage:FQVbQQouTiKcK27xRsECPg"
}""",
                        "request_body": {
                            "exchange_id": "string (required)",
                            "base_url": "string (optional)"
                        }
                    },
                    
                    "test_atf_integration": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/test_atf_integration/",
                        "http_url": "{}/revit_mcp/test_atf_integration/".format(base_url),
                        "description": "Test ATF.XLayer integration and return status information",
                        "mcp_example": "await test_atf_integration()",
                        "http_example": "GET http://localhost:48884/revit_mcp/test_atf_integration/",
                        "request_body": None
                    },
                    
                    # Geometry Tools
                    "check_points_in_bounding_box": {
                        "http_method": "POST",
                        "http_endpoint": "/revit_mcp/check_points_in_bounding_box/",
                        "http_url": "{}/revit_mcp/check_points_in_bounding_box/".format(base_url),
                        "description": "Check if multiple start and end points are inside the bounding box of a selected Revit element",
                        "mcp_example": """await check_points_in_bounding_box(
                            point_pairs=[
                                {
                                    "start_point": {"x": 1000.0, "y": 2000.0, "z": 3000.0},
                                    "end_point": {"x": 1500.0, "y": 2500.0, "z": 3500.0}
                                }
                            ]
                        )""",
                        "http_example": """POST http://localhost:48884/revit_mcp/check_points_in_bounding_box/
Content-Type: application/json

{
    "point_pairs": [
        {
            "start_point": {"x": 1000.0, "y": 2000.0, "z": 3000.0},
            "end_point": {"x": 1500.0, "y": 2500.0, "z": 3500.0}
        }
    ]
}""",
                        "request_body": {
                            "point_pairs": "array (required) - List of point pairs to check"
                        }
                    },
                    
                    # API Mapping Tools
                    "get_mcp_to_http_mapping": {
                        "http_method": "GET",
                        "http_endpoint": "/revit_mcp/mcp_to_http_mapping/",
                        "http_url": "{}/revit_mcp/mcp_to_http_mapping/".format(base_url),
                        "description": "Provides comprehensive mapping between MCP tools and HTTP API routes",
                        "mcp_example": "await get_mcp_to_http_mapping()",
                        "http_example": "GET http://localhost:48884/revit_mcp/mcp_to_http_mapping/",
                        "request_body": None
                    }
                },
                
                "workflow_examples": [
                    {
                        "name": "Floor Transfer Workflow",
                        "description": "Get floor from Revit and create in Tekla",
                        "steps": [
                            {
                                "step": 1,
                                "description": "Get selected floor details from Revit",
                                "mcp": "await get_floor_details()",
                                "http": "GET http://localhost:48884/revit_mcp/floor_details/"
                            },
                            {
                                "step": 2,
                                "description": "Process boundary curves and extract contour points",
                                "code": "# Extract contour points from boundary curves"
                            },
                            {
                                "step": 3,
                                "description": "Create slab in Tekla using processed data",
                                "tekla_mcp": "await create_tekla_slab(slab_config)"
                            }
                        ]
                    },
                    {
                        "name": "Model Analysis Workflow", 
                        "description": "Analyze and color-code elements",
                        "steps": [
                            {
                                "step": 1,
                                "description": "Get model information",
                                "mcp": "await get_revit_model_info()",
                                "http": "GET http://localhost:48884/revit_mcp/model_info/"
                            },
                            {
                                "step": 2,
                                "description": "List available parameters for walls",
                                "mcp": "await list_category_parameters(category_name='Walls')",
                                "http": "GET http://localhost:48884/revit_mcp/category_parameters/?category_name=Walls"
                            },
                            {
                                "step": 3,
                                "description": "Color walls by type",
                                "mcp": "await color_splash(category_name='Walls', parameter_name='Type Name')",
                                "http": """POST http://localhost:48884/revit_mcp/color_splash/
{
    "category_name": "Walls",
    "parameter_name": "Type Name"
}"""
                            }
                        ]
                    },
                    {
                        "name": "Structural Grid and Column Layout Workflow",
                        "description": "Create a structural grid system and place columns at intersections",
                        "steps": [
                            {
                                "step": 1,
                                "description": "Create a grid system",
                                "mcp": "await create_grid_system(linear_grids=[...])",
                                "http": "POST http://localhost:48884/revit_mcp/create_grid_system/"
                            },
                            {
                                "step": 2,
                                "description": "Find grid intersections",
                                "mcp": "await find_grid_intersections()",
                                "http": "POST http://localhost:48884/revit_mcp/find_grid_intersections/"
                            },
                            {
                                "step": 3,
                                "description": "Create columns at all intersections",
                                "mcp": "await create_columns_at_grid_intersections(...)",
                                "http": "POST http://localhost:48884/revit_mcp/create_columns_at_grid_intersections/"
                            }
                        ]
                    },
                    {
                        "name": "Structural Framing Workflow",
                        "description": "Create beams and analyze their properties",
                        "steps": [
                            {
                                "step": 1,
                                "description": "Create multiple beams in a layout",
                                "mcp": "await create_beam_layout(level_name='Level 1', beam_configs=[...])",
                                "http": "POST http://localhost:48884/revit_mcp/create_beam_layout/"
                            },
                            {
                                "step": 2,
                                "description": "Get detailed beam information",
                                "mcp": "await get_beam_details()",
                                "http": "GET http://localhost:48884/revit_mcp/get_beam_details/"
                            },
                            {
                                "step": 3,
                                "description": "Query specific beam properties",
                                "mcp": "await query_beam(element_id='123456')",
                                "http": "GET http://localhost:48884/revit_mcp/query_beam/?element_id=123456"
                            }
                        ]
                    },
                    {
                        "name": "MEP Pipe Layout Workflow",
                        "description": "Create multiple pipes for MEP systems",
                        "steps": [
                            {
                                "step": 1,
                                "description": "Create multiple pipes with configurations",
                                "mcp": "await create_or_edit_multiple_pipes(pipe_configs=[...])",
                                "http": "POST http://localhost:48884/revit_mcp/create_or_edit_multiple_pipes/"
                            },
                            {
                                "step": 2,
                                "description": "Check pipe geometry against building elements",
                                "mcp": "await check_points_in_bounding_box(point_pairs=[...])",
                                "http": "POST http://localhost:48884/revit_mcp/check_points_in_bounding_box/"
                            }
                        ]
                    },
                    {
                        "name": "ATF Integration Workflow",
                        "description": "Work with ATF component models",
                        "steps": [
                            {
                                "step": 1,
                                "description": "Test ATF integration",
                                "mcp": "await test_atf_integration()",
                                "http": "GET http://localhost:48884/revit_mcp/test_atf_integration/"
                            },
                            {
                                "step": 2,
                                "description": "Construct exchange URL",
                                "mcp": "await construct_exchange_url(exchange_id='urn:...')",
                                "http": "POST http://localhost:48884/revit_mcp/construct_exchange_url/"
                            },
                            {
                                "step": 3,
                                "description": "Get component instances from URN",
                                "mcp": "await get_component_instances_from_urn(urn='urn:...')",
                                "http": "POST http://localhost:48884/revit_mcp/get_component_instances_from_urn/"
                            }
                        ]
                    }
                ],
                
                "common_patterns": {
                    "authentication": "No authentication required for local connections",
                    "content_type": "application/json for POST requests",
                    "error_handling": "HTTP status codes indicate success/failure",
                    "coordinate_system": "All coordinates in millimeters unless specified",
                    "response_format": "JSON responses with data/error structure"
                },
                
                "python_http_example": '''
import requests
import json

# Example: Get floor details
response = requests.get("http://localhost:48884/revit_mcp/floor_details/")
floor_data = response.json()

# Example: Create a floor
floor_config = {
    "level_name": "Level 1",
    "boundary_curves": [
        {"type": "Line", "start_point": {"x": 0, "y": 0, "z": 0}, "end_point": {"x": 5000, "y": 0, "z": 0}},
        {"type": "Line", "start_point": {"x": 5000, "y": 0, "z": 0}, "end_point": {"x": 5000, "y": 3000, "z": 0}},
        {"type": "Line", "start_point": {"x": 5000, "y": 3000, "z": 0}, "end_point": {"x": 0, "y": 3000, "z": 0}},
        {"type": "Line", "start_point": {"x": 0, "y": 3000, "z": 0}, "end_point": {"x": 0, "y": 0, "z": 0}}
    ],
    "thickness": 200.0
}

response = requests.post(
    "http://localhost:48884/revit_mcp/create_or_edit_floor/",
    headers={"Content-Type": "application/json"},
    data=json.dumps(floor_config)
)
result = response.json()
'''
            }
            
            return routes.make_response(data=mapping_data, status=200)
            
        except Exception as e:
            logger.error("Failed to generate MCP to HTTP mapping: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Failed to generate mapping: {}".format(str(e))},
                status=500,
            )