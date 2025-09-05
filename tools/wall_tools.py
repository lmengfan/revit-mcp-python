# -*- coding: utf-8 -*-
"""
MCP Tools for Wall Management

This module provides MCP tools for comprehensive wall management in Revit.
It includes tools for creating, editing, querying, and analyzing walls with
full parametric control and detailed type property extraction.

Key Features:
- Create and edit walls with comprehensive control
- Place walls along curves, between points, or as rectangular enclosures
- Query wall properties and extract detailed type information
- Support for various wall types (basic, curtain, stacked, etc.)
- Grid-based wall placement and automated layout generation
- Comprehensive type property extraction including layers, materials, and thermal data
- Unit conversion and proper metric output (mm, sq m, cu m)

Tools:
- create_or_edit_wall() - Create new or edit existing walls
- create_rectangular_wall() - Create rectangular wall enclosure
- query_wall() - Get basic wall information by ID
- get_wall_details() - Get comprehensive wall details from selection
- create_wall_layout() - Create multiple walls in layout patterns
"""

from mcp.server.fastmcp import Context
from typing import Dict, Any, List
from .utils import format_response


def register_wall_tools(mcp, revit_get, revit_post):
    """Register wall management tools with the MCP server."""

    @mcp.tool()
    async def create_or_edit_wall(
        level_name: str,
        curve_points: List[Dict[str, float]],
        element_id: str = None,
        wall_type_name: str = "Generic - 200mm",
        height: float = None,
        height_offset: float = 0.0,
        top_offset: float = 0.0,
        location_line: str = "Wall Centerline",
        structural: bool = False,
        properties: Dict[str, Any] = None,
        ctx: Context = None,
    ) -> str:
        """
        Create a new wall or edit an existing one in Revit

        This tool can operate in two modes:
        1. **Creation Mode** (when element_id is None): Creates a new wall
        2. **Edit Mode** (when element_id is provided): Modifies an existing wall

        Args:
            level_name: Name of the base level for the wall (required)
            curve_points: Array of points defining wall path, each with x, y, z keys (in mm)
            element_id: Element ID of existing wall to edit (optional, for edit mode)
            wall_type_name: Name of the wall type to use (default: "Generic - 200mm")
            height: Wall height in millimeters (optional, uses level height if not specified)
            height_offset: Base offset from level in millimeters (default: 0.0)
            top_offset: Top offset in millimeters (default: 0.0)
            location_line: Wall location line - "Wall Centerline", "Finish Face: Exterior", 
                          "Finish Face: Interior", "Core Centerline", "Core Face: Exterior", 
                          "Core Face: Interior" (default: "Wall Centerline")
            structural: Whether the wall is structural (default: False)
            properties: Additional parameters to set (optional):
                {"Mark": "W1", "Comments": "Interior wall", "Room Bounding": True, etc.}
            ctx: MCP context for logging

        Returns:
            Success message with wall details or error information

        Examples:
            # Create a simple interior wall
            create_or_edit_wall(
                level_name="Level 1",
                curve_points=[
                    {"x": 0, "y": 0, "z": 0},
                    {"x": 5000, "y": 0, "z": 0}
                ],
                wall_type_name="Generic - 200mm",
                height=3000.0,
                properties={"Mark": "W1", "Comments": "Interior partition"}
            )
            
            # Edit an existing wall
            create_or_edit_wall(
                element_id="123456",
                level_name="Level 1", 
                curve_points=[
                    {"x": 0, "y": 0, "z": 0},
                    {"x": 6000, "y": 0, "z": 0}
                ],
                wall_type_name="Generic - 300mm",
                height=3500.0
            )
            
            # Create structural exterior wall
            create_or_edit_wall(
                level_name="Level 1",
                curve_points=[
                    {"x": 0, "y": 0, "z": 0},
                    {"x": 10000, "y": 0, "z": 0}
                ],
                wall_type_name="Exterior - Brick and CMU",
                height=3000.0,
                location_line="Finish Face: Exterior",
                structural=True,
                properties={"Mark": "EW1", "Comments": "Load bearing exterior wall"}
            )
        """
        try:
            if ctx:
                ctx.info("Creating/editing wall...")

            # Prepare request data
            request_data = {
                "level_name": level_name,
                "curve_points": curve_points,
                "wall_type_name": wall_type_name,
                "height_offset": height_offset,
                "top_offset": top_offset,
                "location_line": location_line,
                "structural": structural,
                "properties": properties or {}
            }
            
            # Add optional parameters
            if element_id:
                request_data["element_id"] = element_id
            if height is not None:
                request_data["height"] = height

            response = await revit_post("/create_or_edit_wall/", request_data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to create/edit wall: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def create_rectangular_wall(
        level_name: str,
        origin: Dict[str, float],
        width: float,
        length: float,
        wall_type_name: str = "Generic - 200mm",
        height: float = None,
        create_as_single_wall: bool = False,
        properties: Dict[str, Any] = None,
        ctx: Context = None,
    ) -> str:
        """
        Create a rectangular wall enclosure

        This is a convenience tool that creates a rectangular room or enclosure by 
        specifying dimensions and a corner point. Can create either as a single 
        wall element or as four separate walls.

        Args:
            level_name: Name of the base level for the walls (required)
            origin: Corner point coordinates as dict with x, y, z keys (in mm)
            width: Width of the rectangle in millimeters (X direction)
            length: Length of the rectangle in millimeters (Y direction)
            wall_type_name: Name of the wall type to use (default: "Generic - 200mm")
            height: Wall height in millimeters (optional, uses level height if not specified)
            create_as_single_wall: Create as single wall element vs 4 separate walls (default: False)
            properties: Additional parameters to set (optional)
            ctx: MCP context for logging

        Returns:
            Success message with wall details or error information

        Examples:
            # Create a simple rectangular room (4 separate walls)
            create_rectangular_wall(
                level_name="Level 1",
                origin={"x": 0, "y": 0, "z": 0},
                width=5000.0,
                length=3000.0,
                wall_type_name="Generic - 200mm",
                height=3000.0,
                properties={"Mark": "ROOM1"}
            )
            
            # Create as single wall element
            create_rectangular_wall(
                level_name="Level 1",
                origin={"x": 2000, "y": 1000, "z": 0},
                width=4000.0,
                length=4000.0,
                wall_type_name="Generic - 150mm",
                height=2700.0,
                create_as_single_wall=True,
                properties={"Mark": "ENCLOSURE", "Comments": "Equipment enclosure"}
            )
        """
        try:
            if ctx:
                ctx.info("Creating rectangular wall enclosure...")

            # Prepare request data
            request_data = {
                "level_name": level_name,
                "origin": origin,
                "width": width,
                "length": length,
                "wall_type_name": wall_type_name,
                "create_as_single_wall": create_as_single_wall,
                "properties": properties or {}
            }
            
            # Add optional parameters
            if height is not None:
                request_data["height"] = height

            response = await revit_post("/create_rectangular_wall/", request_data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to create rectangular wall: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def query_wall(element_id: str, ctx: Context = None) -> str:
        """
        Query basic information about a wall by element ID

        This tool retrieves essential information about an existing wall including
        its configuration, location, type, and key properties. The returned data
        can be used for inspection, copying, or modification workflows.

        Args:
            element_id: The element ID of the wall to query (required)
            ctx: MCP context for logging

        Returns:
            Wall configuration and properties or error message

        Response includes:
            - message: Success/error message
            - wall_config: Complete wall configuration including:
                - element_id: Wall element ID
                - name: Wall name/mark
                - wall_type_name: Wall type name (e.g., "Generic - 200mm")
                - curve_points: Start/end coordinates in mm
                - length: Wall length in mm
                - level_name: Base level name
                - height: Wall height in mm
                - structural: Is structural wall
                - location_line: Wall location line setting
                - properties: Additional parameters

        This is useful for getting wall properties, understanding configurations,
        and preparing data for wall copying or modification operations.

        Examples:
            # Query a specific wall
            result = query_wall("123456")
            # Returns detailed wall configuration
            
            # Use for copying wall configuration
            original = query_wall("123456")
            # Then use the config to create similar wall
        """
        try:
            if ctx:
                ctx.info("Querying wall with ID: {}".format(element_id))

            response = await revit_get("/query_wall/?element_id={}".format(element_id), ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to query wall: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def get_wall_details(ctx: Context = None) -> str:
        """
        Get comprehensive information about selected wall elements in Revit

        Returns detailed information about each selected wall including:
        - Wall ID, name, and type information
        - Comprehensive wall type properties with detailed breakdown:
            - Layer composition (materials, thicknesses, functions)
            - Material properties for each layer (thermal, structural, physical)
            - Total wall thickness and structure information
            - Thermal properties (U-value, R-value, thermal mass, etc.)
            - Identity data (manufacturer, model, cost, fire rating)
            - Additional custom parameters
        - Location information (start/end points, length, direction, midpoint)
        - Level information (base/top levels, elevations) and height/offset data
        - Structural properties and location line settings
        - Key parameters (Mark, Comments, Room Bounding, Area, Volume, etc.)
        - Bounding box dimensions and positioning

        All measurements are converted to metric units (mm for lengths, sq m for areas,
        cu m for volumes, etc.).

        Args:
            ctx: MCP context for logging

        Returns:
            Detailed wall information or error message

        Response includes:
            - message: Success/error message
            - selected_count: Total number of selected elements
            - walls_found: Number of wall elements found
            - walls: Array of detailed wall information with:
                - Basic info (ID, name, wall type)
                - Comprehensive type_properties:
                    - layers: Layer-by-layer breakdown with materials and properties
                    - structure: Overall wall structure information
                    - thermal: Thermal performance properties
                    - identity: Manufacturer data, cost, ratings
                    - additional_parameters: Custom type parameters
                - location: Start/end points, length, direction, midpoint
                - level information: Base/top levels, elevations, offsets
                - structural_properties: Structural flag, location line
                - parameters: Instance parameters (Mark, Comments, Area, Volume, etc.)
                - bounding_box: Element bounds

        This is useful for analyzing selected walls, getting their comprehensive properties,
        understanding their construction and thermal characteristics, and extracting data 
        for analysis, energy modeling, documentation, or export to other systems.

        Examples:
            # Select some walls in Revit, then call:
            result = get_wall_details()
            # Returns comprehensive information about all selected walls
            
            # Use for energy analysis data extraction
            wall_data = get_wall_details()
            # Extract layer compositions, U-values, etc.
        """
        try:
            if ctx:
                ctx.info("Getting detailed information about selected walls...")

            response = await revit_get("/get_wall_details/", ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to get wall details: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def create_wall_layout(
        level_name: str,
        wall_configs: List[Dict[str, Any]],
        layout_type: str = "custom",
        wall_type_name: str = "Generic - 200mm",
        height: float = None,
        naming_pattern: str = "W{}",
        ctx: Context = None,
    ) -> str:
        """
        Create multiple walls in a layout pattern

        This tool allows you to create multiple walls at once using different layout strategies.
        It's useful for creating wall systems, building layouts, or any pattern of multiple walls.

        Args:
            level_name: Name of the base level for all walls (required)
            wall_configs: Array of wall configurations, each containing:
                - curve_points: Array of points defining wall path [{"x": 0, "y": 0, "z": 0}, ...]
                - wall_type_name: Wall type (optional, uses default)
                - height: Wall height in mm (optional, uses default)
                - mark: Wall mark (optional, uses naming_pattern)
                - properties: Additional parameters (optional)
            layout_type: Layout strategy - "grid", "rectangular", or "custom" (default: "custom")
            wall_type_name: Default wall type for all walls (default: "Generic - 200mm")
            height: Default wall height in millimeters (optional)
            naming_pattern: Pattern for auto-naming walls with {} placeholder (default: "W{}")
            ctx: MCP context for logging

        Returns:
            Success message with created wall details or error information

        Response includes:
            - message: Summary of creation results
            - created_count: Number of successfully created walls
            - requested_count: Total number of walls requested
            - walls: Array of created wall details

        Examples:
            # Create a simple wall layout
            create_wall_layout(
                level_name="Level 1",
                wall_configs=[
                    {
                        "curve_points": [
                            {"x": 0, "y": 0, "z": 0},
                            {"x": 5000, "y": 0, "z": 0}
                        ],
                        "wall_type_name": "Generic - 200mm"
                    },
                    {
                        "curve_points": [
                            {"x": 0, "y": 0, "z": 0},
                            {"x": 0, "y": 3000, "z": 0}
                        ],
                        "wall_type_name": "Generic - 200mm"
                    }
                ],
                height=3000.0,
                naming_pattern="W{}"
            )
            
            # Create mixed wall types layout
            create_wall_layout(
                level_name="Level 1",
                wall_configs=[
                    {
                        "curve_points": [
                            {"x": 0, "y": 0, "z": 0},
                            {"x": 10000, "y": 0, "z": 0}
                        ],
                        "wall_type_name": "Exterior - Brick and CMU",
                        "height": 3500.0,
                        "mark": "EW1",
                        "properties": {
                            "Comments": "Exterior load bearing wall",
                            "structural": True
                        }
                    },
                    {
                        "curve_points": [
                            {"x": 2000, "y": 0, "z": 0},
                            {"x": 2000, "y": 8000, "z": 0}
                        ],
                        "wall_type_name": "Generic - 150mm",
                        "height": 3000.0,
                        "mark": "IW1",
                        "properties": {"Comments": "Interior partition"}
                    }
                ],
                layout_type="custom"
            )
        """
        try:
            if ctx:
                ctx.info("Creating wall layout with {} walls...".format(len(wall_configs)))

            # Prepare request data
            request_data = {
                "level_name": level_name,
                "wall_configs": wall_configs,
                "layout_type": layout_type,
                "wall_type_name": wall_type_name,
                "naming_pattern": naming_pattern
            }
            
            # Add optional parameters
            if height is not None:
                request_data["height"] = height

            response = await revit_post("/create_wall_layout/", request_data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to create wall layout: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg 