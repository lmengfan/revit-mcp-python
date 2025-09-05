# -*- coding: utf-8 -*-
"""
MCP Tools for Pipe Management

This module provides MCP tools for comprehensive pipe management in Revit MEP systems.
It includes tools for creating, editing, querying, and analyzing pipes with full
parametric control and detailed type property extraction.

Key Features:
- Create and edit pipes with comprehensive control
- Place pipes between points with diameter specifications
- Query pipe properties and extract detailed type information
- Support for various pipe types and piping systems
- Automatic system type and pipe type selection based on criteria
- Comprehensive type property extraction including dimensions, materials, and system data
- Unit conversion and proper metric output (mm, L/s, kPa)

Tools:
- create_or_edit_pipe() - Create new or edit existing pipes
- place_pipe_between_points() - Place pipe between two specific points
- query_pipe() - Get basic pipe information by ID
- get_pipe_details() - Get comprehensive pipe details from selection
- create_pipe_layout() - Create multiple pipes in layout patterns
"""

from mcp.server.fastmcp import Context
from typing import Dict, Any, List
from .utils import format_response


def register_pipe_tools(mcp, revit_get, revit_post):
    """Register pipe management tools with the MCP server."""

    @mcp.tool()
    async def create_or_edit_pipe(
        start_point: Dict[str, float],
        end_point: Dict[str, float],
        element_id: str = None,
        inner_diameter: float = None,
        outer_diameter: float = None,
        nominal_diameter: str = None,
        level_name: str = None,
        system_type_name: str = None,
        pipe_type_name: str = None,
        material: str = None,
        properties: Dict[str, Any] = None,
        ctx: Context = None,
    ) -> str:
        """
        Create a new pipe or edit an existing pipe in Revit.

        This tool can operate in two modes:
        1. **Creation Mode** (when element_id is None): Creates a new pipe
        2. **Edit Mode** (when element_id is provided): Modifies an existing pipe

        Args:
            start_point: Start point coordinates as dict with x, y, z keys (in mm)
            end_point: End point coordinates as dict with x, y, z keys (in mm)
            element_id: Element ID of existing pipe to edit (optional, for edit mode)
            inner_diameter: Inner diameter in mm (optional)
            outer_diameter: Outer diameter in mm (optional)
            nominal_diameter: Nominal size (e.g., "4\"", "100mm") (optional)
            level_name: Level name for the pipe (optional)
            system_type_name: Piping system type name (e.g., "Domestic Hot Water") (optional)
            pipe_type_name: Pipe type name (e.g., "Standard") (optional)
            material: Pipe material name (e.g., "Steel") (optional)
            properties: Additional parameters to set (optional):
                {"Mark": "P1", "Comments": "Main supply line", etc.}
            ctx: MCP context for logging

        Returns:
            Success message with pipe details or error information

        Examples:
            # Create a new pipe with diameter specification
            create_or_edit_pipe(
                start_point={"x": 0, "y": 0, "z": 3000},
                end_point={"x": 5000, "y": 0, "z": 3000},
                inner_diameter=100.0,
                outer_diameter=110.0,
                system_type_name="Domestic Hot Water",
                properties={"Mark": "P1", "Comments": "Main supply line"}
            )
            
            # Edit an existing pipe
            create_or_edit_pipe(
                element_id="123456",
                start_point={"x": 0, "y": 0, "z": 3000},
                end_point={"x": 6000, "y": 0, "z": 3000},
                nominal_diameter="4\"",
                pipe_type_name="Standard"
            )
            
            # Create pipe with nominal diameter
            create_or_edit_pipe(
                start_point={"x": 2000, "y": 1000, "z": 2500},
                end_point={"x": 8000, "y": 1000, "z": 2500},
                nominal_diameter="6\"",
                system_type_name="Chilled Water Supply",
                material="Steel",
                properties={"Mark": "CHW-S1"}
            )
        """
        try:
            if ctx:
                ctx.info("Creating/editing pipe...")

            # Prepare request data
            request_data = {
                "start_point": start_point,
                "end_point": end_point,
                "properties": properties or {}
            }
            
            # Add optional parameters
            if element_id:
                request_data["element_id"] = element_id
            if inner_diameter is not None:
                request_data["inner_diameter"] = inner_diameter
            if outer_diameter is not None:
                request_data["outer_diameter"] = outer_diameter
            if nominal_diameter:
                request_data["nominal_diameter"] = nominal_diameter
            if level_name:
                request_data["level_name"] = level_name
            if system_type_name:
                request_data["system_type_name"] = system_type_name
            if pipe_type_name:
                request_data["pipe_type_name"] = pipe_type_name
            if material:
                request_data["material"] = material

            response = await revit_post("/create_or_edit_pipe/", request_data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to create/edit pipe: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def place_pipe_between_points(
        point1: Dict[str, float],
        point2: Dict[str, float],
        diameter: float = None,
        nominal_diameter: str = None,
        system_type_name: str = None,
        mark: str = None,
        ctx: Context = None,
    ) -> str:
        """
        Place a pipe between two specific points.

        This is a convenience tool that creates a pipe by specifying two points directly.
        It's useful for quick pipe placement when you know the exact coordinates.

        Args:
            point1: First point coordinates as dict with x, y, z keys (in mm)
            point2: Second point coordinates as dict with x, y, z keys (in mm)
            diameter: Pipe diameter in mm (optional)
            nominal_diameter: Nominal pipe size (e.g., "4\"", "100mm") (optional)
            system_type_name: Piping system type name (optional)
            mark: Pipe mark/identifier (optional)
            ctx: MCP context for logging

        Returns:
            Success message with pipe details or error information

        Examples:
            # Place a simple pipe
            place_pipe_between_points(
                point1={"x": 0, "y": 0, "z": 3000},
                point2={"x": 5000, "y": 0, "z": 3000},
                diameter=100.0,
                system_type_name="Domestic Hot Water",
                mark="P1"
            )
            
            # Place a pipe with nominal diameter
            place_pipe_between_points(
                point1={"x": 2000, "y": 1000, "z": 2500},
                point2={"x": 8000, "y": 1000, "z": 2500},
                nominal_diameter="6\"",
                system_type_name="Chilled Water Supply",
                mark="CHW-1"
            )
        """
        try:
            if ctx:
                ctx.info("Placing pipe between points...")

            # Prepare request data
            request_data = {
                "start_point": point1,
                "end_point": point2,
                "properties": {}
            }
            
            # Add optional parameters
            if diameter is not None:
                request_data["inner_diameter"] = diameter
                request_data["outer_diameter"] = diameter + 10  # Approximate wall thickness
            if nominal_diameter:
                request_data["nominal_diameter"] = nominal_diameter
            if system_type_name:
                request_data["system_type_name"] = system_type_name
            if mark:
                request_data["properties"]["Mark"] = mark

            response = await revit_post("/create_or_edit_pipe/", request_data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to place pipe: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def query_pipe(element_id: str, ctx: Context = None) -> str:
        """
        Query basic information about a pipe by element ID.

        This tool retrieves essential information about an existing pipe including
        its configuration, location, type, and key properties. The returned data
        can be used for inspection, copying, or modification workflows.

        Args:
            element_id: The element ID of the pipe to query (required)
            ctx: MCP context for logging

        Returns:
            Pipe configuration and properties or error message

        Response includes:
            - message: Success/error message
            - pipe_config: Complete pipe configuration including:
                - element_id: Pipe element ID
                - name: Pipe name/mark
                - start_point/end_point: Coordinates in mm
                - length: Pipe length in mm
                - diameter: Pipe diameter in mm
                - system_type_name: Piping system type
                - pipe_type_name: Pipe type name
                - level_name: Associated level
                - properties: Additional parameters

        This is useful for getting pipe properties, understanding configurations,
        and preparing data for pipe copying or modification operations.

        Examples:
            # Query a specific pipe
            result = query_pipe("123456")
            # Returns detailed pipe configuration
            
            # Use for copying pipe configuration
            original = query_pipe("123456")
            # Then use the config to create similar pipe
        """
        try:
            if ctx:
                ctx.info("Querying pipe with ID: {}".format(element_id))

            response = await revit_get("/query_pipe/?element_id={}".format(element_id), ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to query pipe: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def get_pipe_details(ctx: Context = None) -> str:
        """
        Get comprehensive information about selected pipe elements in Revit.

        Returns detailed information about each selected pipe including:
        - Pipe ID, name, and type information
        - Pipe type properties (diameter, material, roughness, etc.)
        - System type information (fluid type, temperature, pressure)
        - Location information (start/end points, length, slope)
        - Level information and height data
        - Flow and sizing parameters
        - Key parameters (Mark, Comments, etc.)
        - Bounding box dimensions

        All measurements are converted to metric units (mm for lengths, L/s for flow,
        kPa for pressure, etc.).

        Args:
            ctx: MCP context for logging

        Returns:
            Detailed pipe information or error message

        Response includes:
            - message: Success/error message
            - selected_count: Total number of selected elements
            - pipes_found: Number of pipe elements found
            - pipes: Array of detailed pipe information with:
                - Basic info (ID, name, pipe type)
                - Comprehensive type_properties:
                    - dimensions: Diameter, wall thickness, etc.
                    - material: Material properties and characteristics
                    - roughness: Surface roughness values
                    - additional_parameters: Custom type parameters
                - system_properties: Fluid type, temperature, density, etc.
                - location: Start/end points, length, direction, midpoint
                - level: Level information and elevation
                - parameters: Instance parameters (Mark, Comments, Flow, Size, etc.)
                - bounding_box: Element bounds

        This is useful for analyzing selected pipes, getting their comprehensive properties,
        understanding their system characteristics, and extracting data for analysis,
        flow calculations, documentation, or export to other systems.

        Examples:
            # Select some pipes in Revit, then call:
            result = get_pipe_details()
            # Returns comprehensive information about all selected pipes
            
            # Use for flow analysis data extraction
            pipe_data = get_pipe_details()
            # Extract diameters, materials, system properties, etc.
        """
        try:
            if ctx:
                ctx.info("Getting detailed information about selected pipes...")

            response = await revit_get("/get_pipe_details/", ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to get pipe details: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def create_pipe_layout(
        pipe_configs: List[Dict[str, Any]],
        system_type_name: str = None,
        pipe_type_name: str = None,
        naming_pattern: str = "P{}",
        ctx: Context = None,
    ) -> str:
        """
        Create multiple pipes in a layout pattern.

        This tool allows you to create multiple pipes at once using different layout strategies.
        It's useful for creating pipe runs, distribution systems, or any pattern of multiple pipes.

        Args:
            pipe_configs: Array of pipe configurations, each containing:
                - start_point: Start coordinates {"x": 0, "y": 0, "z": 3000}
                - end_point: End coordinates {"x": 5000, "y": 0, "z": 3000}
                - diameter: Pipe diameter in mm (optional)
                - nominal_diameter: Nominal size (optional)
                - mark: Pipe mark (optional, uses naming_pattern)
                - properties: Additional parameters (optional)
            system_type_name: Default system type for all pipes (optional)
            pipe_type_name: Default pipe type for all pipes (optional)
            naming_pattern: Pattern for auto-naming pipes with {} placeholder (default: "P{}")
            ctx: MCP context for logging

        Returns:
            Success message with created pipe details or error information

        Response includes:
            - message: Summary of creation results
            - created_count: Number of successfully created pipes
            - requested_count: Total number of pipes requested
            - pipes: Array of created pipe details

        Examples:
            # Create a simple pipe layout
            create_pipe_layout(
                pipe_configs=[
                    {
                        "start_point": {"x": 0, "y": 0, "z": 3000},
                        "end_point": {"x": 5000, "y": 0, "z": 3000},
                        "diameter": 100.0
                    },
                    {
                        "start_point": {"x": 5000, "y": 0, "z": 3000},
                        "end_point": {"x": 5000, "y": 3000, "z": 3000},
                        "diameter": 80.0
                    }
                ],
                system_type_name="Domestic Hot Water",
                naming_pattern="DHW{}"
            )
            
            # Create mixed pipe sizes layout
            create_pipe_layout(
                pipe_configs=[
                    {
                        "start_point": {"x": 0, "y": 0, "z": 3000},
                        "end_point": {"x": 10000, "y": 0, "z": 3000},
                        "nominal_diameter": "6\"",
                        "mark": "MAIN-1",
                        "properties": {"Comments": "Main supply line"}
                    },
                    {
                        "start_point": {"x": 2000, "y": 0, "z": 3000},
                        "end_point": {"x": 2000, "y": 8000, "z": 3000},
                        "nominal_diameter": "4\"",
                        "mark": "BRANCH-1",
                        "properties": {"Comments": "Branch line"}
                    }
                ],
                system_type_name="Chilled Water Supply"
            )
        """
        try:
            if ctx:
                ctx.info("Creating pipe layout with {} pipes...".format(len(pipe_configs)))

            # Process each pipe configuration
            results = []
            created_count = 0
            
            for i, config in enumerate(pipe_configs):
                try:
                    # Prepare request data for individual pipe
                    request_data = {
                        "start_point": config.get("start_point"),
                        "end_point": config.get("end_point"),
                        "properties": config.get("properties", {})
                    }
                    
                    # Add diameter specifications
                    if "diameter" in config:
                        request_data["inner_diameter"] = config["diameter"]
                        request_data["outer_diameter"] = config["diameter"] + 10
                    if "nominal_diameter" in config:
                        request_data["nominal_diameter"] = config["nominal_diameter"]
                    
                    # Add system and type specifications
                    if system_type_name:
                        request_data["system_type_name"] = system_type_name
                    if pipe_type_name:
                        request_data["pipe_type_name"] = pipe_type_name
                    
                    # Add mark if not specified
                    if "mark" not in config and "Mark" not in request_data["properties"]:
                        request_data["properties"]["Mark"] = naming_pattern.format(i + 1)
                    elif "mark" in config:
                        request_data["properties"]["Mark"] = config["mark"]
                    
                    # Create the pipe
                    response = await revit_post("/create_or_edit_pipe/", request_data, ctx)
                    
                    if response and response.get("status") == "success":
                        created_count += 1
                        results.append({
                            "index": i + 1,
                            "status": "success",
                            "element_id": response.get("element_id"),
                            "message": response.get("message")
                        })
                    else:
                        results.append({
                            "index": i + 1,
                            "status": "error",
                            "message": response.get("message", "Unknown error")
                        })
                        
                except Exception as e:
                    results.append({
                        "index": i + 1,
                        "status": "error",
                        "message": str(e)
                    })
                    continue
            
            # Prepare summary response
            requested_count = len(pipe_configs)
            summary_message = "Created {} of {} pipes successfully".format(created_count, requested_count)
            
            return format_response({
                "status": "success" if created_count > 0 else "error",
                "message": summary_message,
                "created_count": created_count,
                "requested_count": requested_count,
                "pipes": results
            })

        except Exception as e:
            error_msg = "Failed to create pipe layout: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def find_or_create_pipe_type_with_routing(
        pipe_type_name: str,
        nominal_diameter: float = None,
        inner_diameter: float = None,
        outer_diameter: float = None,
        material: str = None,
        ctx: Context = None,
    ) -> str:
        """
        Find an existing pipe type with exact name match and check RoutingPreferenceManager for matching rules.
        
        This tool implements exact matching logic:
        1. If pipe type name does not match exactly, creates a new pipe type
        2. If name matches, checks RoutingPreferenceManager rules for matching material and diameters
        3. If no matching rule found, creates a new segment rule with specified criteria
        
        This follows the RoutingPreferenceManager approach as documented in the Revit API.

        Args:
            pipe_type_name: Exact pipe type name (required)
            nominal_diameter: Nominal diameter in mm (optional)
            inner_diameter: Inner diameter in mm (optional)
            outer_diameter: Outer diameter in mm (optional)
            material: Material name for exact matching (optional, e.g., "Steel", "Copper")
            ctx: MCP context for logging

        Returns:
            Pipe type information with routing rule status

        Response includes:
            - pipe_type_id: The pipe type element ID
            - pipe_type_name: The actual pipe type name
            - created: Boolean indicating if new pipe type was created
            - rule_match_found: Boolean indicating if matching routing rule was found
            - segment_id: Associated segment ID (if applicable)
            - nominal_diameter: Nominal diameter in mm
            - inner_diameter: Inner diameter in mm
            - outer_diameter: Outer diameter in mm

        Examples:
            # Find pipe type with exact name and check routing rules
            find_or_create_pipe_type_with_routing(
                pipe_type_name="Standard Steel Pipe",
                inner_diameter=100.0,
                outer_diameter=110.0,
                material="Steel"
            )
            
            # Create new pipe type if name doesn't match
            find_or_create_pipe_type_with_routing(
                pipe_type_name="Custom Copper DHW",
                nominal_diameter=25.0,
                material="Copper"
            )
        """
        try:
            if ctx:
                ctx.info("Finding/creating pipe type with routing: {}".format(pipe_type_name))

            # Use the pipe creation endpoint with the new logic
            request_data = {
                "start_point": {"x": 0, "y": 0, "z": 0},
                "end_point": {"x": 1000, "y": 0, "z": 0},  # Dummy points for type creation
                "pipe_type_name": pipe_type_name,
                "properties": {"Mark": "TYPE_CREATION_DUMMY"}
            }
            
            # Add diameter parameters
            if nominal_diameter is not None:
                request_data["nominal_diameter"] = str(nominal_diameter)
            if inner_diameter is not None:
                request_data["inner_diameter"] = inner_diameter
            if outer_diameter is not None:
                request_data["outer_diameter"] = outer_diameter
            if material:
                request_data["material"] = material

            response = await revit_post("/create_or_edit_pipe/", request_data, ctx)
            
            # Extract type information from the response
            if response and response.get("status") == "success":
                return format_response({
                    "status": "success",
                    "message": "Pipe type processing completed",
                    "pipe_type_processing": "completed",
                    "details": response
                })
            else:
                return format_response(response)

        except Exception as e:
            error_msg = "Failed to find/create pipe type with routing: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def find_or_create_pipe_segment(
        name: str,
        nominal_diameter: float = None,
        inner_diameter: float = None,
        outer_diameter: float = None,
        material: str = None,
        roughness: float = None,
        base_segment_name: str = None,
        ctx: Context = None,
    ) -> str:
        """
        Find an existing segment with matching size or create a new one based on name and diameter criteria.

        This tool searches for segments matching the specified criteria. If an exact match
        is found (name matches and one of the sizes matches the diameters), it returns the existing
        segment and matching size. If no match is found, it creates a new segment with the specified size.

        Args:
            name: Segment name (required)
            nominal_diameter: Nominal diameter in mm (optional)
            inner_diameter: Inner diameter in mm (optional)
            outer_diameter: Outer diameter in mm (optional)
            material: Material name (optional, e.g., "Steel", "Copper")
            roughness: Surface roughness value (optional)
            base_segment_name: Base segment to duplicate from (optional, uses first available if not specified)
            ctx: MCP context for logging

        Returns:
            Segment information with element ID and creation status

        Response includes:
            - segment_id: The segment element ID
            - segment_name: The actual segment name
            - created: Boolean indicating if new segment was created (true) or existing found (false)
            - nominal_diameter: Nominal diameter in mm
            - inner_diameter: Inner diameter in mm
            - outer_diameter: Outer diameter in mm

        Examples:
            # Find existing or create new steel segment
            find_or_create_pipe_segment(
                name="Custom Steel 100mm",
                inner_diameter=100.0,
                outer_diameter=110.0,
                material="Steel",
                roughness=0.0015
            )
            
            # Create segment with nominal diameter
            find_or_create_pipe_segment(
                name="Copper DHW 25mm",
                nominal_diameter=25.0,
                inner_diameter=25.0,
                outer_diameter=28.0,
                material="Copper"
            )
            
            # Simple segment creation with any diameter specification
            find_or_create_pipe_segment(
                name="Custom Pipe 50mm",
                nominal_diameter=50.0
            )
        """
        try:
            if ctx:
                ctx.info("Finding/creating pipe segment: {}".format(name))

            # Prepare request data
            request_data = {
                "name": name
            }
            
            # Add diameter parameters
            if nominal_diameter is not None:
                request_data["nominal_diameter"] = nominal_diameter
            if inner_diameter is not None:
                request_data["inner_diameter"] = inner_diameter
            if outer_diameter is not None:
                request_data["outer_diameter"] = outer_diameter
            
            # Add optional parameters
            if material:
                request_data["material"] = material
            if roughness is not None:
                request_data["roughness"] = roughness
            if base_segment_name:
                request_data["base_segment_name"] = base_segment_name

            response = await revit_post("/find_or_create_pipe_segment/", request_data, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to find/create pipe segment: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg

    @mcp.tool()
    async def list_pipe_segments(
        name_filter: str = None,
        include_sizes: bool = False,
        ctx: Context = None,
    ) -> str:
        """
        List all available pipe segments in the current Revit document.

        This tool provides a comprehensive list of all pipe segments available in the document,
        with optional filtering and detailed size information. Useful for discovering
        existing segments before creating new ones.

        Args:
            name_filter: Optional filter for segment names (case-insensitive contains search)
            include_sizes: Include detailed size information for each segment (default: False)
            ctx: MCP context for logging

        Returns:
            List of pipe segments with their properties

        Response includes:
            - count: Number of segments found
            - segments: Array of segment information:
                - segment_id: Segment element ID
                - name: Segment name
                - roughness: Surface roughness value
                - sizes: Array of size information (if include_sizes=True):
                    - nominal_diameter: Nominal diameter in mm
                    - inner_diameter: Inner diameter in mm
                    - outer_diameter: Outer diameter in mm
                - size_count: Number of sizes available

        Examples:
            # List all pipe segments
            list_pipe_segments()
            
            # Filter segments containing "steel"
            list_pipe_segments(name_filter="steel")
            
            # Get detailed size information for all segments
            list_pipe_segments(include_sizes=True)
            
            # Find copper segments with size details
            list_pipe_segments(name_filter="copper", include_sizes=True)
        """
        try:
            if ctx:
                ctx.info("Listing pipe segments...")

            # Build query parameters
            params = []
            if name_filter:
                params.append("name_filter={}".format(name_filter))
            if include_sizes:
                params.append("include_sizes=true")
            
            query_string = "&".join(params)
            url = "/list_pipe_segments/"
            if query_string:
                url += "?" + query_string

            response = await revit_get(url, ctx)
            return format_response(response)

        except Exception as e:
            error_msg = "Failed to list pipe segments: {}".format(str(e))
            if ctx:
                ctx.error(error_msg)
            return error_msg 