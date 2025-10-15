# -*- coding: utf-8 -*-
"""
MCP Tools for Structural Beam Management

This module provides MCP tools for comprehensive structural framing (beam) management
in Revit. It includes tools for creating, editing, querying, and analyzing beams with
full parametric control and detailed type property extraction.

Key Features:
- Create and edit structural beams with comprehensive control
- Place beams between points, along curves, or in layout patterns
- Query beam properties and extract detailed type information
- Support for various beam families (steel, concrete, timber, etc.)
- Grid-based beam placement and automated layout generation
- Comprehensive type property extraction including dimensions, materials, and structural data
- Unit conversion and proper metric output (mm, MPa, kg/m³)

Tools:
- create_or_edit_beam() - Create new or edit existing structural beams
- place_beam_between_points() - Place beam between two specific points
- query_beam() - Get basic beam information by ID
- get_beam_details() - Get comprehensive beam details from selection
- create_beam_layout() - Create multiple beams in layout patterns
- place_beams_on_grids() - Place beams along grid lines (if grid functionality available)
"""

from mcp.server.fastmcp import Context
from typing import Dict, Any, List
from .utils import format_response


def register_beam_tools(mcp, revit_get, revit_post):
    """Register beam management tools with the MCP server."""

    @mcp.tool()
    async def create_or_edit_beam(
        level_name: str,
        start_point: dict,
        end_point: dict,
        element_id: str = None,
        family_name: str = "W-Wide Flange",
        type_name: str = None,
        structural_usage: str = "Beam",
        height_offset: float = 0.0,
        rotation: float = 0.0,
        properties: dict = None,
        ctx: Context = None
    ) -> str:
        """
        Create a new structural beam or edit an existing one in Revit

        This tool can operate in two modes:
        1. **Creation Mode** (when element_id is None): Creates a new structural beam
        2. **Edit Mode** (when element_id is provided): Modifies an existing beam

        Args:
            level_name: Name of the target level for the beam (required)
            start_point: Start point coordinates as dict with x, y, z keys (in mm)
            end_point: End point coordinates as dict with x, y, z keys (in mm)
            element_id: Element ID of existing beam to edit (optional, for edit mode)
            family_name: Name of the beam family to use (default: "W-Wide Flange")
            type_name: Name of the beam type within the family (optional)
            structural_usage: Structural usage - "Beam", "Girder", "Joist", or "Other" (default: "Beam")
            height_offset: Offset from level in millimeters (default: 0.0)
            rotation: Rotation angle in degrees (default: 0.0)
            properties: Additional parameters to set (optional):
                {"Mark": "B1", "Comments": "Steel beam", etc.}
            ctx: MCP context for logging

        Returns:
            Success message with beam details or error information

        Examples:
            # Create a new steel beam
            create_or_edit_beam(
                level_name="Level 1",
                start_point={"x": 0, "y": 0, "z": 3000},
                end_point={"x": 5000, "y": 0, "z": 3000},
                family_name="W-Wide Flange",
                type_name="W12X26",
                structural_usage="Beam",
                properties={"Mark": "B1", "Comments": "Main beam"}
            )
            
            # Edit an existing beam
            create_or_edit_beam(
                element_id="123456",
                level_name="Level 2", 
                start_point={"x": 1000, "y": 0, "z": 3000},
                end_point={"x": 6000, "y": 0, "z": 3000},
                type_name="W14X30"
            )
            
            # Create concrete beam
            create_or_edit_beam(
                level_name="Level 1",
                start_point={"x": 0, "y": 0, "z": 3000},
                end_point={"x": 8000, "y": 0, "z": 3000},
                family_name="Concrete-Rectangular-Beam",
                type_name="300x600mm",
                structural_usage="Girder",
                height_offset=100.0
            )
        """
        try:
            if ctx:
                await ctx.info("Creating/editing structural beam...")

            # Prepare request data
            request_data = {
                "level_name": level_name,
                "start_point": start_point,
                "end_point": end_point,
                "family_name": family_name,
                "structural_usage": structural_usage,
                "height_offset": height_offset,
                "rotation": rotation,
                "properties": properties or {}
            }
            
            # Add optional parameters
            if element_id:
                request_data["element_id"] = element_id
            if type_name:
                request_data["type_name"] = type_name

            response = await revit_post("/create_or_edit_beam/", request_data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to create/edit beam: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg


    @mcp.tool()
    async def place_beam_between_points(
        level_name: str,
        point1: dict,
        point2: dict,
        family_name: str = "W-Wide Flange",
        type_name: str = None,
        mark: str = None,
        structural_usage: str = "Beam",
        ctx: Context = None
    ) -> str:
        """
        Place a structural beam between two specific points

        This is a convenience tool that creates a beam by specifying two points directly.
        It's useful for quick beam placement when you know the exact coordinates.

        Args:
            level_name: Name of the target level for the beam (required)
            point1: First point coordinates as dict with x, y, z keys (in mm)
            point2: Second point coordinates as dict with x, y, z keys (in mm)
            family_name: Name of the beam family to use (default: "W-Wide Flange")
            type_name: Name of the beam type within the family (optional)
            mark: Beam mark/identifier (optional)
            structural_usage: Structural usage - "Beam", "Girder", "Joist", or "Other" (default: "Beam")
            ctx: MCP context for logging

        Returns:
            Success message with beam details or error information

        Examples:
            # Place a simple steel beam
            place_beam_between_points(
                level_name="Level 1",
                point1={"x": 0, "y": 0, "z": 3000},
                point2={"x": 5000, "y": 0, "z": 3000},
                family_name="W-Wide Flange",
                type_name="W12X26",
                mark="B1"
            )
            
            # Place a girder between two points
            place_beam_between_points(
                level_name="Level 2",
                point1={"x": 2000, "y": 1000, "z": 6000},
                point2={"x": 8000, "y": 1000, "z": 6000},
                family_name="W-Wide Flange",
                type_name="W21X44",
                mark="G1",
                structural_usage="Girder"
            )
        """
        try:
            if ctx:
                await ctx.info("Placing beam between two points...")

            # Prepare request data
            request_data = {
                "level_name": level_name,
                "point1": point1,
                "point2": point2,
                "family_name": family_name,
                "structural_usage": structural_usage
            }
            
            # Add optional parameters
            if type_name:
                request_data["type_name"] = type_name
            if mark:
                request_data["mark"] = mark

            response = await revit_post("/place_beam_between_points/", request_data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to place beam between points: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg


    @mcp.tool()
    async def query_beam(element_id: str, ctx: Context = None) -> str:
        """
        Query basic information about a structural beam by element ID

        This tool retrieves essential information about an existing beam including
        its configuration, location, type, and key properties. The returned data
        can be used for inspection, copying, or modification workflows.

        Args:
            element_id: The element ID of the beam to query (required)
            ctx: MCP context for logging

        Returns:
            Beam configuration and properties or error message

        Response includes:
            - message: Success/error message
            - beam_config: Complete beam configuration including:
                - element_id: Beam element ID
                - name: Beam name/mark
                - family_name: Family name (e.g., "W-Wide Flange")
                - type_name: Type name (e.g., "W12X26")
                - start_point/end_point: Coordinates in mm
                - length: Beam length in mm
                - level_name: Associated level
                - structural_usage: Usage type (Beam, Girder, etc.)
                - properties: Additional parameters

        This is useful for getting beam properties, understanding configurations,
        and preparing data for beam copying or modification operations.

        Examples:
            # Query a specific beam
            result = query_beam("123456")
            # Returns detailed beam configuration
            
            # Use for copying beam configuration
            original = query_beam("123456")
            # Then use the config to create similar beam
        """
        try:
            if ctx:
                await ctx.info("Querying beam with ID: {}".format(element_id))

            response = await revit_get("/query_beam/?element_id={}".format(element_id), ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to query beam: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg

    
    @mcp.tool()
    async def get_beam_details(ctx: Context = None) -> str:
        """
        Get comprehensive information about selected structural beam elements in Revit

        Returns detailed information about each selected beam including:
        - Beam ID, name, and type (family and type names)
        - Comprehensive type properties with detailed breakdown:
            - Dimensional properties (section dimensions, area, moments of inertia)
            - Material properties (structural material, strength values, modulus)
            - Structural properties (usage, analytical settings, extensions)
            - Identity data (manufacturer, model, cost, fire rating)
            - Additional custom parameters
        - Location information (start/end points, length, direction, midpoint)
        - Level information (name, ID, elevation) and height offsets
        - Structural usage and material assignments
        - Key parameters (Mark, Comments, Phasing, etc.)
        - Bounding box dimensions and positioning

        All measurements are converted to metric units (mm for lengths, MPa for stresses,
        kg/m³ for densities, etc.).

        Args:
            ctx: MCP context for logging

        Returns:
            Detailed beam information or error message

        Response includes:
            - message: Success/error message
            - selected_count: Total number of selected elements
            - beams_found: Number of beam elements found
            - beams: Array of detailed beam information with:
                - Basic info (ID, name, family, type)
                - Comprehensive type_properties:
                    - dimensions: Section properties (d, bf, tf, tw, area, Ix, Iy, etc.)
                    - materials: Material assignments with detailed properties
                    - structural: Structural usage, strength values, modulus
                    - identity: Manufacturer data, cost, ratings
                    - analytical: Analytical model settings, extensions
                    - additional_parameters: Custom family parameters
                - location: Start/end points, length, direction, midpoint
                - level: Level information and offsets
                - structural_properties: Usage and material data
                - parameters: Instance parameters
                - bounding_box: Element bounds

        This is useful for analyzing selected beams, getting their comprehensive properties,
        understanding their structural characteristics, and extracting data for analysis,
        documentation, or export to other systems.

        Examples:
            # Select some beams in Revit, then call:
            result = get_beam_details()
            # Returns comprehensive information about all selected beams
            
            # Use for structural analysis data extraction
            beam_data = get_beam_details()
            # Extract section properties, material data, etc.
        """
        try:
            if ctx:
                await ctx.info("Getting detailed information about selected beams...")

            response = await revit_get("/get_beam_details/", ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to get beam details: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg


    @mcp.tool()
    async def create_beam_layout(
        level_name: str,
        beam_configs: list,
        layout_type: str = "custom",
        family_name: str = "W-Wide Flange",
        structural_usage: str = "Beam",
        naming_pattern: str = "B{}",
        ctx: Context = None
    ) -> str:
        """
        Create multiple structural beams in a layout pattern

        This tool allows you to create multiple beams at once using different layout strategies.
        It's useful for creating beam systems, grids of beams, or any pattern of multiple beams.

        Args:
            level_name: Name of the target level for all beams (required)
            beam_configs: Array of beam configurations, each containing:
                - start_point: Start coordinates {"x": 0, "y": 0, "z": 3000}
                - end_point: End coordinates {"x": 5000, "y": 0, "z": 3000}
                - type_name: Beam type (optional, uses family default)
                - mark: Beam mark (optional, uses naming_pattern)
                - properties: Additional parameters (optional)
            layout_type: Layout strategy - "grid", "radial", or "custom" (default: "custom")
            family_name: Default beam family for all beams (default: "W-Wide Flange")
            structural_usage: Default structural usage for all beams (default: "Beam")
            naming_pattern: Pattern for auto-naming beams with {} placeholder (default: "B{}")
            ctx: MCP context for logging

        Returns:
            Success message with created beam details or error information

        Response includes:
            - message: Summary of creation results
            - created_count: Number of successfully created beams
            - requested_count: Total number of beams requested
            - beams: Array of created beam details

        Examples:
            # Create a simple beam layout
            create_beam_layout(
                level_name="Level 1",
                beam_configs=[
                    {
                        "start_point": {"x": 0, "y": 0, "z": 3000},
                        "end_point": {"x": 5000, "y": 0, "z": 3000},
                        "type_name": "W12X26"
                    },
                    {
                        "start_point": {"x": 0, "y": 2000, "z": 3000},
                        "end_point": {"x": 5000, "y": 2000, "z": 3000},
                        "type_name": "W12X26"
                    }
                ],
                family_name="W-Wide Flange",
                naming_pattern="B{}"
            )
            
            # Create mixed beam types layout
            create_beam_layout(
                level_name="Level 2",
                beam_configs=[
                    {
                        "start_point": {"x": 0, "y": 0, "z": 6000},
                        "end_point": {"x": 10000, "y": 0, "z": 6000},
                        "type_name": "W21X44",
                        "mark": "G1",
                        "properties": {"Comments": "Main girder"}
                    },
                    {
                        "start_point": {"x": 0, "y": 3000, "z": 6000},
                        "end_point": {"x": 10000, "y": 3000, "z": 6000},
                        "type_name": "W18X35",
                        "mark": "B1"
                    }
                ],
                layout_type="custom",
                structural_usage="Beam"
            )
        """
        try:
            if ctx:
                await ctx.info("Creating beam layout with {} beams...".format(len(beam_configs)))

            # Prepare request data
            request_data = {
                "level_name": level_name,
                "beam_configs": beam_configs,
                "layout_type": layout_type,
                "family_name": family_name,
                "structural_usage": structural_usage,
                "naming_pattern": naming_pattern
            }

            response = await revit_post("/create_beam_layout/", request_data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to create beam layout: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg 