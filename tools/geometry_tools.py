# -*- coding: utf-8 -*-
"""Geometry analysis tools for the MCP server."""

from mcp.server.fastmcp import Context
from typing import Dict, Any
from .utils import format_response


def register_geometry_tools(mcp, revit_get, revit_post):


    @mcp.tool()
    async def check_points_in_bounding_box(
        point_pairs: list,
        ctx: Context = None,
    ) -> str:
        """
        Check if multiple start and end points are inside the bounding box of a selected Revit element.

        This tool checks whether given start and end points are inside the bounding box 
        of the currently selected Revit element. For each point pair, it returns true if 
        either the start point OR the end point is inside the bounding box.

        Args:
            point_pairs: List of point pairs, each containing start_point and end_point
                        [
                            {
                                "start_point": {"x": 1000.0, "y": 2000.0, "z": 3000.0},
                                "end_point": {"x": 1500.0, "y": 2500.0, "z": 3500.0}
                            },
                            {
                                "start_point": {"x": 4000.0, "y": 5000.0, "z": 6000.0},
                                "end_point": {"x": 4500.0, "y": 5500.0, "z": 6500.0}
                            }
                        ]
            ctx: MCP context for logging

        Returns:
            Success message with batch results or error information

        Response includes:
            - message: Success/error message
            - results: List of boolean values - one for each point pair
            - detailed_results: Detailed breakdown showing which points are inside
            - total_pairs: Total number of point pairs processed
            - pairs_inside: Number of pairs where at least one point is inside
            - selected_count: Number of selected elements (always 1)
            - bounding_box_info: Information about the bounding box used
            - element: Selected element information

        Examples:
            # Check multiple point pairs against bounding box
            check_points_in_bounding_box(
                point_pairs=[
                    {
                        "start_point": {"x": 1000.0, "y": 2000.0, "z": 3000.0},
                        "end_point": {"x": 1500.0, "y": 2500.0, "z": 3500.0}
                    },
                    {
                        "start_point": {"x": 4000.0, "y": 5000.0, "z": 6000.0},
                        "end_point": {"x": 4500.0, "y": 5500.0, "z": 6500.0}
                    }
                ]
            )
            # Returns: {"results": [true, false], ...}

        Usage Tips:
            - Select exactly one Revit element before calling this tool
            - Point coordinates should be in mm (Revit internal units)
            - Returns true if EITHER start OR end point is inside the bounding box
            - Efficient for checking multiple point pairs against the same bounding box
            - Provides both simple boolean results and detailed breakdown
        """
        try:
            data = {
                "point_pairs": point_pairs
            }

            if ctx:
                await ctx.info("Checking {} point pairs against bounding box of selected element".format(len(point_pairs)))

            response = await revit_post("/check_points_in_bounding_box/", data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to check points inside bounding box: {}".format(str(e))
            if ctx:
                await ctx.error(error_msg)
            return error_msg

