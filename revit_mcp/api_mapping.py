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
    def get_mcp_to_http_mapping():
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
                "last_updated": "2024-12-19",
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