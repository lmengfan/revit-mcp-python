# -*- coding: utf-8 -*-
"""Grid management tools for the MCP server."""

from mcp.server.fastmcp import Context
from typing import Dict, Any, List
from .utils import format_response


def register_grid_tools(mcp, revit_get, revit_post):
    """Register grid management tools with the MCP server."""

    @mcp.tool()
    async def create_or_edit_grid(
        grid_type: str,
        element_id: str = None,
        name: str = None,
        start_point: Dict[str, float] = None,
        end_point: Dict[str, float] = None,
        center_point: Dict[str, float] = None,
        radius: float = None,
        start_angle: float = 0.0,
        end_angle: float = 180.0,
        vertical_extents: Dict[str, str] = None,
        properties: Dict[str, Any] = None,
        ctx: Context = None,
    ) -> str:
        """
        Create a new grid or edit an existing grid in Revit.

        This tool can operate in two modes:
        1. **Creation Mode** (when element_id is None): Creates a new grid
        2. **Edit Mode** (when element_id is provided): Modifies an existing grid

        Args:
            grid_type: Type of grid - "linear" or "radial" (required)
            element_id: Element ID of existing grid to edit (optional, for edit mode)
            name: Grid name/label (optional, e.g., "A", "1", "Grid-01")
            start_point: Start point for linear grids {"x": 0, "y": 0, "z": 0} in mm
            end_point: End point for linear grids {"x": 5000, "y": 0, "z": 0} in mm
            center_point: Center point for radial grids {"x": 0, "y": 0, "z": 0} in mm
            radius: Radius for radial grids in mm (required for radial grids)
            start_angle: Start angle for radial grids in degrees (default: 0.0)
            end_angle: End angle for radial grids in degrees (default: 180.0)
            vertical_extents: Level extents {"bottom_level": "Level 1", "top_level": "Level 2"}
            properties: Additional parameters {"Comments": "Created via MCP"}
            ctx: MCP context for logging

        Returns:
            Success message with grid details or error information

        Examples:
            # Create a linear grid
            create_or_edit_grid(
                grid_type="linear",
                name="A",
                start_point={"x": 0, "y": 0, "z": 0},
                end_point={"x": 10000, "y": 0, "z": 0},
                properties={"Comments": "Main structural grid"}
            )

            # Create a radial grid
            create_or_edit_grid(
                grid_type="radial",
                name="R1",
                center_point={"x": 5000, "y": 5000, "z": 0},
                radius=8000.0,
                start_angle=0.0,
                end_angle=270.0
            )

            # Edit an existing grid
            create_or_edit_grid(
                element_id="123456",
                grid_type="linear",
                name="A-Modified",
                start_point={"x": 0, "y": 0, "z": 0},
                end_point={"x": 12000, "y": 0, "z": 0}
            )
        """
        try:
            data = {
                "grid_type": grid_type,
                "element_id": element_id,
                "name": name,
                "start_point": start_point,
                "end_point": end_point,
                "center_point": center_point,
                "radius": radius,
                "start_angle": start_angle,
                "end_angle": end_angle,
                "vertical_extents": vertical_extents,
                "properties": properties or {}
            }

            if ctx:
                ctx.info("Creating/editing {} grid{}".format(
                    grid_type, " '{}'".format(name) if name else ""
                ))

            response = await revit_post("/create_or_edit_grid/", data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to create/edit grid: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def create_linear_grid(
        start_point: Dict[str, float],
        end_point: Dict[str, float],
        name: str = None,
        vertical_extents: Dict[str, str] = None,
        properties: Dict[str, Any] = None,
        ctx: Context = None,
    ) -> str:
        """
        Create a linear grid with start and end points.

        This is a convenience tool that automatically sets grid_type to "linear".

        Args:
            start_point: Start point {"x": 0, "y": 0, "z": 0} in mm (required)
            end_point: End point {"x": 5000, "y": 0, "z": 0} in mm (required)
            name: Grid name/label (optional, e.g., "A", "1", "Grid-01")
            vertical_extents: Level extents {"bottom_level": "Level 1", "top_level": "Level 2"}
            properties: Additional parameters {"Comments": "Created via MCP"}
            ctx: MCP context for logging

        Returns:
            Success message with grid details or error information

        Example:
            # Create a horizontal linear grid
            create_linear_grid(
                start_point={"x": 0, "y": 0, "z": 0},
                end_point={"x": 15000, "y": 0, "z": 0},
                name="A",
                properties={"Comments": "Primary grid line"}
            )
        """
        return await create_or_edit_grid(
            grid_type="linear",
            start_point=start_point,
            end_point=end_point,
            name=name,
            vertical_extents=vertical_extents,
            properties=properties,
            ctx=ctx
        )

    @mcp.tool()
    async def create_radial_grid(
        center_point: Dict[str, float],
        radius: float,
        start_angle: float = 0.0,
        end_angle: float = 180.0,
        name: str = None,
        vertical_extents: Dict[str, str] = None,
        properties: Dict[str, Any] = None,
        ctx: Context = None,
    ) -> str:
        """
        Create a radial (arc) grid with center point, radius, and angles.

        This is a convenience tool that automatically sets grid_type to "radial".

        Args:
            center_point: Center point {"x": 0, "y": 0, "z": 0} in mm (required)
            radius: Radius in mm (required)
            start_angle: Start angle in degrees (default: 0.0)
            end_angle: End angle in degrees (default: 180.0)
            name: Grid name/label (optional, e.g., "R1", "Arc-01")
            vertical_extents: Level extents {"bottom_level": "Level 1", "top_level": "Level 2"}
            properties: Additional parameters {"Comments": "Created via MCP"}
            ctx: MCP context for logging

        Returns:
            Success message with grid details or error information

        Example:
            # Create a 270-degree radial grid
            create_radial_grid(
                center_point={"x": 5000, "y": 5000, "z": 0},
                radius=10000.0,
                start_angle=0.0,
                end_angle=270.0,
                name="R1"
            )
        """
        return await create_or_edit_grid(
            grid_type="radial",
            center_point=center_point,
            radius=radius,
            start_angle=start_angle,
            end_angle=end_angle,
            name=name,
            vertical_extents=vertical_extents,
            properties=properties,
            ctx=ctx
        )

    @mcp.tool()
    async def query_grid(
        element_id: str,
        ctx: Context = None,
    ) -> str:
        """
        Query an existing grid by ID and return its configuration.

        This tool retrieves all properties of an existing grid in Revit and returns
        them in a structured format that can be used for inspection, copying, or
        modification workflows.

        Args:
            element_id: The Revit element ID of the grid to query (required)
            ctx: MCP context for logging

        Returns:
            Grid configuration with all properties or error information

        Response includes:
            - element_id: Grid element ID
            - name: Grid name/label
            - grid_type: "linear" or "radial"
            - For linear grids: start_point, end_point
            - For radial grids: center_point, radius, start_angle, end_angle

        Example:
            # Query existing grid
            result = query_grid("123456")
            # Use returned config to create similar grid
        """
        try:
            data = {"element_id": element_id}

            if ctx:
                ctx.info("Querying grid with ID: {}".format(element_id))

            response = await revit_post("/query_grid/", data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to query grid: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def find_grid_intersections(
        grid_ids: List[str] = None,
        level_name: str = None,
        ctx: Context = None,
    ) -> str:
        """
        Find intersection points between grids in the model.

        This tool calculates intersection points between grid lines, which is useful
        for placing structural elements like columns at grid intersections.

        Args:
            grid_ids: List of specific grid element IDs to analyze (optional)
                     If not provided, analyzes all grids in the model
            level_name: Level name to project intersections to (optional)
                       If provided, all intersection Z coordinates will be set to this level
            ctx: MCP context for logging

        Returns:
            List of intersection points with grid information

        Response includes:
            - intersections: Array of intersection data
              - grid1_id, grid1_name: First grid information
              - grid2_id, grid2_name: Second grid information
              - intersection_point: {"x": 1000, "y": 2000, "z": 0} in mm
            - grid_count: Number of grids analyzed
            - level_name: Level used for Z projection (if any)

        Examples:
            # Find all grid intersections
            find_grid_intersections()

            # Find intersections between specific grids
            find_grid_intersections(grid_ids=["123", "456", "789"])

            # Find intersections projected to a specific level
            find_grid_intersections(level_name="Level 1")

            # Find intersections between specific grids at a level
            find_grid_intersections(
                grid_ids=["123", "456"],
                level_name="Level 2"
            )
        """
        try:
            data = {
                "grid_ids": grid_ids or [],
                "level_name": level_name
            }

            if ctx:
                if grid_ids:
                    ctx.info("Finding intersections for {} specific grids".format(len(grid_ids)))
                else:
                    ctx.info("Finding intersections for all grids in model")
                if level_name:
                    ctx.info("Projecting intersections to level: {}".format(level_name))

            response = await revit_post("/find_grid_intersections/", data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to find grid intersections: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def create_grid_system(
        linear_grids: List[Dict[str, Any]],
        radial_grids: List[Dict[str, Any]] = None,
        vertical_extents: Dict[str, str] = None,
        ctx: Context = None,
    ) -> str:
        """
        Create a complete grid system with multiple linear and/or radial grids.

        This is a convenience tool for creating multiple grids at once, useful for
        setting up structural grid systems.

        Args:
            linear_grids: List of linear grid definitions, each containing:
                         {"name": "A", "start_point": {...}, "end_point": {...}}
            radial_grids: List of radial grid definitions (optional), each containing:
                         {"name": "R1", "center_point": {...}, "radius": 5000, "start_angle": 0, "end_angle": 180}
            vertical_extents: Common vertical extents for all grids (optional)
            ctx: MCP context for logging

        Returns:
            Summary of created grids or error information

        Example:
            # Create a rectangular grid system
            create_grid_system(
                linear_grids=[
                    {
                        "name": "A",
                        "start_point": {"x": 0, "y": 0, "z": 0},
                        "end_point": {"x": 0, "y": 20000, "z": 0}
                    },
                    {
                        "name": "B",
                        "start_point": {"x": 8000, "y": 0, "z": 0},
                        "end_point": {"x": 8000, "y": 20000, "z": 0}
                    },
                    {
                        "name": "1",
                        "start_point": {"x": 0, "y": 0, "z": 0},
                        "end_point": {"x": 8000, "y": 0, "z": 0}
                    },
                    {
                        "name": "2",
                        "start_point": {"x": 0, "y": 10000, "z": 0},
                        "end_point": {"x": 8000, "y": 10000, "z": 0}
                    }
                ],
                vertical_extents={"bottom_level": "Level 1", "top_level": "Roof"}
            )
        """
        try:
            created_grids = []
            failed_grids = []

            if ctx:
                total_grids = len(linear_grids) + (len(radial_grids) if radial_grids else 0)
                ctx.info("Creating grid system with {} grids".format(total_grids))

            # Create linear grids
            for i, grid_def in enumerate(linear_grids):
                try:
                    if ctx:
                        ctx.info("Creating linear grid {}/{}: {}".format(
                            i + 1, len(linear_grids), grid_def.get("name", "Unnamed")
                        ))

                    result = await create_linear_grid(
                        start_point=grid_def["start_point"],
                        end_point=grid_def["end_point"],
                        name=grid_def.get("name"),
                        vertical_extents=vertical_extents,
                        properties=grid_def.get("properties"),
                        ctx=ctx
                    )
                    created_grids.append({
                        "type": "linear",
                        "name": grid_def.get("name", "Unnamed"),
                        "result": result
                    })

                except Exception as e:
                    failed_grids.append({
                        "type": "linear",
                        "name": grid_def.get("name", "Unnamed"),
                        "error": str(e)
                    })

            # Create radial grids if provided
            if radial_grids:
                for i, grid_def in enumerate(radial_grids):
                    try:
                        if ctx:
                            ctx.info("Creating radial grid {}/{}: {}".format(
                                i + 1, len(radial_grids), grid_def.get("name", "Unnamed")
                            ))

                        result = await create_radial_grid(
                            center_point=grid_def["center_point"],
                            radius=grid_def["radius"],
                            start_angle=grid_def.get("start_angle", 0.0),
                            end_angle=grid_def.get("end_angle", 180.0),
                            name=grid_def.get("name"),
                            vertical_extents=vertical_extents,
                            properties=grid_def.get("properties"),
                            ctx=ctx
                        )
                        created_grids.append({
                            "type": "radial",
                            "name": grid_def.get("name", "Unnamed"),
                            "result": result
                        })

                    except Exception as e:
                        failed_grids.append({
                            "type": "radial",
                            "name": grid_def.get("name", "Unnamed"),
                            "error": str(e)
                        })

            # Prepare summary
            summary = "Grid system creation completed:\n"
            summary += "- Successfully created: {} grids\n".format(len(created_grids))
            if failed_grids:
                summary += "- Failed to create: {} grids\n".format(len(failed_grids))

            if created_grids:
                summary += "\nCreated grids:\n"
                for grid in created_grids:
                    summary += "  - {} grid '{}'\n".format(grid["type"], grid["name"])

            if failed_grids:
                summary += "\nFailed grids:\n"
                for grid in failed_grids:
                    summary += "  - {} grid '{}': {}\n".format(
                        grid["type"], grid["name"], grid["error"]
                    )

            return summary

        except Exception as e:
            error_msg = "Failed to create grid system: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def get_grid_details(ctx: Context = None) -> str:
        """
        Get comprehensive information about selected grid elements in Revit

        Returns detailed information about each selected grid including:
        - Grid ID, name, and type (linear or radial)
        - Curve geometry and coordinates in mm
        - For linear grids: start_point, end_point, length, direction, midpoint
        - For radial grids: center_point, radius, start_angle, end_angle, arc_span
        - Vertical extents and level information
        - Grid bubble and leader information
        - Key parameters (Comments, Mark, Phasing, etc.)
        - Bounding box dimensions and positioning
        - Intersection capabilities and calculations between selected grids

        All measurements are converted to metric units (mm for lengths, degrees for angles).

        Args:
            ctx: MCP context for logging

        Returns:
            Detailed grid information or error message

        Response includes:
            - message: Success/error message
            - selected_count: Total number of selected elements
            - grids_found: Number of grid elements found
            - grids: Array of detailed grid information
            - intersections: Intersection points between selected grids
            - intersection_count: Number of intersections found

        This is useful for analyzing selected grids, getting their properties,
        understanding their geometry, and finding intersection points for
        structural element placement.

        Example:
            # Select some grids in Revit, then call:
            result = get_grid_details()
            # Returns comprehensive information about all selected grids
        """
        try:
            if ctx:
                ctx.info("Getting detailed information about selected grids...")

            response = await revit_get("/grid_details/", ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to get grid details: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg 