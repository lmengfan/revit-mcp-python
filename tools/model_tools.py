# -*- coding: utf-8 -*-
"""Model structure and hierarchy tools"""

from mcp.server.fastmcp import Context
from .utils import format_response


def register_model_tools(mcp, revit_get):
    """Register model structure tools"""

    @mcp.tool()
    async def list_levels(ctx: Context = None) -> str:
        """Get a list of all levels in the current Revit model"""
        response = await revit_get("/list_levels/", ctx)
        return format_response(response)

    @mcp.tool()
    async def get_selected_elements(ctx: Context = None) -> str:
        """
        Get information about currently selected elements in Revit
        
        Returns detailed information about each selected element including:
        - Element ID, name, and type
        - Category and category ID
        - Level information (if applicable)
        - Location information (point or curve)
        - Key parameters (Mark, Comments, Type Name, Family, etc.)
        - Family and type information for family instances
        - Summary statistics grouped by category
        
        This is useful for analyzing selected elements, getting their properties,
        and understanding their relationships within the model.
        """
        if ctx:
            ctx.info("Getting information about selected elements...")
        response = await revit_get("/selected_elements/", ctx)
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
            ctx.info("Getting detailed information about selected floor elements...")
        response = await revit_get("/floor_details/", ctx)
        return format_response(response)
