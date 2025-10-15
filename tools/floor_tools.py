# -*- coding: utf-8 -*-
"""Floor tools for Revit MCP Server"""

from mcp.server.fastmcp import Context
from .utils import format_response


def register_floor_tools(mcp, revit_get, revit_post):
    """Register floor management tools"""

    @mcp.tool()
    async def create_or_edit_floor(
        level_name: str,
        boundary_curves: list,
        element_id: str = None,
        height_offset: float = 0.0,
        transformation: dict = None,
        thickness: float = None,
        floor_type_name: str = None,
        properties: dict = None,
        ctx: Context = None
    ) -> str:
        """
        Create a new floor or edit an existing floor in Revit.

        This tool can operate in two modes:
        1. **Creation Mode** (when element_id is None): Creates a new floor
        2. **Edit Mode** (when element_id is provided): Modifies an existing floor

        Args:
            level_name: Name of the target level for the floor (required)
            boundary_curves: Array of curve definitions defining the floor boundary (required)
                Each curve should be a dict with:
                - type: "Line", "Arc", or "Spline" 
                - start_point: {"x": float, "y": float, "z": float} (in mm)
                - end_point: {"x": float, "y": float, "z": float} (in mm)
                - For arcs: center: {"x": float, "y": float, "z": float} and radius: float
            element_id: Element ID of existing floor to edit (optional, for edit mode)
            height_offset: Offset from level in millimeters (default: 0.0)
            transformation: Optional transformation to apply to geometry:
                {
                    "origin": {"x": float, "y": float, "z": float},
                    "x_axis": {"x": float, "y": float, "z": float},
                    "y_axis": {"x": float, "y": float, "z": float},
                    "z_axis": {"x": float, "y": float, "z": float}
                }
            thickness: Floor thickness in millimeters (optional, mainly for new floors)
            floor_type_name: Name of the floor type to use (optional)
            properties: Additional parameters to set (optional):
                {"Mark": "F1", "Comments": "Created via MCP", etc.}
            ctx: MCP context for logging
            
        Returns:
            Success message with floor details or error information
            
        Examples:
            # Create a simple rectangular floor
            create_or_edit_floor(
                level_name="Level 1",
                boundary_curves=[
                    {"type": "Line", "start_point": {"x": 0, "y": 0, "z": 0}, "end_point": {"x": 5000, "y": 0, "z": 0}},
                    {"type": "Line", "start_point": {"x": 5000, "y": 0, "z": 0}, "end_point": {"x": 5000, "y": 3000, "z": 0}},
                    {"type": "Line", "start_point": {"x": 5000, "y": 3000, "z": 0}, "end_point": {"x": 0, "y": 3000, "z": 0}},
                    {"type": "Line", "start_point": {"x": 0, "y": 3000, "z": 0}, "end_point": {"x": 0, "y": 0, "z": 0}}
                ],
                height_offset=100.0,
                thickness=200.0,
                properties={"Mark": "F1", "Comments": "New floor"}
            )
            
            # Edit an existing floor
            create_or_edit_floor(
                element_id="123456",
                level_name="Level 2", 
                boundary_curves=[...],  # New boundary
                height_offset=50.0
            )
        """
        if ctx:
            operation = "Editing" if element_id else "Creating"
            await ctx.info("{} floor on level '{}'...".format(operation, level_name))

        # Prepare the request data
        data = {
            "level_name": level_name,
            "boundary_curves": boundary_curves,
            "height_offset": height_offset
        }
        
        if element_id:
            data["element_id"] = element_id
        if transformation:
            data["transformation"] = transformation
        if thickness:
            data["thickness"] = thickness
        if floor_type_name:
            data["floor_type_name"] = floor_type_name
        if properties:
            data["properties"] = properties

        response = await revit_post("/create_or_edit_floor/", data, ctx)
        return format_response(response)

    @mcp.tool()
    async def create_rectangular_floor(
        level_name: str,
        width: float,
        length: float,
        origin_x: float = 0.0,
        origin_y: float = 0.0,
        origin_z: float = 0.0,
        height_offset: float = 0.0,
        thickness: float = None,
        floor_type_name: str = None,
        properties: dict = None,
        ctx: Context = None
    ) -> str:
        """
        Create a rectangular floor with specified dimensions.

        This is a convenience tool that automatically generates the boundary curves
        for a rectangular floor based on width, length, and origin point.

        Args:
            level_name: Name of the target level for the floor (required)
            width: Floor width in millimeters (X direction)
            length: Floor length in millimeters (Y direction) 
            origin_x: X coordinate of the floor origin in millimeters (default: 0.0)
            origin_y: Y coordinate of the floor origin in millimeters (default: 0.0)
            origin_z: Z coordinate of the floor origin in millimeters (default: 0.0)
            height_offset: Offset from level in millimeters (default: 0.0)
            thickness: Floor thickness in millimeters (optional)
            floor_type_name: Name of the floor type to use (optional)
            properties: Additional parameters to set (optional)
            ctx: MCP context for logging
            
        Returns:
            Success message with floor details or error information
            
        Example:
            # Create a 5m x 3m rectangular floor
            create_rectangular_floor(
                level_name="Level 1",
                width=5000.0,
                length=3000.0,
                origin_x=1000.0,
                origin_y=500.0,
                height_offset=100.0,
                properties={"Mark": "F1"}
            )
        """
        if ctx:
            await ctx.info("Creating {}mm x {}mm rectangular floor on level '{}'...".format(
                width, length, level_name
            ))

        # Prepare the request data
        data = {
            "level_name": level_name,
            "width": width,
            "length": length,
            "origin_x": origin_x,
            "origin_y": origin_y,
            "origin_z": origin_z,
            "height_offset": height_offset
        }
        
        if thickness:
            data["thickness"] = thickness
        if floor_type_name:
            data["floor_type_name"] = floor_type_name
        if properties:
            data["properties"] = properties

        response = await revit_post("/create_rectangular_floor/", data, ctx)
        return format_response(response) 
        
    @mcp.tool()
    async def get_floor_details(ctx: Context = None) -> str:
        """
        Get comprehensive information about selected floor elements in Revit
        
        Returns detailed information about floor elements including:
        - Family Name and Type information (e.g., "Generic - 12\"", "Concrete on Metal Deck")
        - Thickness and material properties with layer-by-layer breakdown
        - Boundary curves and geometry points with coordinates in mm
        - Level information (name, ID, elevation) and height offset from level
        - Level elevation and absolute Z-coordinate positioning
        - Structural properties and construction details
        - All relevant parameters (Area, Volume, Perimeter, Structural flags, etc.)
        - Bounding box dimensions and positioning
        
        This tool specifically filters for floor elements from the current selection
        and provides comprehensive construction and geometric information needed
        for analysis, documentation, or export to other systems like Tekla.
        
        All measurements are converted to metric units (mm for lengths, sq m for areas).
        """
        if ctx:
            await ctx.info("Getting detailed information about selected floor elements...")
        response = await revit_get("/floor_details/", ctx)
        return format_response(response)