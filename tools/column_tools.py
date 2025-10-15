# -*- coding: utf-8 -*-
"""Structural column management tools for the MCP server."""

from mcp.server.fastmcp import Context
from typing import Dict, Any, List
from .utils import format_response


def register_column_tools(mcp, revit_get, revit_post):
    """Register structural column management tools with the MCP server."""

    @mcp.tool()
    async def create_or_edit_column(
        family_name: str,
        base_level: str,
        location: Dict[str, float],
        element_id: str = None,
        type_name: str = None,
        top_level: str = None,
        height: float = None,
        base_offset: float = 0.0,
        top_offset: float = 0.0,
        rotation: float = 0.0,
        structural_type: str = "Column",
        structural_usage: str = "Other",
        properties: Dict[str, Any] = None,
        ctx: Context = None,
    ) -> str:
        """
        Create a new structural column or edit an existing column in Revit.

        This tool can operate in two modes:
        1. **Creation Mode** (when element_id is None): Creates a new column
        2. **Edit Mode** (when element_id is provided): Modifies an existing column

        Args:
            family_name: Column family name (required, e.g., "Concrete-Rectangular-Column")
            base_level: Base level name (required, e.g., "Level 1")
            location: Column location {"x": 0, "y": 0, "z": 0} in mm (required)
            element_id: Element ID of existing column to edit (optional, for edit mode)
            type_name: Column type name (optional, e.g., "600 x 600mm")
            top_level: Top level name (optional, e.g., "Level 2")
            height: Column height in mm (optional, used if top_level not provided)
            base_offset: Offset from base level in mm (default: 0.0)
            top_offset: Offset from top level in mm (default: 0.0)
            rotation: Rotation angle in degrees (default: 0.0)
            structural_type: Structural type - "Column", "Beam", "Brace", "NonStructural" (default: "Column")
            structural_usage: Structural usage - "Other", "Girder", "Purlin", "Joist", "Kicker" (default: "Other")
            properties: Additional parameters {"Mark": "C1", "Comments": "Created via MCP"}
            ctx: MCP context for logging

        Returns:
            Success message with column details or error information

        Examples:
            # Create a new concrete column
            create_or_edit_column(
                family_name="Concrete-Rectangular-Column",
                type_name="600 x 600mm",
                base_level="Level 1",
                top_level="Level 2",
                location={"x": 5000, "y": 5000, "z": 0},
                base_offset=100,
                properties={"Mark": "C1", "Comments": "Main structural column"}
            )

            # Create a column with specific height
            create_or_edit_column(
                family_name="Steel-Wide_Flange-Column",
                type_name="W14X90",
                base_level="Level 1",
                height=3500,
                location={"x": 10000, "y": 8000, "z": 0},
                rotation=45.0,
                structural_usage="Other"
            )

            # Edit an existing column
            create_or_edit_column(
                element_id="123456",
                family_name="Concrete-Rectangular-Column",
                type_name="800 x 800mm",
                base_level="Level 1",
                top_level="Level 3",
                location={"x": 5000, "y": 5000, "z": 0}
            )
        """
        try:
            data = {
                "element_id": element_id,
                "family_name": family_name,
                "type_name": type_name,
                "location": location,
                "base_level": base_level,
                "top_level": top_level,
                "height": height,
                "base_offset": base_offset,
                "top_offset": top_offset,
                "rotation": rotation,
                "structural_type": structural_type,
                "structural_usage": structural_usage,
                "properties": properties or {}
            }

            if ctx:
                await ctx.info("Creating/editing {} column{}".format(
                    structural_type.lower(), " '{}'".format(type_name) if type_name else ""
                ))

            response = await revit_post("/create_or_edit_column/", data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to create/edit column: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def create_column_at_grid_intersection(
        family_name: str,
        base_level: str,
        intersection_point: Dict[str, float],
        type_name: str = None,
        top_level: str = None,
        height: float = None,
        base_offset: float = 0.0,
        top_offset: float = 0.0,
        structural_type: str = "Column",
        structural_usage: str = "Other",
        properties: Dict[str, Any] = None,
        ctx: Context = None,
    ) -> str:
        """
        Create a structural column at a specific grid intersection point.

        This is a convenience tool for placing columns at grid intersections,
        commonly used in structural design workflows.

        Args:
            family_name: Column family name (required)
            base_level: Base level name (required)
            intersection_point: Grid intersection point {"x": 1000, "y": 2000, "z": 0} in mm
            type_name: Column type name (optional)
            top_level: Top level name (optional)
            height: Column height in mm (optional, used if top_level not provided)
            base_offset: Offset from base level in mm (default: 0.0)
            top_offset: Offset from top level in mm (default: 0.0)
            structural_type: Structural type (default: "Column")
            structural_usage: Structural usage (default: "Other")
            properties: Additional parameters (optional)
            ctx: MCP context for logging

        Returns:
            Success message with column details or error information

        Example:
            # Place column at grid intersection
            create_column_at_grid_intersection(
                family_name="Concrete-Rectangular-Column",
                type_name="600 x 600mm",
                base_level="Level 1",
                top_level="Level 2",
                intersection_point={"x": 5000, "y": 8000, "z": 0},
                properties={"Mark": "C-A1"}
            )
        """
        return await create_or_edit_column(
            family_name=family_name,
            type_name=type_name,
            base_level=base_level,
            top_level=top_level,
            height=height,
            location=intersection_point,
            base_offset=base_offset,
            top_offset=top_offset,
            structural_type=structural_type,
            structural_usage=structural_usage,
            properties=properties,
            ctx=ctx
        )

    @mcp.tool()
    async def create_columns_at_grid_intersections(
        family_name: str,
        base_level: str,
        intersections: List[Dict[str, Any]],
        type_name: str = None,
        top_level: str = None,
        height: float = None,
        base_offset: float = 0.0,
        top_offset: float = 0.0,
        structural_type: str = "Column",
        structural_usage: str = "Other",
        mark_prefix: str = "C",
        ctx: Context = None,
    ) -> str:
        """
        Create multiple structural columns at grid intersection points.

        This tool creates columns at multiple grid intersections in a single operation,
        useful for structural layouts with regular grid systems.

        Args:
            family_name: Column family name (required)
            base_level: Base level name (required)
            intersections: List of intersection data from find_grid_intersections
            type_name: Column type name (optional)
            top_level: Top level name (optional)
            height: Column height in mm (optional)
            base_offset: Offset from base level in mm (default: 0.0)
            top_offset: Offset from top level in mm (default: 0.0)
            structural_type: Structural type (default: "Column")
            structural_usage: Structural usage (default: "Other")
            mark_prefix: Prefix for column marks (default: "C")
            ctx: MCP context for logging

        Returns:
            Summary of created columns or error information

        Example:
            # First find grid intersections
            intersections = find_grid_intersections()
            
            # Then create columns at all intersections
            create_columns_at_grid_intersections(
                family_name="Steel-Wide_Flange-Column",
                type_name="W14X90",
                base_level="Level 1",
                top_level="Level 2",
                intersections=intersections["intersections"],
                mark_prefix="C"
            )
        """
        try:
            created_columns = []
            failed_columns = []

            if ctx:
                await ctx.info("Creating columns at {} grid intersections".format(len(intersections)))

            for i, intersection in enumerate(intersections):
                try:
                    # Generate column mark
                    grid1_name = intersection.get("grid1_name", "")
                    grid2_name = intersection.get("grid2_name", "")
                    mark = "{}-{}{}".format(mark_prefix, grid1_name, grid2_name)
                    
                    # Get intersection point
                    intersection_point = intersection.get("intersection_point", {})
                    
                    if ctx:
                        await ctx.info("Creating column {}/{} at grid intersection {}-{}".format(
                            i + 1, len(intersections), grid1_name, grid2_name
                        ))

                    result = await create_or_edit_column(
                        family_name=family_name,
                        type_name=type_name,
                        base_level=base_level,
                        top_level=top_level,
                        height=height,
                        location=intersection_point,
                        base_offset=base_offset,
                        top_offset=top_offset,
                        structural_type=structural_type,
                        structural_usage=structural_usage,
                        properties={"Mark": mark},
                        ctx=ctx
                    )
                    
                    created_columns.append({
                        "mark": mark,
                        "grids": "{}-{}".format(grid1_name, grid2_name),
                        "location": intersection_point,
                        "result": result
                    })

                except Exception as e:
                    failed_columns.append({
                        "mark": "{}-{}{}".format(mark_prefix, 
                                               intersection.get("grid1_name", "?"), 
                                               intersection.get("grid2_name", "?")),
                        "error": str(e)
                    })

            # Prepare summary
            summary = "Column creation at grid intersections completed:\n"
            summary += "- Successfully created: {} columns\n".format(len(created_columns))
            if failed_columns:
                summary += "- Failed to create: {} columns\n".format(len(failed_columns))

            if created_columns:
                summary += "\nCreated columns:\n"
                for column in created_columns:
                    summary += "  - {} at grids {}\n".format(column["mark"], column["grids"])

            if failed_columns:
                summary += "\nFailed columns:\n"
                for column in failed_columns:
                    summary += "  - {}: {}\n".format(column["mark"], column["error"])

            return summary

        except Exception as e:
            error_msg = "Failed to create columns at grid intersections: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def query_column(
        element_id: str,
        ctx: Context = None,
    ) -> str:
        """
        Query an existing structural column by ID and return its configuration.

        This tool retrieves all properties of an existing column in Revit and returns
        them in a structured format that can be used for inspection, copying, or
        modification workflows.

        Args:
            element_id: The Revit element ID of the column to query (required)
            ctx: MCP context for logging

        Returns:
            Column configuration with all properties or error information

        Response includes:
            - element_id: Column element ID
            - name: Column name
            - family_name, type_name: Family and type information
            - location: Column location coordinates
            - base_level, top_level: Level information
            - base_offset, top_offset, height: Dimension information
            - structural_type, structural_usage: Structural properties
            - rotation: Column rotation angle

        Example:
            # Query existing column
            result = query_column("123456")
            # Use returned config to create similar column
        """
        try:
            data = {"element_id": element_id}

            if ctx:
                await ctx.info("Querying column with ID: {}".format(element_id))

            response = await revit_post("/query_column/", data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to query column: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def get_column_details(ctx: Context = None) -> str:
        """
        Get comprehensive information about selected structural column elements in Revit

        Returns detailed information about each selected column including:
        - Column ID, name, family, and type information
        - Location and geometry information (point or line-based)
        - Base and top level information with elevations
        - Offsets and height dimensions in mm
        - Structural properties (type, usage, material)
        - Cross-section properties and dimensions
        - Rotation and orientation information
        - Key parameters (Mark, Comments, Volume, etc.)
        - Bounding box dimensions and positioning
        - Slanted column detection

        All measurements are converted to metric units (mm for lengths, degrees for angles).

        Args:
            ctx: MCP context for logging

        Returns:
            Detailed column information or error message

        Response includes:
            - message: Success/error message
            - selected_count: Total number of selected elements
            - columns_found: Number of column elements found
            - columns: Array of detailed column information

        This is useful for analyzing selected columns, getting their properties,
        understanding their geometry and structural characteristics, and
        preparing data for structural analysis or documentation.

        Example:
            # Select some columns in Revit, then call:
            result = get_column_details()
            # Returns comprehensive information about all selected columns
        """
        try:
            if ctx:
                await ctx.info("Getting detailed information about selected columns...")

            response = await revit_get("/column_details/", ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to get column details: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def create_column_layout(
        family_name: str,
        base_level: str,
        grid_layout: Dict[str, Any],
        type_name: str = None,
        top_level: str = None,
        height: float = None,
        base_offset: float = 0.0,
        top_offset: float = 0.0,
        structural_type: str = "Column",
        structural_usage: str = "Other",
        skip_intersections: List[str] = None,
        ctx: Context = None,
    ) -> str:
        """
        Create a complete column layout based on a grid system.

        This tool creates columns at grid intersections with options to skip
        specific intersections and customize column properties.

        Args:
            family_name: Column family name (required)
            base_level: Base level name (required)
            grid_layout: Grid layout with intersection information
            type_name: Column type name (optional)
            top_level: Top level name (optional)
            height: Column height in mm (optional)
            base_offset: Offset from base level in mm (default: 0.0)
            top_offset: Offset from top level in mm (default: 0.0)
            structural_type: Structural type (default: "Column")
            structural_usage: Structural usage (default: "Other")
            skip_intersections: List of grid intersections to skip (e.g., ["A1", "B3"])
            ctx: MCP context for logging

        Returns:
            Summary of column layout creation

        Example:
            # Create column layout skipping some intersections
            create_column_layout(
                family_name="Concrete-Rectangular-Column",
                type_name="600 x 600mm",
                base_level="Level 1",
                top_level="Level 2",
                grid_layout=grid_intersections,
                skip_intersections=["A1", "C3"],  # Skip these intersections
                base_offset=50
            )
        """
        try:
            if ctx:
                await ctx.info("Creating column layout for grid system...")

            # Get intersections from grid layout
            intersections = grid_layout.get("intersections", [])
            if not intersections:
                return "No grid intersections found in the provided grid layout"

            # Filter out skipped intersections
            if skip_intersections:
                filtered_intersections = []
                for intersection in intersections:
                    grid1_name = intersection.get("grid1_name", "")
                    grid2_name = intersection.get("grid2_name", "")
                    intersection_name = "{}{}".format(grid1_name, grid2_name)
                    
                    if intersection_name not in skip_intersections:
                        filtered_intersections.append(intersection)
                    elif ctx:
                        await ctx.info("Skipping intersection: {}".format(intersection_name))
                
                intersections = filtered_intersections

            if ctx:
                await ctx.info("Creating {} columns (skipped {})".format(
                    len(intersections), 
                    len(skip_intersections) if skip_intersections else 0
                ))

            # Create columns at filtered intersections
            result = await create_columns_at_grid_intersections(
                family_name=family_name,
                base_level=base_level,
                intersections=intersections,
                type_name=type_name,
                top_level=top_level,
                height=height,
                base_offset=base_offset,
                top_offset=top_offset,
                structural_type=structural_type,
                structural_usage=structural_usage,
                ctx=ctx
            )

            return result

        except Exception as e:
            error_msg = "Failed to create column layout: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg 