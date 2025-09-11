# -*- coding: utf-8 -*-
"""
Wall Management for Revit MCP

This module provides comprehensive functionality for creating, editing, and querying
wall elements in Revit. It handles wall placement, modification, type properties,
and detailed information extraction.

Key Features:
- Create and edit walls with full parametric control
- Place walls along curves, between points, or by height/length
- Query wall properties and extract detailed type information
- Support for various wall types (basic, curtain, stacked, etc.)
- Comprehensive type property extraction including layers, materials, and thermal data
- Grid-based wall placement and layout generation
- Unit conversion between metric (mm) and Revit internal units (feet)

Routes:
- /create_or_edit_wall/ - Create new or edit existing walls
- /create_wall_by_curve/ - Create wall following a curve path
- /create_rectangular_wall/ - Create rectangular wall by dimensions
- /query_wall/ - Get basic wall information by ID
- /get_wall_details/ - Get comprehensive wall details from selection
- /create_wall_layout/ - Create multiple walls in a layout pattern
- /place_walls_on_grids/ - Place walls along grid lines
"""

import math
import logging

try:
    import clr
    clr.AddReference("RevitAPI")
    clr.AddReference("RevitAPIUI")
    from Autodesk.Revit import DB
    from pyrevit import revit, routes
    from revit_mcp.utils import get_element_name, find_family_symbol_safely
except ImportError as e:
    print("Revit API not available: {}".format(e))
    DB = None
    revit = None
    routes = None

# Configure logging
logger = logging.getLogger(__name__)


def register_wall_management_routes(api):
    """Register all wall management routes with the API"""
    if not api:
        logger.error("No API instance provided for wall management routes")
        return
    
    logger.info("Registering wall management routes...")

    logger.info("Wall management routes registered successfully")


    @api.route("/create_or_edit_wall/", methods=["POST"])
    @api.route("/create_or_edit_wall", methods=["POST"])
    def create_or_edit_wall():
        """
        Create a new wall or edit an existing one
        
        This endpoint can operate in two modes:
        1. Creation Mode (when element_id is None): Creates a new wall
        2. Edit Mode (when element_id is provided): Modifies an existing wall
        
        Expected JSON payload:
        {
            "element_id": "123456",  // Optional - for editing existing wall
            "level_name": "Level 1",  // Required - base level name
            "curve_points": [  // Required - array of points defining wall path
                {"x": 0, "y": 0, "z": 0},
                {"x": 5000, "y": 0, "z": 0}
            ],
            "wall_type_name": "Generic - 200mm",  // Optional - wall type name
            "height": 3000.0,  // Optional - wall height in mm (default: level height)
            "height_offset": 0.0,  // Optional - base offset from level in mm
            "top_offset": 0.0,  // Optional - top offset in mm
            "location_line": "Wall Centerline",  // Optional - Wall Centerline, Finish Face: Exterior, etc.
            "structural": false,  // Optional - is structural wall
            "properties": {  // Optional - additional parameters
                "Mark": "W1",
                "Comments": "Interior wall"
            }
        }
        """
        try:
            doc = revit.doc
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )
            
            # Get request data
            data = routes.get_request_json()
            if not data:
                return routes.make_response(
                    data={"error": "No JSON data provided"}, status=400
                )
            
            # Validate required parameters
            required_params = ["level_name", "curve_points"]
            for param in required_params:
                if param not in data:
                    return routes.make_response(
                        data={"error": "Missing required parameter: {}".format(param)}, status=400
                    )
            
            # Extract parameters
            element_id = data.get("element_id")
            level_name = data["level_name"]
            curve_points = data["curve_points"]
            wall_type_name = data.get("wall_type_name", "Generic - 200mm")
            height = data.get("height")
            height_offset = data.get("height_offset", 0.0)
            top_offset = data.get("top_offset", 0.0)
            location_line = data.get("location_line", "Wall Centerline")
            structural = data.get("structural", False)
            properties = data.get("properties", {})
            
            # Validate curve points
            if not isinstance(curve_points, list) or len(curve_points) < 2:
                return routes.make_response(
                    data={"error": "curve_points must be a list with at least 2 points"}, status=400
                )
            
            for i, point in enumerate(curve_points):
                if not isinstance(point, dict) or not all(k in point for k in ["x", "y", "z"]):
                    return routes.make_response(
                        data={"error": "Invalid point {} format. Expected dict with x, y, z keys".format(i)}, status=400
                    )
            
            # Start transaction
            with DB.Transaction(doc, "Create or Edit Wall") as trans:
                trans.Start()
                
                try:
                    # Find target level
                    level = _find_level_by_name(doc, level_name)
                    if not level:
                        return routes.make_response(
                            data={"error": "Level '{}' not found".format(level_name)}, status=404
                        )
                    
                    # Convert curve points from mm to feet
                    revit_points = []
                    for point in curve_points:
                        revit_pt = DB.XYZ(
                            point["x"] / 304.8,
                            point["y"] / 304.8,
                            (point["z"] + height_offset) / 304.8
                        )
                        revit_points.append(revit_pt)
                    
                    # Create wall curve
                    if len(revit_points) == 2:
                        # Simple line wall
                        wall_curve = DB.Line.CreateBound(revit_points[0], revit_points[1])
                    else:
                        # Multi-segment wall - create curve array
                        curves = []
                        for i in range(len(revit_points) - 1):
                            if not revit_points[i].IsAlmostEqualTo(revit_points[i + 1]):
                                curve = DB.Line.CreateBound(revit_points[i], revit_points[i + 1])
                                curves.append(curve)
                        
                        if len(curves) == 0:
                            return routes.make_response(
                                data={"error": "Cannot create wall with duplicate points"}, status=400
                            )
                        elif len(curves) == 1:
                            wall_curve = curves[0]
                        else:
                            # For multi-segment walls, we'll create individual walls and join them
                            wall_curve = curves[0]  # Start with first segment
                    
                    if element_id:
                        # Edit existing wall
                        result = _edit_existing_wall(
                            doc, element_id, wall_curve, level, wall_type_name,
                            height, height_offset, top_offset, location_line, structural, properties
                        )
                    else:
                        # Create new wall
                        result = _create_new_wall(
                            doc, wall_curve, level, wall_type_name,
                            height, height_offset, top_offset, location_line, structural, properties
                        )
                    
                    trans.Commit()
                    return routes.make_response(data=result, status=200)
                    
                except Exception as e:
                    trans.RollBack()
                    logger.error("Failed to create/edit wall: {}".format(str(e)))
                    return routes.make_response(
                        data={"error": "Failed to create/edit wall: {}".format(str(e))}, status=500
                    )
        
        except Exception as e:
            logger.error("Error in create_or_edit_wall: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Internal server error: {}".format(str(e))}, status=500
            )


    @api.route("/create_rectangular_wall/", methods=["POST"])
    @api.route("/create_rectangular_wall", methods=["POST"])
    def create_rectangular_wall():
        """
        Create a rectangular wall enclosure
        
        Expected JSON payload:
        {
            "level_name": "Level 1",  // Required - base level
            "origin": {"x": 0, "y": 0, "z": 0},  // Required - corner point in mm
            "width": 5000.0,  // Required - width in mm (X direction)
            "length": 3000.0,  // Required - length in mm (Y direction)
            "wall_type_name": "Generic - 200mm",  // Optional
            "height": 3000.0,  // Optional - wall height in mm
            "create_as_single_wall": false,  // Optional - create as 4 separate walls or single element
            "properties": {"Mark": "W1"}  // Optional
        }
        """
        try:
            doc = revit.doc
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )
            
            data = routes.get_request_json()
            if not data:
                return routes.make_response(
                    data={"error": "No JSON data provided"}, status=400
                )
            
            # Validate required parameters
            required_params = ["level_name", "origin", "width", "length"]
            for param in required_params:
                if param not in data:
                    return routes.make_response(
                        data={"error": "Missing required parameter: {}".format(param)}, status=400
                    )
            
            # Extract parameters
            level_name = data["level_name"]
            origin = data["origin"]
            width = data["width"]
            length = data["length"]
            wall_type_name = data.get("wall_type_name", "Generic - 200mm")
            height = data.get("height")
            create_as_single = data.get("create_as_single_wall", False)
            properties = data.get("properties", {})
            
            # Create rectangular curve points
            curve_points = [
                {"x": origin["x"], "y": origin["y"], "z": origin["z"]},
                {"x": origin["x"] + width, "y": origin["y"], "z": origin["z"]},
                {"x": origin["x"] + width, "y": origin["y"] + length, "z": origin["z"]},
                {"x": origin["x"], "y": origin["y"] + length, "z": origin["z"]},
                {"x": origin["x"], "y": origin["y"], "z": origin["z"]}  # Close the rectangle
            ]
            
            if create_as_single:
                # Create as single wall element
                wall_data = {
                    "level_name": level_name,
                    "curve_points": curve_points,
                    "wall_type_name": wall_type_name,
                    "height": height,
                    "properties": properties
                }
                return _create_wall_from_data(wall_data)
            else:
                # Create as 4 separate walls
                walls_data = []
                wall_names = ["South", "East", "North", "West"]
                
                for i in range(4):
                    wall_points = [curve_points[i], curve_points[i + 1]]
                    wall_props = properties.copy() if properties else {}
                    
                    # Add directional naming
                    if "Mark" in wall_props:
                        base_mark = wall_props["Mark"]
                        wall_props["Mark"] = "{}-{}".format(base_mark, wall_names[i])
                    
                    walls_data.append({
                        "level_name": level_name,
                        "curve_points": wall_points,
                        "wall_type_name": wall_type_name,
                        "height": height,
                        "properties": wall_props
                    })
                
                # Use layout creation for multiple walls
                layout_data = {
                    "level_name": level_name,
                    "wall_configs": walls_data,
                    "layout_type": "rectangular"
                }
                
                return _create_wall_layout_from_data(layout_data)
            
        except Exception as e:
            logger.error("Error in create_rectangular_wall: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Internal server error: {}".format(str(e))}, status=500
            )


    @api.route("/query_wall/", methods=["GET"])
    @api.route("/query_wall", methods=["GET"])
    def query_wall():
        """
        Query basic information about a wall by element ID
        
        Query parameters:
        - element_id: The element ID of the wall to query
        
        Returns basic wall information including name, type, location, and key properties
        """
        try:
            doc = revit.doc
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )
            
            # Get element ID from query parameters
            element_id = routes.get_request_args().get("element_id")
            if not element_id:
                return routes.make_response(
                    data={"error": "Missing required parameter: element_id"}, status=400
                )
            
            try:
                elem_id = DB.ElementId(int(element_id))
                element = doc.GetElement(elem_id)
                
                if not element:
                    return routes.make_response(
                        data={"error": "Wall with ID {} not found".format(element_id)}, status=404
                    )
                
                # Verify it's a wall element
                if not (hasattr(element, 'Category') and element.Category and 
                    element.Category.Id.Value == int(DB.BuiltInCategory.OST_Walls)):
                    return routes.make_response(
                        data={"error": "Element {} is not a wall".format(element_id)}, status=400
                    )
                
                # Extract wall configuration
                wall_config = _extract_wall_config(element)
                
                response_data = {
                    "message": "Successfully queried wall '{}'".format(wall_config.get("name", "Unknown")),
                    "wall_config": wall_config
                }
                
                return routes.make_response(data=response_data, status=200)
                
            except ValueError:
                return routes.make_response(
                    data={"error": "Invalid element_id format: {}".format(element_id)}, status=400
                )
            except Exception as e:
                return routes.make_response(
                    data={"error": "Failed to query wall: {}".format(str(e))}, status=500
                )
        
        except Exception as e:
            logger.error("Error in query_wall: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Internal server error: {}".format(str(e))}, status=500
            )


    @api.route("/get_wall_details/", methods=["GET"])
    @api.route("/get_wall_details", methods=["GET"])
    @api.route("/wall_details/", methods=["GET"])
    @api.route("/wall_details", methods=["GET"])
    def get_wall_details():
        """
        Get comprehensive information about selected wall elements in Revit
        
        Returns detailed information including:
        - Wall name, type, and ID information
        - Wall type properties with comprehensive details (layers, materials, thermal)
        - Location information (curve data, length, endpoints)
        - Level information and height/offset data
        - Structural properties and material assignments
        - Layer composition and thickness breakdown
        - All relevant parameters and properties
        """
        try:
            doc = revit.doc
            uidoc = revit.uidoc
            
            if not doc or not uidoc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )
            
            # Get selected element IDs
            selection = uidoc.Selection
            selected_ids = selection.GetElementIds()
            
            if not selected_ids or len(selected_ids) == 0:
                return routes.make_response(
                    data={
                        "message": "No elements currently selected",
                        "selected_count": 0,
                        "walls": []
                    }
                )
            
            walls_info = []
            
            for elem_id in selected_ids:
                try:
                    element = doc.GetElement(elem_id)
                    if not element:
                        continue
                    
                    # Check if element is a wall
                    if not (hasattr(element, 'Category') and element.Category and 
                        element.Category.Id.Value == int(DB.BuiltInCategory.OST_Walls)):
                        continue
                    
                    wall_info = {
                        "id": str(elem_id.Value),
                        "name": get_element_name(element)
                    }
                    
                    # ============ WALL TYPE INFORMATION ============
                    try:
                        wall_type = element.WallType
                        if wall_type:
                            wall_info["wall_type_name"] = get_element_name(wall_type)
                            wall_info["wall_type_id"] = str(wall_type.Id.Value)
                            
                            # Get detailed type properties
                            type_properties = _extract_wall_type_properties(wall_type)
                            wall_info["type_properties"] = type_properties
                        else:
                            wall_info["wall_type_name"] = "Unknown"
                            wall_info["wall_type_id"] = "Unknown"
                            wall_info["type_properties"] = {}
                    except Exception as e:
                        wall_info["wall_type_name"] = "Unknown"
                        wall_info["wall_type_id"] = "Unknown"
                        wall_info["type_properties"] = {}
                        wall_info["type_error"] = str(e)
                    
                    # ============ LOCATION INFORMATION ============
                    try:
                        location = element.Location
                        if hasattr(location, 'Curve') and location.Curve:
                            # Wall with curve location
                            curve = location.Curve
                            start_pt = curve.GetEndPoint(0)
                            end_pt = curve.GetEndPoint(1)
                            
                            wall_info["location_type"] = "curve"
                            wall_info["start_point"] = {
                                "x": round(start_pt.X * 304.8, 2),
                                "y": round(start_pt.Y * 304.8, 2),
                                "z": round(start_pt.Z * 304.8, 2)
                            }
                            wall_info["end_point"] = {
                                "x": round(end_pt.X * 304.8, 2),
                                "y": round(end_pt.Y * 304.8, 2),
                                "z": round(end_pt.Z * 304.8, 2)
                            }
                            wall_info["length"] = round(curve.Length * 304.8, 2)
                            
                            # Calculate direction vector
                            direction = end_pt - start_pt
                            if direction.GetLength() > 0:
                                direction = direction.Normalize()
                                wall_info["direction"] = {
                                    "x": round(direction.X, 3),
                                    "y": round(direction.Y, 3),
                                    "z": round(direction.Z, 3)
                                }
                            
                            # Midpoint
                            midpoint = (start_pt + end_pt) / 2
                            wall_info["midpoint"] = {
                                "x": round(midpoint.X * 304.8, 2),
                                "y": round(midpoint.Y * 304.8, 2),
                                "z": round(midpoint.Z * 304.8, 2)
                            }
                            
                        else:
                            wall_info["location_type"] = "unknown"
                            
                    except Exception as e:
                        wall_info["location_type"] = "error"
                        wall_info["location_error"] = str(e)
                    
                    # ============ LEVEL AND HEIGHT INFORMATION ============
                    try:
                        # Base level
                        level_param = element.get_Parameter(DB.BuiltInParameter.WALL_BASE_CONSTRAINT)
                        if level_param and level_param.HasValue:
                            level_id = level_param.AsElementId()
                            level = doc.GetElement(level_id)
                            if level:
                                wall_info["base_level"] = {
                                    "name": get_element_name(level),
                                    "id": str(level_id.Value),
                                    "elevation": round(level.Elevation * 304.8, 2)
                                }
                        
                        # Top level/constraint
                        top_param = element.get_Parameter(DB.BuiltInParameter.WALL_HEIGHT_TYPE)
                        if top_param and top_param.HasValue:
                            top_id = top_param.AsElementId()
                            if top_id.Value != -1:
                                top_level = doc.GetElement(top_id)
                                if top_level:
                                    wall_info["top_constraint"] = {
                                        "name": get_element_name(top_level),
                                        "id": str(top_id.Value),
                                        "elevation": round(top_level.Elevation * 304.8, 2)
                                    }
                        
                        # Base offset
                        base_offset_param = element.get_Parameter(DB.BuiltInParameter.WALL_BASE_OFFSET)
                        if base_offset_param and base_offset_param.HasValue:
                            wall_info["base_offset"] = round(base_offset_param.AsDouble() * 304.8, 2)
                        else:
                            wall_info["base_offset"] = 0.0
                        
                        # Top offset
                        top_offset_param = element.get_Parameter(DB.BuiltInParameter.WALL_TOP_OFFSET)
                        if top_offset_param and top_offset_param.HasValue:
                            wall_info["top_offset"] = round(top_offset_param.AsDouble() * 304.8, 2)
                        else:
                            wall_info["top_offset"] = 0.0
                        
                        # Unconnected height
                        height_param = element.get_Parameter(DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM)
                        if height_param and height_param.HasValue:
                            wall_info["unconnected_height"] = round(height_param.AsDouble() * 304.8, 2)
                        
                    except Exception as e:
                        wall_info["base_level"] = None
                        wall_info["height_error"] = str(e)
                    
                    # ============ STRUCTURAL PROPERTIES ============
                    try:
                        structural_props = {}
                        
                        # Structural usage
                        structural_param = element.get_Parameter(DB.BuiltInParameter.WALL_STRUCTURAL_SIGNIFICANT)
                        if structural_param and structural_param.HasValue:
                            structural_props["is_structural"] = structural_param.AsInteger() == 1
                        
                        # Location line
                        location_line_param = element.get_Parameter(DB.BuiltInParameter.WALL_KEY_REF_PARAM)
                        if location_line_param and location_line_param.HasValue:
                            structural_props["location_line"] = location_line_param.AsValueString()
                        
                        wall_info["structural_properties"] = structural_props
                        
                    except Exception as e:
                        wall_info["structural_properties"] = {}
                        wall_info["structural_error"] = str(e)
                    
                    # ============ ADDITIONAL PARAMETERS ============
                    additional_params = {}
                    param_names = [
                        "Mark", "Comments", "Type Comments", "Type Mark",
                        "Phasing Created", "Phasing Demolished", "Room Bounding",
                        "Area", "Volume"
                    ]
                    
                    for param_name in param_names:
                        try:
                            param = element.LookupParameter(param_name)
                            if param and param.HasValue:
                                if param.StorageType == DB.StorageType.String:
                                    value = param.AsString()
                                elif param.StorageType == DB.StorageType.Integer:
                                    value = param.AsInteger()
                                    if param_name == "Room Bounding":
                                        value = bool(value)
                                elif param.StorageType == DB.StorageType.Double:
                                    # Convert area/volume to metric
                                    if param_name == "Area":
                                        value = round(param.AsDouble() * 0.092903, 2)  # sq ft to sq m
                                    elif param_name == "Volume":
                                        value = round(param.AsDouble() * 0.0283168, 2)  # cu ft to cu m
                                    else:
                                        value = round(param.AsDouble(), 3)
                                elif param.StorageType == DB.StorageType.ElementId:
                                    elem_id_val = param.AsElementId()
                                    if elem_id_val and elem_id_val.Value != -1:
                                        ref_elem = doc.GetElement(elem_id_val)
                                        value = get_element_name(ref_elem) if ref_elem else str(elem_id_val.Value)
                                    else:
                                        value = "None"
                                else:
                                    value = str(param.AsValueString()) if param.AsValueString() else "Unknown"
                                
                                if value and str(value).strip():
                                    additional_params[param_name] = str(value).strip() if isinstance(value, str) else value
                        except:
                            continue
                    
                    wall_info["parameters"] = additional_params
                    
                    # ============ BOUNDING BOX ============
                    try:
                        bbox = element.get_BoundingBox(None)
                        if bbox:
                            wall_info["bounding_box"] = {
                                "min": {
                                    "x": round(bbox.Min.X * 304.8, 2),
                                    "y": round(bbox.Min.Y * 304.8, 2),
                                    "z": round(bbox.Min.Z * 304.8, 2)
                                },
                                "max": {
                                    "x": round(bbox.Max.X * 304.8, 2),
                                    "y": round(bbox.Max.Y * 304.8, 2),
                                    "z": round(bbox.Max.Z * 304.8, 2)
                                }
                            }
                        else:
                            wall_info["bounding_box"] = None
                    except:
                        wall_info["bounding_box"] = None
                    
                    walls_info.append(wall_info)
                    
                except Exception as e:
                    logger.warning("Could not process wall element {}: {}".format(elem_id, str(e)))
                    continue
            
            # Prepare response
            response_data = {
                "message": "Successfully retrieved {} wall elements".format(len(walls_info)),
                "selected_count": len(selected_ids),
                "walls_found": len(walls_info),
                "walls": walls_info
            }
            
            return routes.make_response(data=response_data, status=200)
            
        except Exception as e:
            logger.error("Failed to get wall details: {}".format(str(e)))
            return routes.make_response(
                data={
                    "error": "Failed to retrieve wall details: {}".format(str(e))
                },
                status=500
            )


    @api.route("/create_wall_layout/", methods=["POST"])
    @api.route("/create_wall_layout", methods=["POST"])
    def create_wall_layout():
        """
        Create multiple walls in a layout pattern
        
        Expected JSON payload:
        {
            "layout_type": "grid",  // "grid", "rectangular", or "custom"
            "level_name": "Level 1",
            "wall_configs": [  // Array of wall configurations
                {
                    "curve_points": [
                        {"x": 0, "y": 0, "z": 0},
                        {"x": 5000, "y": 0, "z": 0}
                    ],
                    "wall_type_name": "Generic - 200mm",
                    "height": 3000,
                    "mark": "W1"
                }
            ],
            "wall_type_name": "Generic - 200mm",  // Default type for all walls
            "height": 3000.0,  // Default height
            "naming_pattern": "W{}"  // Pattern for auto-naming (optional)
        }
        """
    try:
        doc = revit.doc
        if not doc:
            return routes.make_response(
                data={"error": "No active Revit document"}, status=503
            )
        
        data = routes.get_request_json()
        if not data:
            return routes.make_response(
                data={"error": "No JSON data provided"}, status=400
            )
        
        return _create_wall_layout_from_data(data)
        
    except Exception as e:
        logger.error("Error in create_wall_layout: {}".format(str(e)))
        return routes.make_response(
            data={"error": "Internal server error: {}".format(str(e))}, status=500
        )


# ============ HELPER FUNCTIONS ============

def _find_level_by_name(doc, level_name):
    """Find a level by name"""
    try:
        levels = DB.FilteredElementCollector(doc).OfClass(DB.Level).ToElements()
        for level in levels:
            if get_element_name(level) == level_name:
                return level
        return None
    except:
        return None


def _find_wall_type_by_name(doc, wall_type_name):
    """Find a wall type by name"""
    try:
        wall_types = DB.FilteredElementCollector(doc).OfClass(DB.WallType).ToElements()
        for wall_type in wall_types:
            if get_element_name(wall_type) == wall_type_name:
                return wall_type
        return None
    except:
        return None


def _create_new_wall(doc, wall_curve, level, wall_type_name, height, height_offset, top_offset, location_line, structural, properties):
    """Create a new wall"""
    try:
        # Find wall type
        wall_type = _find_wall_type_by_name(doc, wall_type_name)
        if not wall_type:
            return {"error": "Could not find wall type '{}'".format(wall_type_name)}
        
        # Create wall
        wall = DB.Wall.Create(doc, wall_curve, wall_type.Id, level.Id, height / 304.8 if height else 10.0, 0.0, False, False)
        
        if not wall:
            return {"error": "Failed to create wall instance"}
        
        # Set height offset
        if height_offset != 0.0:
            base_offset_param = wall.get_Parameter(DB.BuiltInParameter.WALL_BASE_OFFSET)
            if base_offset_param:
                base_offset_param.Set(height_offset / 304.8)
        
        # Set top offset
        if top_offset != 0.0:
            top_offset_param = wall.get_Parameter(DB.BuiltInParameter.WALL_TOP_OFFSET)
            if top_offset_param:
                top_offset_param.Set(top_offset / 304.8)
        
        # Set structural flag
        if structural:
            structural_param = wall.get_Parameter(DB.BuiltInParameter.WALL_STRUCTURAL_SIGNIFICANT)
            if structural_param:
                structural_param.Set(1)
        
        # Set location line
        if location_line != "Wall Centerline":
            _set_wall_location_line(wall, location_line)
        
        # Set additional properties
        _set_wall_properties(wall, properties)
        
        return {
            "success": True,
            "message": "Successfully created wall '{}'".format(get_element_name(wall)),
            "element_id": str(wall.Id.Value),
            "element_type": "wall",
            "wall_type_name": get_element_name(wall_type),
            "length": round(wall_curve.Length * 304.8, 2)
        }
        
    except Exception as e:
        logger.error("Failed to create new wall: {}".format(str(e)))
        return {"error": "Failed to create wall: {}".format(str(e))}


def _edit_existing_wall(doc, element_id, wall_curve, level, wall_type_name, height, height_offset, top_offset, location_line, structural, properties):
    """Edit an existing wall"""
    try:
        # Get existing wall
        elem_id = DB.ElementId(int(element_id))
        wall = doc.GetElement(elem_id)
        
        if not wall:
            # Fallback to create new wall
            return _create_new_wall(doc, wall_curve, level, wall_type_name, height, height_offset, top_offset, location_line, structural, properties)
        
        # Verify it's a wall
        if not (hasattr(wall, 'Category') and wall.Category and 
               wall.Category.Id.Value == int(DB.BuiltInCategory.OST_Walls)):
            return {"error": "Element is not a wall"}
        
        # Update wall curve (location)
        if hasattr(wall.Location, 'Curve'):
            wall.Location.Curve = wall_curve
        
        # Update wall type if specified
        if wall_type_name:
            wall_type = _find_wall_type_by_name(doc, wall_type_name)
            if wall_type:
                wall.WallType = wall_type
        
        # Update level
        level_param = wall.get_Parameter(DB.BuiltInParameter.WALL_BASE_CONSTRAINT)
        if level_param:
            level_param.Set(level.Id)
        
        # Update height
        if height:
            height_param = wall.get_Parameter(DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM)
            if height_param:
                height_param.Set(height / 304.8)
        
        # Update offsets
        if height_offset != 0.0:
            base_offset_param = wall.get_Parameter(DB.BuiltInParameter.WALL_BASE_OFFSET)
            if base_offset_param:
                base_offset_param.Set(height_offset / 304.8)
        
        if top_offset != 0.0:
            top_offset_param = wall.get_Parameter(DB.BuiltInParameter.WALL_TOP_OFFSET)
            if top_offset_param:
                top_offset_param.Set(top_offset / 304.8)
        
        # Update structural flag
        structural_param = wall.get_Parameter(DB.BuiltInParameter.WALL_STRUCTURAL_SIGNIFICANT)
        if structural_param:
            structural_param.Set(1 if structural else 0)
        
        # Set location line
        if location_line != "Wall Centerline":
            _set_wall_location_line(wall, location_line)
        
        # Set additional properties
        _set_wall_properties(wall, properties)
        
        return {
            "success": True,
            "message": "Successfully modified wall '{}'".format(get_element_name(wall)),
            "element_id": str(wall.Id.Value),
            "element_type": "wall",
            "wall_type_name": get_element_name(wall.WallType),
            "length": round(wall_curve.Length * 304.8, 2)
        }
        
    except ValueError:
        # Invalid element ID, create new wall instead
        return _create_new_wall(doc, wall_curve, level, wall_type_name, height, height_offset, top_offset, location_line, structural, properties)
    except Exception as e:
        logger.error("Failed to edit wall: {}".format(str(e)))
        return {"error": "Failed to edit wall: {}".format(str(e))}


def _set_wall_location_line(wall, location_line):
    """Set wall location line"""
    try:
        location_param = wall.get_Parameter(DB.BuiltInParameter.WALL_KEY_REF_PARAM)
        if location_param:
            # Map location line names to values
            location_map = {
                "Wall Centerline": 0,
                "Core Centerline": 1,
                "Finish Face: Exterior": 2,
                "Finish Face: Interior": 3,
                "Core Face: Exterior": 4,
                "Core Face: Interior": 5
            }
            
            if location_line in location_map:
                location_param.Set(location_map[location_line])
    except:
        pass


def _set_wall_properties(wall, properties):
    """Set additional properties on a wall"""
    if not properties:
        return
    
    for prop_name, prop_value in properties.items():
        try:
            param = wall.LookupParameter(prop_name)
            if param and not param.IsReadOnly:
                if param.StorageType == DB.StorageType.String:
                    param.Set(str(prop_value))
                elif param.StorageType == DB.StorageType.Integer:
                    param.Set(int(prop_value))
                elif param.StorageType == DB.StorageType.Double:
                    param.Set(float(prop_value))
        except:
            continue


def _create_wall_from_data(wall_data):
    """Create wall from data dictionary - external interface"""
    try:
        doc = revit.doc
        if not doc:
            return routes.make_response(
                data={"error": "No active Revit document"}, status=503
            )
        
        with DB.Transaction(doc, "Create Wall") as trans:
            trans.Start()
            
            try:
                result = _create_wall_from_data_internal(doc, wall_data)
                trans.Commit()
                return routes.make_response(data=result, status=200)
            except Exception as e:
                trans.RollBack()
                logger.error("Failed to create wall: {}".format(str(e)))
                return routes.make_response(
                    data={"error": "Failed to create wall: {}".format(str(e))}, status=500
                )
    
    except Exception as e:
        logger.error("Error in _create_wall_from_data: {}".format(str(e)))
        return routes.make_response(
            data={"error": "Internal server error: {}".format(str(e))}, status=500
        )


def _create_wall_from_data_internal(doc, wall_data):
    """Create wall from data dictionary - internal function"""
    try:
        # Find level
        level = _find_level_by_name(doc, wall_data["level_name"])
        if not level:
            return {"error": "Level '{}' not found".format(wall_data["level_name"])}
        
        # Convert curve points
        curve_points = wall_data["curve_points"]
        if len(curve_points) < 2:
            return {"error": "Need at least 2 points to create wall"}
        
        # Convert to Revit points
        revit_points = []
        for point in curve_points:
            revit_pt = DB.XYZ(
                point["x"] / 304.8,
                point["y"] / 304.8,
                point["z"] / 304.8
            )
            revit_points.append(revit_pt)
        
        # Create wall curve
        if len(revit_points) == 2:
            wall_curve = DB.Line.CreateBound(revit_points[0], revit_points[1])
        else:
            # For now, just use first two points
            wall_curve = DB.Line.CreateBound(revit_points[0], revit_points[1])
        
        # Create wall
        return _create_new_wall(
            doc, wall_curve, level,
            wall_data.get("wall_type_name", "Generic - 200mm"),
            wall_data.get("height"),
            wall_data.get("height_offset", 0.0),
            wall_data.get("top_offset", 0.0),
            wall_data.get("location_line", "Wall Centerline"),
            wall_data.get("structural", False),
            wall_data.get("properties", {})
        )
        
    except Exception as e:
        logger.error("Failed to create wall from data: {}".format(str(e)))
        return {"error": "Failed to create wall: {}".format(str(e))}


def _create_wall_layout_from_data(data):
    """Create multiple walls from layout data"""
    try:
        doc = revit.doc
        if not doc:
            return routes.make_response(
                data={"error": "No active Revit document"}, status=503
            )
        
        # Validate required parameters
        required_params = ["level_name", "wall_configs"]
        for param in required_params:
            if param not in data:
                return routes.make_response(
                    data={"error": "Missing required parameter: {}".format(param)}, status=400
                )
        
        wall_configs = data["wall_configs"]
        if not isinstance(wall_configs, list) or len(wall_configs) == 0:
            return routes.make_response(
                data={"error": "wall_configs must be a non-empty list"}, status=400
            )
        
        # Extract common parameters
        level_name = data["level_name"]
        default_wall_type = data.get("wall_type_name", "Generic - 200mm")
        default_height = data.get("height")
        naming_pattern = data.get("naming_pattern", "W{}")
        
        # Start transaction
        with DB.Transaction(doc, "Create Wall Layout") as trans:
            trans.Start()
            
            try:
                created_walls = []
                
                for i, wall_config in enumerate(wall_configs):
                    try:
                        # Prepare wall data
                        wall_data = {
                            "level_name": level_name,
                            "curve_points": wall_config.get("curve_points"),
                            "wall_type_name": wall_config.get("wall_type_name", default_wall_type),
                            "height": wall_config.get("height", default_height),
                            "height_offset": wall_config.get("height_offset", 0.0),
                            "top_offset": wall_config.get("top_offset", 0.0),
                            "location_line": wall_config.get("location_line", "Wall Centerline"),
                            "structural": wall_config.get("structural", False),
                            "properties": wall_config.get("properties", {})
                        }
                        
                        # Auto-generate mark if not provided
                        if "mark" not in wall_data["properties"] and "mark" not in wall_config:
                            if "{}" in naming_pattern:
                                wall_data["properties"]["Mark"] = naming_pattern.format(i + 1)
                        elif "mark" in wall_config:
                            wall_data["properties"]["Mark"] = wall_config["mark"]
                        
                        # Create wall
                        result = _create_wall_from_data_internal(doc, wall_data)
                        if result.get("success"):
                            created_walls.append(result)
                        
                    except Exception as e:
                        logger.warning("Failed to create wall {}: {}".format(i + 1, str(e)))
                        continue
                
                trans.Commit()
                
                response_data = {
                    "message": "Successfully created {} walls out of {} requested".format(
                        len(created_walls), len(wall_configs)
                    ),
                    "created_count": len(created_walls),
                    "requested_count": len(wall_configs),
                    "walls": created_walls
                }
                
                return routes.make_response(data=response_data, status=200)
                
            except Exception as e:
                trans.RollBack()
                logger.error("Failed to create wall layout: {}".format(str(e)))
                return routes.make_response(
                    data={"error": "Failed to create wall layout: {}".format(str(e))}, status=500
                )
    
    except Exception as e:
        logger.error("Error in _create_wall_layout_from_data: {}".format(str(e)))
        return routes.make_response(
            data={"error": "Internal server error: {}".format(str(e))}, status=500
        )


def _extract_wall_config(wall):
    """Extract wall configuration from an existing wall element"""
    try:
        config = {
            "element_id": str(wall.Id.Value),
            "name": get_element_name(wall)
        }
        
        # Wall type information
        if hasattr(wall, 'WallType') and wall.WallType:
            config["wall_type_name"] = get_element_name(wall.WallType)
            config["wall_type_id"] = str(wall.WallType.Id.Value)
        
        # Location information
        if hasattr(wall.Location, 'Curve') and wall.Location.Curve:
            curve = wall.Location.Curve
            start_pt = curve.GetEndPoint(0)
            end_pt = curve.GetEndPoint(1)
            
            config["curve_points"] = [
                {
                    "x": round(start_pt.X * 304.8, 2),
                    "y": round(start_pt.Y * 304.8, 2),
                    "z": round(start_pt.Z * 304.8, 2)
                },
                {
                    "x": round(end_pt.X * 304.8, 2),
                    "y": round(end_pt.Y * 304.8, 2),
                    "z": round(end_pt.Z * 304.8, 2)
                }
            ]
            config["length"] = round(curve.Length * 304.8, 2)
        
        # Level information
        level_param = wall.get_Parameter(DB.BuiltInParameter.WALL_BASE_CONSTRAINT)
        if level_param and level_param.HasValue:
            level_id = level_param.AsElementId()
            level = wall.Document.GetElement(level_id)
            if level:
                config["level_name"] = get_element_name(level)
                config["base_elevation"] = round(level.Elevation * 304.8, 2)
        
        # Height information
        height_param = wall.get_Parameter(DB.BuiltInParameter.WALL_USER_HEIGHT_PARAM)
        if height_param and height_param.HasValue:
            config["height"] = round(height_param.AsDouble() * 304.8, 2)
        
        # Base offset
        base_offset_param = wall.get_Parameter(DB.BuiltInParameter.WALL_BASE_OFFSET)
        if base_offset_param and base_offset_param.HasValue:
            config["height_offset"] = round(base_offset_param.AsDouble() * 304.8, 2)
        
        # Top offset
        top_offset_param = wall.get_Parameter(DB.BuiltInParameter.WALL_TOP_OFFSET)
        if top_offset_param and top_offset_param.HasValue:
            config["top_offset"] = round(top_offset_param.AsDouble() * 304.8, 2)
        
        # Structural flag
        structural_param = wall.get_Parameter(DB.BuiltInParameter.WALL_STRUCTURAL_SIGNIFICANT)
        if structural_param and structural_param.HasValue:
            config["structural"] = structural_param.AsInteger() == 1
        
        # Location line
        location_param = wall.get_Parameter(DB.BuiltInParameter.WALL_KEY_REF_PARAM)
        if location_param and location_param.HasValue:
            config["location_line"] = location_param.AsValueString()
        
        # Additional parameters
        additional_params = {}
        for param_name in ["Mark", "Comments"]:
            param = wall.LookupParameter(param_name)
            if param and param.HasValue:
                if param.StorageType == DB.StorageType.String:
                    additional_params[param_name] = param.AsString()
        
        config["properties"] = additional_params
        
        return config
        
    except Exception as e:
        logger.error("Failed to extract wall config: {}".format(str(e)))
        raise


def _extract_wall_type_properties(wall_type):
    """Extract comprehensive type properties from a wall type"""
    try:
        type_properties = {}
        
        # ============ BASIC TYPE INFORMATION ============
        type_properties["type_name"] = get_element_name(wall_type)
        type_properties["category"] = wall_type.Category.Name if wall_type.Category else "Unknown"
        type_properties["kind"] = str(wall_type.Kind) if hasattr(wall_type, 'Kind') else "Unknown"
        
        # ============ WALL STRUCTURE AND LAYERS ============
        layers_info = []
        total_thickness = 0.0
        
        try:
            compound_structure = wall_type.GetCompoundStructure()
            if compound_structure:
                layers = compound_structure.GetLayers()
                
                for i, layer in enumerate(layers):
                    layer_info = {
                        "index": i,
                        "thickness": round(layer.Width * 304.8, 2),  # Convert to mm
                        "function": str(layer.Function) if hasattr(layer, 'Function') else "Unknown"
                    }
                    
                    # Get layer material
                    try:
                        material_id = layer.MaterialId
                        if material_id and material_id.Value != -1:
                            material = wall_type.Document.GetElement(material_id)
                            if material:
                                layer_info["material"] = {
                                    "name": get_element_name(material),
                                    "id": str(material_id.Value)
                                }
                                
                                # Get material properties
                                material_props = _extract_material_properties(material)
                                layer_info["material"]["properties"] = material_props
                    except:
                        layer_info["material"] = {"name": "Unknown", "id": "Unknown"}
                    
                    layers_info.append(layer_info)
                    total_thickness += layer.Width
                
                type_properties["layers"] = layers_info
                type_properties["total_thickness"] = round(total_thickness * 304.8, 2)  # Convert to mm
                
                # Structure information
                type_properties["structure"] = {
                    "layer_count": len(layers),
                    "has_core": compound_structure.HasStructuralDeck(),
                    "variable_thickness": compound_structure.IsVerticallyHomogeneous() == False
                }
            else:
                type_properties["layers"] = []
                type_properties["total_thickness"] = 0.0
                type_properties["structure"] = {"layer_count": 0}
                
        except Exception as e:
            type_properties["layers"] = []
            type_properties["structure_error"] = str(e)
        
        # ============ THERMAL PROPERTIES ============
        thermal = {}
        
        thermal_param_names = [
            "Heat Transfer Coefficient (U)", "Thermal Resistance (R)", 
            "Thermal Mass", "Absorptance", "Roughness"
        ]
        
        for param_name in thermal_param_names:
            try:
                param = wall_type.LookupParameter(param_name)
                if param and param.HasValue:
                    if param.StorageType == DB.StorageType.Double:
                        thermal[param_name.lower().replace(" ", "_").replace("(", "").replace(")", "")] = round(param.AsDouble(), 3)
                    elif param.StorageType == DB.StorageType.String:
                        thermal[param_name.lower().replace(" ", "_").replace("(", "").replace(")", "")] = param.AsString()
            except:
                continue
        
        type_properties["thermal"] = thermal
        
        # ============ IDENTITY DATA ============
        identity = {}
        
        identity_param_names = [
            "Type Name", "Type Comments", "Type Mark", "Type Image", "Description", 
            "Assembly Code", "Assembly Description", "Keynote", "Model", "Manufacturer", 
            "Cost", "URL", "Fire Rating"
        ]
        
        for param_name in identity_param_names:
            try:
                param = wall_type.LookupParameter(param_name)
                if param and param.HasValue:
                    if param.StorageType == DB.StorageType.String:
                        value = param.AsString()
                        if value and value.strip():
                            identity[param_name.lower().replace(" ", "_")] = value.strip()
                    elif param.StorageType == DB.StorageType.Double:
                        identity[param_name.lower().replace(" ", "_")] = round(param.AsDouble(), 2)
                    elif param.StorageType == DB.StorageType.Integer:
                        identity[param_name.lower().replace(" ", "_")] = param.AsInteger()
            except:
                continue
        
        type_properties["identity"] = identity
        
        # ============ ADDITIONAL TYPE PARAMETERS ============
        additional = {}
        
        # Get all parameters not already captured
        try:
            for param in wall_type.Parameters:
                param_name = param.Definition.Name
                
                # Skip if already captured in other sections
                skip_params = ["Element ID", "Type ID", "Type Name", "Category"]
                if param_name in skip_params:
                    continue
                
                # Skip if already in other sections
                if any(param_name.lower().replace(" ", "_") in section for section in [thermal, identity]):
                    continue
                
                try:
                    if param.HasValue:
                        if param.StorageType == DB.StorageType.String:
                            value = param.AsString()
                            if value and value.strip():
                                additional[param_name.lower().replace(" ", "_")] = value.strip()
                        elif param.StorageType == DB.StorageType.Double:
                            additional[param_name.lower().replace(" ", "_")] = round(param.AsDouble(), 3)
                        elif param.StorageType == DB.StorageType.Integer:
                            additional[param_name.lower().replace(" ", "_")] = param.AsInteger()
                        elif param.StorageType == DB.StorageType.ElementId:
                            elem_id = param.AsElementId()
                            if elem_id and elem_id.Value != -1:
                                elem = wall_type.Document.GetElement(elem_id)
                                additional[param_name.lower().replace(" ", "_")] = get_element_name(elem) if elem else str(elem_id.Value)
                except:
                    continue
        except:
            pass
        
        type_properties["additional_parameters"] = additional
        
        return type_properties
        
    except Exception as e:
        logger.warning("Could not extract wall type properties: {}".format(str(e)))
        return {
            "error": str(e),
            "layers": [],
            "structure": {},
            "thermal": {},
            "identity": {},
            "additional_parameters": {}
        }


def _extract_material_properties(material):
    """Extract material properties from a material element"""
    try:
        material_props = {}
        
        # Material property parameters
        prop_param_names = [
            "Young's Modulus", "Poisson Ratio", "Shear Modulus", "Density", 
            "Thermal Expansion Coefficient", "Damping Ratio", "Unit Weight",
            "Compressive Strength", "Tensile Strength", "Yield Strength",
            "Thermal Conductivity", "Specific Heat", "Emissivity", "Permeability"
        ]
        
        for param_name in prop_param_names:
            try:
                param = material.LookupParameter(param_name)
                if param and param.HasValue:
                    if param.StorageType == DB.StorageType.Double:
                        value = param.AsDouble()
                        if param_name in ["Density", "Unit Weight"]:
                            # Convert to kg/m³
                            material_props[param_name.lower().replace(" ", "_")] = round(value * 16.0185, 2)
                        elif param_name in ["Compressive Strength", "Tensile Strength", "Yield Strength"]:
                            # Convert to MPa
                            material_props[param_name.lower().replace(" ", "_")] = round(value * 0.00689476, 2)  # psi to MPa
                        elif param_name in ["Young's Modulus"]:
                            # Convert to MPa
                            material_props[param_name.lower().replace("'", "").replace(" ", "_")] = round(value * 0.00689476, 2)
                        else:
                            material_props[param_name.lower().replace("'", "").replace(" ", "_")] = round(value, 3)
                    elif param.StorageType == DB.StorageType.String:
                        material_props[param_name.lower().replace("'", "").replace(" ", "_")] = param.AsString()
            except:
                continue
        
        return material_props
        
    except Exception as e:
        logger.warning("Could not extract material properties: {}".format(str(e)))
        return {"error": str(e)} 