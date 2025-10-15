# -*- coding: utf-8 -*-
"""Pipe management tools for the MCP server."""

from mcp.server.fastmcp import Context
from typing import Dict, Any, List
from .utils import format_response


def register_pipe_tools(mcp, revit_get, revit_post):
    """Register pipe management tools with the MCP server."""

    @mcp.tool()
    async def create_or_edit_multiple_pipes(
        pipe_configs: List[Dict[str, Any]],
        naming_pattern: str = "P{}",
        system_type_name: str = None,
        pipe_type_name: str = None,
        ctx: Context = None,
    ) -> str:
        """
        Create or edit multiple pipes using a list of pipe configurations.

        This tool allows you to create multiple pipes at once using different layout strategies.
        It's useful for creating pipe runs, distribution systems, or any pattern of multiple pipes.
        if the source data has id attached, it should be passed in the element_id field.
        This source contain length unit, you should convert the data from source unit to mm.
        Args:
            pipe_configs: Array of pipe configurations, each containing:
                - start_point: Start coordinates in mm {"x": 0, "y": 0, "z": 3000}
                - end_point: End coordinates in mm {"x": 5000, "y": 0, "z": 3000} 
                - element_id: Source object id for mapping and updating (optional)
                - inner_diameter: Inner diameter in mm 
                - outer_diameter: Outer diameter in mm 
                - nominal_diameter: Nominal size 
                - level_name: Level name (optional)
                - system_type_name: System type (optional)
                - pipe_type_name: Pipe type 
                - material: Material name 
                - properties: Additional parameters (optional)
            naming_pattern: Pattern for auto-naming pipes with {} placeholder (default: "P{}")
            system_type_name: Default system type for all pipes (optional)
            pipe_type_name: Default pipe type for all pipes (optional)
            ctx: MCP context for logging

        Returns:
            Success message with created pipe details or error information

        Response includes:
            - message: Summary of creation results
            - status: "success", "partial", or "failed"
            - total_requested: Total number of pipes requested
            - successful_count: Number of successfully created pipes
            - failed_count: Number of failed pipes
            - results: Array of detailed results for each pipe
            - successful_pipes: Array of created pipe element IDs
            - failed_configs: Array of failed configurations with errors

        Examples:
            # Create a simple pipe layout
            create_or_edit_multiple_pipes(
                pipe_configs=[
                    {
                        "start_point": {"x": 0, "y": 0, "z": 3000},
                        "end_point": {"x": 5000, "y": 0, "z": 3000},
                        "element_id": null,  // Optional - Source object id for mapping and updating
                        "inner_diameter": 100.0,  // Inner diameter in mm
                        "outer_diameter": 110.0,  // Outer diameter in mm
                        "nominal_diameter": 100.0,  // Nominal diameter in mm
                        "level_name": "L1",  // Optional - level name
                        "system_type_name": "Domestic Hot Water",  // Optional - system type
                        "pipe_type_name": "Standard",  // Pipe type Name
                        "material": "Steel",  // Material name
                        "properties": {  // Optional - additional parameters
                            "Comments": "Main supply line"
                    },
                    {
                        "start_point": {"x": 5000, "y": 0, "z": 3000},
                        "end_point": {"x": 5000, "y": 3000, "z": 3000},
                        "element_id": null,  // Optional - Source object id for mapping and updating
                        "inner_diameter": 100.0,  // Inner diameter in mm
                        "outer_diameter": 110.0,  // Outer diameter in mm
                        "nominal_diameter": 100.0,  // Nominal diameter in mm
                        "level_name": "L1",  // Optional - level name
                        "system_type_name": "Domestic Hot Water",  // Optional - system type
                        "pipe_type_name": "Standard",  // Pipe type Name
                        "material": "Steel",  // Material name
                        "properties": {  // Optional - additional parameters
                            "Comments": "Main supply line"
                    }
                ],
                system_type_name="Domestic Hot Water",
                naming_pattern="DHW{}"
            )
        """
        try:
            data = {
                "pipe_configs": pipe_configs,
                "naming_pattern": naming_pattern,
                "system_type_name": system_type_name,
                "pipe_type_name": pipe_type_name
            }

            if ctx:
                await ctx.info("Creating/editing {} pipes via batch operation".format(len(pipe_configs)))

            response = await revit_post("/create_or_edit_multiple_pipes/", data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to create/edit multiple pipes: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg
