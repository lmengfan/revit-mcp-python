# -*- coding: utf-8 -*-
"""
Structural Beam Management for Revit MCP

This module provides comprehensive functionality for creating, editing, and querying
structural framing elements (beams) in Revit. It handles beam placement, modification,
type properties, and detailed information extraction.

Key Features:
- Create and edit structural beams with full parametric control
- Place beams between points, along curves, or at specific locations
- Query beam properties and extract detailed type information
- Support for various beam families (steel, concrete, timber, etc.)
- Comprehensive type property extraction including dimensions, materials, and structural data
- Grid-based beam placement and layout generation
- Unit conversion between metric (mm) and Revit internal units (feet)

Routes:
- /create_or_edit_beam/ - Create new or edit existing structural beams
- /create_beam_along_curve/ - Create beam following a curve path
- /place_beam_between_points/ - Place beam between two specific points
- /query_beam/ - Get basic beam information by ID
- /get_beam_details/ - Get comprehensive beam details from selection
- /create_beam_layout/ - Create multiple beams in a layout pattern
- /place_beams_on_grids/ - Place beams along grid lines
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


def register_beam_management_routes(api):
    """Register all beam management routes with the API"""
    if not api:
        logger.error("No API instance provided for beam management routes")
        return
    
    logger.info("Registering beam management routes...")
    
    logger.info("Beam management routes registered successfully")


    @api.route("/create_or_edit_beam/", methods=["POST"])
    @api.route("/create_or_edit_beam", methods=["POST"])
    def create_or_edit_beam():
        """
        Create a new structural beam or edit an existing one
        
        This endpoint can operate in two modes:
        1. Creation Mode (when element_id is None): Creates a new beam
        2. Edit Mode (when element_id is provided): Modifies an existing beam
        
        Expected JSON payload:
        {
            "element_id": "123456",  // Optional - for editing existing beam
            "level_name": "Level 1",  // Required - target level name
            "start_point": {"x": 0, "y": 0, "z": 0},  // Required - start point in mm
            "end_point": {"x": 5000, "y": 0, "z": 0},  // Required - end point in mm
            "family_name": "W-Wide Flange",  // Optional - beam family name
            "type_name": "W12X26",  // Optional - beam type name
            "structural_usage": "Beam",  // Optional - Beam, Girder, Joist, Other
            "height_offset": 0.0,  // Optional - offset from level in mm
            "rotation": 0.0,  // Optional - rotation angle in degrees
            "properties": {  // Optional - additional parameters
                "Mark": "B1",
                "Comments": "Steel beam"
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
            required_params = ["level_name", "start_point", "end_point"]
            for param in required_params:
                if param not in data:
                    return routes.make_response(
                        data={"error": "Missing required parameter: {}".format(param)}, status=400
                    )
            
            # Extract parameters
            element_id = data.get("element_id")
            level_name = data["level_name"]
            start_point = data["start_point"]
            end_point = data["end_point"]
            family_name = data.get("family_name", "W-Wide Flange")
            type_name = data.get("type_name")
            structural_usage = data.get("structural_usage", "Beam")
            height_offset = data.get("height_offset", 0.0)
            rotation = data.get("rotation", 0.0)
            properties = data.get("properties", {})
            
            # Validate point data
            for point_name, point_data in [("start_point", start_point), ("end_point", end_point)]:
                if not isinstance(point_data, dict) or not all(k in point_data for k in ["x", "y", "z"]):
                    return routes.make_response(
                        data={"error": "Invalid {} format. Expected dict with x, y, z keys".format(point_name)}, status=400
                    )
            
            # Start transaction
            with DB.Transaction(doc, "Create or Edit Structural Beam") as trans:
                trans.Start()
                
                try:
                    # Find target level
                    level = _find_level_by_name(doc, level_name)
                    if not level:
                        return routes.make_response(
                            data={"error": "Level '{}' not found".format(level_name)}, status=404
                        )
                    
                    # Convert points from mm to feet
                    start_pt = DB.XYZ(
                        start_point["x"] / 304.8,
                        start_point["y"] / 304.8,
                        (start_point["z"] + height_offset) / 304.8
                    )
                    end_pt = DB.XYZ(
                        end_point["x"] / 304.8,
                        end_point["y"] / 304.8,
                        (end_point["z"] + height_offset) / 304.8
                    )
                    
                    # Create curve for beam
                    if start_pt.IsAlmostEqualTo(end_pt):
                        return routes.make_response(
                            data={"error": "Start and end points cannot be the same"}, status=400
                        )
                    
                    beam_curve = DB.Line.CreateBound(start_pt, end_pt)
                    
                    if element_id:
                        # Edit existing beam
                        result = _edit_existing_beam(
                            doc, element_id, beam_curve, level, family_name, type_name,
                            structural_usage, rotation, properties
                        )
                    else:
                        # Create new beam
                        result = _create_new_beam(
                            doc, beam_curve, level, family_name, type_name,
                            structural_usage, rotation, properties
                        )
                    
                    trans.Commit()
                    return routes.make_response(data=result, status=200)
                    
                except Exception as e:
                    trans.RollBack()
                    logger.error("Failed to create/edit beam: {}".format(str(e)))
                    return routes.make_response(
                        data={"error": "Failed to create/edit beam: {}".format(str(e))}, status=500
                    )
        
        except Exception as e:
            logger.error("Error in create_or_edit_beam: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Internal server error: {}".format(str(e))}, status=500
            )


    @api.route("/place_beam_between_points/", methods=["POST"])
    @api.route("/place_beam_between_points", methods=["POST"])
    def place_beam_between_points():
        """
        Place a structural beam between two specific points
        
        Expected JSON payload:
        {
            "point1": {"x": 0, "y": 0, "z": 3000},  // First point in mm
            "point2": {"x": 5000, "y": 0, "z": 3000},  // Second point in mm
            "level_name": "Level 1",  // Target level
            "family_name": "W-Wide Flange",  // Optional
            "type_name": "W12X26",  // Optional
            "mark": "B1",  // Optional beam mark
            "structural_usage": "Beam"  // Optional
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
            required_params = ["point1", "point2", "level_name"]
            for param in required_params:
                if param not in data:
                    return routes.make_response(
                        data={"error": "Missing required parameter: {}".format(param)}, status=400
                    )
            
            # Convert to create_or_edit_beam format
            beam_data = {
                "level_name": data["level_name"],
                "start_point": data["point1"],
                "end_point": data["point2"],
                "family_name": data.get("family_name", "W-Wide Flange"),
                "type_name": data.get("type_name"),
                "structural_usage": data.get("structural_usage", "Beam"),
                "properties": {}
            }
            
            # Add mark if provided
            if "mark" in data:
                beam_data["properties"]["Mark"] = data["mark"]
            
            # Use the main create function
            return _create_beam_from_data(beam_data)
            
        except Exception as e:
            logger.error("Error in place_beam_between_points: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Internal server error: {}".format(str(e))}, status=500
            )


    @api.route("/query_beam/", methods=["GET"])
    @api.route("/query_beam", methods=["GET"])
    def query_beam():
        """
        Query basic information about a structural beam by element ID
        
        Query parameters:
        - element_id: The element ID of the beam to query
        
        Returns basic beam information including name, type, location, and key properties
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
                        data={"error": "Beam with ID {} not found".format(element_id)}, status=404
                    )
                
                # Verify it's a structural framing element
                if not (hasattr(element, 'Category') and element.Category and 
                    element.Category.Id.Value == int(DB.BuiltInCategory.OST_StructuralFraming)):
                    return routes.make_response(
                        data={"error": "Element {} is not a structural framing element".format(element_id)}, status=400
                    )
                
                # Extract beam configuration
                beam_config = _extract_beam_config(element)
                
                response_data = {
                    "message": "Successfully queried beam '{}'".format(beam_config.get("name", "Unknown")),
                    "beam_config": beam_config
                }
                
                return routes.make_response(data=response_data, status=200)
                
            except ValueError:
                return routes.make_response(
                    data={"error": "Invalid element_id format: {}".format(element_id)}, status=400
                )
            except Exception as e:
                return routes.make_response(
                    data={"error": "Failed to query beam: {}".format(str(e))}, status=500
                )
        
        except Exception as e:
            logger.error("Error in query_beam: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Internal server error: {}".format(str(e))}, status=500
            )


    @api.route("/get_beam_details/", methods=["GET"])
    @api.route("/get_beam_details", methods=["GET"])
    @api.route("/beam_details/", methods=["GET"])
    @api.route("/beam_details", methods=["GET"])
    def get_beam_details():
        """
        Get comprehensive information about selected structural beam elements in Revit
        
        Returns detailed information including:
        - Beam name, type, and ID information
        - Family and type properties with comprehensive details
        - Location information (start/end points, curve data)
        - Level information and height offsets
        - Structural usage and material properties
        - Cross-sectional properties and dimensions
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
                        "beams": []
                    }
                )
            
            beams_info = []
            
            for elem_id in selected_ids:
                try:
                    element = doc.GetElement(elem_id)
                    if not element:
                        continue
                    
                    # Check if element is a structural framing element (beam)
                    if not (hasattr(element, 'Category') and element.Category and 
                        element.Category.Id.Value == int(DB.BuiltInCategory.OST_StructuralFraming)):
                        continue
                    
                    beam_info = {
                        "id": str(elem_id.Value),
                        "name": get_element_name(element)
                    }
                    
                    # ============ FAMILY AND TYPE INFORMATION ============
                    try:
                        symbol = element.Symbol
                        if symbol:
                            beam_info["family_name"] = get_element_name(symbol.Family)
                            beam_info["type_name"] = get_element_name(symbol)
                            beam_info["type_id"] = str(symbol.Id.Value)
                            
                            # Get detailed type properties
                            type_properties = _extract_beam_type_properties(symbol)
                            beam_info["type_properties"] = type_properties
                        else:
                            beam_info["family_name"] = "Unknown"
                            beam_info["type_name"] = "Unknown"
                            beam_info["type_id"] = "Unknown"
                            beam_info["type_properties"] = {}
                    except Exception as e:
                        beam_info["family_name"] = "Unknown"
                        beam_info["type_name"] = "Unknown"
                        beam_info["type_id"] = "Unknown"
                        beam_info["type_properties"] = {}
                        beam_info["type_error"] = str(e)
                    
                    # ============ LOCATION INFORMATION ============
                    try:
                        location = element.Location
                        if hasattr(location, 'Curve') and location.Curve:
                            # Beam with curve location
                            curve = location.Curve
                            start_pt = curve.GetEndPoint(0)
                            end_pt = curve.GetEndPoint(1)
                            
                            beam_info["location_type"] = "curve"
                            beam_info["start_point"] = {
                                "x": round(start_pt.X * 304.8, 2),
                                "y": round(start_pt.Y * 304.8, 2),
                                "z": round(start_pt.Z * 304.8, 2)
                            }
                            beam_info["end_point"] = {
                                "x": round(end_pt.X * 304.8, 2),
                                "y": round(end_pt.Y * 304.8, 2),
                                "z": round(end_pt.Z * 304.8, 2)
                            }
                            beam_info["length"] = round(curve.Length * 304.8, 2)
                            
                            # Calculate direction vector
                            direction = end_pt - start_pt
                            if direction.GetLength() > 0:
                                direction = direction.Normalize()
                                beam_info["direction"] = {
                                    "x": round(direction.X, 3),
                                    "y": round(direction.Y, 3),
                                    "z": round(direction.Z, 3)
                                }
                            
                            # Midpoint
                            midpoint = (start_pt + end_pt) / 2
                            beam_info["midpoint"] = {
                                "x": round(midpoint.X * 304.8, 2),
                                "y": round(midpoint.Y * 304.8, 2),
                                "z": round(midpoint.Z * 304.8, 2)
                            }
                            
                        elif hasattr(location, 'Point') and location.Point:
                            # Point-based location (rare for beams)
                            point = location.Point
                            beam_info["location_type"] = "point"
                            beam_info["point"] = {
                                "x": round(point.X * 304.8, 2),
                                "y": round(point.Y * 304.8, 2),
                                "z": round(point.Z * 304.8, 2)
                            }
                        else:
                            beam_info["location_type"] = "unknown"
                            
                    except Exception as e:
                        beam_info["location_type"] = "error"
                        beam_info["location_error"] = str(e)
                    
                    # ============ LEVEL INFORMATION ============
                    try:
                        level_param = element.get_Parameter(DB.BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM)
                        if level_param and level_param.HasValue:
                            level_id = level_param.AsElementId()
                            level = doc.GetElement(level_id)
                            if level:
                                beam_info["level"] = {
                                    "name": get_element_name(level),
                                    "id": str(level_id.Value),
                                    "elevation": round(level.Elevation * 304.8, 2)
                                }
                        
                        # Height offset from level
                        offset_param = element.get_Parameter(DB.BuiltInParameter.Z_OFFSET_VALUE)
                        if offset_param and offset_param.HasValue:
                            beam_info["height_offset"] = round(offset_param.AsDouble() * 304.8, 2)
                        else:
                            beam_info["height_offset"] = 0.0
                            
                    except Exception as e:
                        beam_info["level"] = None
                        beam_info["height_offset"] = 0.0
                        beam_info["level_error"] = str(e)
                    
                    # ============ STRUCTURAL PROPERTIES ============
                    try:
                        structural_props = {}
                        
                        # Structural usage
                        usage_param = element.get_Parameter(DB.BuiltInParameter.INSTANCE_STRUCT_USAGE_PARAM)
                        if usage_param and usage_param.HasValue:
                            structural_props["usage"] = str(usage_param.AsValueString())
                        
                        # Material
                        material_param = element.get_Parameter(DB.BuiltInParameter.STRUCTURAL_MATERIAL_PARAM)
                        if material_param and material_param.HasValue:
                            material_id = material_param.AsElementId()
                            if material_id and material_id.Value != -1:
                                material = doc.GetElement(material_id)
                                if material:
                                    structural_props["material"] = {
                                        "name": get_element_name(material),
                                        "id": str(material_id.Value)
                                    }
                        
                        beam_info["structural_properties"] = structural_props
                        
                    except Exception as e:
                        beam_info["structural_properties"] = {}
                        beam_info["structural_error"] = str(e)
                    
                    # ============ ADDITIONAL PARAMETERS ============
                    additional_params = {}
                    param_names = [
                        "Mark", "Comments", "Type Comments", "Type Mark",
                        "Phasing Created", "Phasing Demolished", "Start Extension", "End Extension",
                        "Start Level Offset", "End Level Offset", "Reference Level"
                    ]
                    
                    for param_name in param_names:
                        try:
                            param = element.LookupParameter(param_name)
                            if param and param.HasValue:
                                if param.StorageType == DB.StorageType.String:
                                    value = param.AsString()
                                elif param.StorageType == DB.StorageType.Integer:
                                    value = param.AsInteger()
                                elif param.StorageType == DB.StorageType.Double:
                                    # Convert length parameters to mm
                                    if "offset" in param_name.lower() or "extension" in param_name.lower():
                                        value = round(param.AsDouble() * 304.8, 2)
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
                                    additional_params[param_name] = str(value).strip()
                        except:
                            continue
                    
                    beam_info["parameters"] = additional_params
                    
                    # ============ BOUNDING BOX ============
                    try:
                        bbox = element.get_BoundingBox(None)
                        if bbox:
                            beam_info["bounding_box"] = {
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
                            beam_info["bounding_box"] = None
                    except:
                        beam_info["bounding_box"] = None
                    
                    beams_info.append(beam_info)
                    
                except Exception as e:
                    logger.warning("Could not process beam element {}: {}".format(elem_id, str(e)))
                    continue
            
            # Prepare response
            response_data = {
                "message": "Successfully retrieved {} beam elements".format(len(beams_info)),
                "selected_count": len(selected_ids),
                "beams_found": len(beams_info),
                "beams": beams_info
            }
            
            return routes.make_response(data=response_data, status=200)
            
        except Exception as e:
            logger.error("Failed to get beam details: {}".format(str(e)))
            return routes.make_response(
                data={
                    "error": "Failed to retrieve beam details: {}".format(str(e))
                },
                status=500
            )


    @api.route("/create_beam_layout/", methods=["POST"])
    @api.route("/create_beam_layout", methods=["POST"])
    def create_beam_layout():
        """
        Create multiple beams in a layout pattern
        
        Expected JSON payload:
        {
            "layout_type": "grid",  // "grid", "radial", or "custom"
            "level_name": "Level 1",
            "beam_configs": [  // Array of beam configurations
                {
                    "start_point": {"x": 0, "y": 0, "z": 3000},
                    "end_point": {"x": 5000, "y": 0, "z": 3000},
                    "type_name": "W12X26",
                    "mark": "B1"
                }
            ],
            "family_name": "W-Wide Flange",  // Default family for all beams
            "structural_usage": "Beam",  // Default usage
            "naming_pattern": "B{}"  // Pattern for auto-naming (optional)
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
        required_params = ["level_name", "beam_configs"]
        for param in required_params:
            if param not in data:
                return routes.make_response(
                    data={"error": "Missing required parameter: {}".format(param)}, status=400
                )
        
        beam_configs = data["beam_configs"]
        if not isinstance(beam_configs, list) or len(beam_configs) == 0:
            return routes.make_response(
                data={"error": "beam_configs must be a non-empty list"}, status=400
            )
        
        # Extract common parameters
        level_name = data["level_name"]
        family_name = data.get("family_name", "W-Wide Flange")
        structural_usage = data.get("structural_usage", "Beam")
        naming_pattern = data.get("naming_pattern", "B{}")
        
        # Start transaction
        with DB.Transaction(doc, "Create Beam Layout") as trans:
            trans.Start()
            
            try:
                created_beams = []
                
                for i, beam_config in enumerate(beam_configs):
                    try:
                        # Prepare beam data
                        beam_data = {
                            "level_name": level_name,
                            "start_point": beam_config.get("start_point"),
                            "end_point": beam_config.get("end_point"),
                            "family_name": beam_config.get("family_name", family_name),
                            "type_name": beam_config.get("type_name"),
                            "structural_usage": beam_config.get("structural_usage", structural_usage),
                            "properties": beam_config.get("properties", {})
                        }
                        
                        # Auto-generate mark if not provided
                        if "mark" not in beam_data["properties"] and "mark" not in beam_config:
                            if "{}" in naming_pattern:
                                beam_data["properties"]["Mark"] = naming_pattern.format(i + 1)
                        elif "mark" in beam_config:
                            beam_data["properties"]["Mark"] = beam_config["mark"]
                        
                        # Create beam
                        result = _create_beam_from_data_internal(doc, beam_data)
                        if result.get("success"):
                            created_beams.append(result)
                        
                    except Exception as e:
                        logger.warning("Failed to create beam {}: {}".format(i + 1, str(e)))
                        continue
                
                trans.Commit()
                
                response_data = {
                    "message": "Successfully created {} beams out of {} requested".format(
                        len(created_beams), len(beam_configs)
                    ),
                    "created_count": len(created_beams),
                    "requested_count": len(beam_configs),
                    "beams": created_beams
                }
                
                return routes.make_response(data=response_data, status=200)
                
            except Exception as e:
                trans.RollBack()
                logger.error("Failed to create beam layout: {}".format(str(e)))
                return routes.make_response(
                    data={"error": "Failed to create beam layout: {}".format(str(e))}, status=500
                )
    
    except Exception as e:
        logger.error("Error in create_beam_layout: {}".format(str(e)))
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


def _create_new_beam(doc, beam_curve, level, family_name, type_name, structural_usage, rotation, properties):
    """Create a new structural beam"""
    try:
        # Find beam family symbol
        symbol = find_family_symbol_safely(doc, family_name, type_name, DB.BuiltInCategory.OST_StructuralFraming)
        if not symbol:
            return {"error": "Could not find beam family '{}' type '{}'".format(family_name, type_name or "default")}
        
        # Ensure symbol is active
        if not symbol.IsActive:
            symbol.Activate()
            doc.Regenerate()
        
        # Create beam instance
        beam = doc.Create.NewFamilyInstance(beam_curve, symbol, level, DB.Structure.StructuralType.Beam)
        
        if not beam:
            return {"error": "Failed to create beam instance"}
        
        # Set structural usage
        if structural_usage:
            _set_structural_usage(beam, structural_usage)
        
        # Apply rotation if specified
        if rotation != 0.0:
            _apply_beam_rotation(beam, rotation)
        
        # Set additional properties
        _set_beam_properties(beam, properties)
        
        return {
            "success": True,
            "message": "Successfully created beam '{}'".format(get_element_name(beam)),
            "element_id": str(beam.Id.Value),
            "element_type": "beam",
            "family_name": get_element_name(symbol.Family),
            "type_name": get_element_name(symbol),
            "length": round(beam_curve.Length * 304.8, 2)
        }
        
    except Exception as e:
        logger.error("Failed to create new beam: {}".format(str(e)))
        return {"error": "Failed to create beam: {}".format(str(e))}


def _edit_existing_beam(doc, element_id, beam_curve, level, family_name, type_name, structural_usage, rotation, properties):
    """Edit an existing structural beam"""
    try:
        # Get existing beam
        elem_id = DB.ElementId(int(element_id))
        beam = doc.GetElement(elem_id)
        
        if not beam:
            # Fallback to create new beam
            return _create_new_beam(doc, beam_curve, level, family_name, type_name, structural_usage, rotation, properties)
        
        # Verify it's a structural framing element
        if not (hasattr(beam, 'Category') and beam.Category and 
               beam.Category.Id.Value == int(DB.BuiltInCategory.OST_StructuralFraming)):
            return {"error": "Element is not a structural framing element"}
        
        # Update beam curve (location)
        if hasattr(beam.Location, 'Curve'):
            beam.Location.Curve = beam_curve
        
        # Update family/type if specified
        if family_name or type_name:
            symbol = find_family_symbol_safely(doc, family_name, type_name, DB.BuiltInCategory.OST_StructuralFraming)
            if symbol:
                if not symbol.IsActive:
                    symbol.Activate()
                    doc.Regenerate()
                beam.Symbol = symbol
        
        # Update level
        level_param = beam.get_Parameter(DB.BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM)
        if level_param:
            level_param.Set(level.Id)
        
        # Set structural usage
        if structural_usage:
            _set_structural_usage(beam, structural_usage)
        
        # Apply rotation if specified
        if rotation != 0.0:
            _apply_beam_rotation(beam, rotation)
        
        # Set additional properties
        _set_beam_properties(beam, properties)
        
        return {
            "success": True,
            "message": "Successfully modified beam '{}'".format(get_element_name(beam)),
            "element_id": str(beam.Id.Value),
            "element_type": "beam",
            "family_name": get_element_name(beam.Symbol.Family),
            "type_name": get_element_name(beam.Symbol),
            "length": round(beam_curve.Length * 304.8, 2)
        }
        
    except ValueError:
        # Invalid element ID, create new beam instead
        return _create_new_beam(doc, beam_curve, level, family_name, type_name, structural_usage, rotation, properties)
    except Exception as e:
        logger.error("Failed to edit beam: {}".format(str(e)))
        return {"error": "Failed to edit beam: {}".format(str(e))}


def _set_structural_usage(beam, structural_usage):
    """Set structural usage for a beam"""
    try:
        usage_param = beam.get_Parameter(DB.BuiltInParameter.INSTANCE_STRUCT_USAGE_PARAM)
        if usage_param:
            usage_map = {
                "Beam": DB.Structure.StructuralInstanceUsage.Beam,
                "Girder": DB.Structure.StructuralInstanceUsage.Girder,
                "Joist": DB.Structure.StructuralInstanceUsage.Joist,
                "Other": DB.Structure.StructuralInstanceUsage.Other
            }
            
            if structural_usage in usage_map:
                usage_param.Set(int(usage_map[structural_usage]))
    except:
        pass


def _apply_beam_rotation(beam, rotation_degrees):
    """Apply rotation to a beam"""
    try:
        if hasattr(beam.Location, 'Curve'):
            curve = beam.Location.Curve
            midpoint = curve.Evaluate(0.5, True)
            axis = DB.Line.CreateBound(midpoint, midpoint + DB.XYZ.BasisZ)
            angle = math.radians(rotation_degrees)
            beam.Location.Rotate(axis, angle)
    except:
        pass


def _set_beam_properties(beam, properties):
    """Set additional properties on a beam"""
    if not properties:
        return
    
    for prop_name, prop_value in properties.items():
        try:
            param = beam.LookupParameter(prop_name)
            if param and not param.IsReadOnly:
                if param.StorageType == DB.StorageType.String:
                    param.Set(str(prop_value))
                elif param.StorageType == DB.StorageType.Integer:
                    param.Set(int(prop_value))
                elif param.StorageType == DB.StorageType.Double:
                    param.Set(float(prop_value))
        except:
            continue


def _create_beam_from_data(beam_data):
    """Create beam from data dictionary - external interface"""
    try:
        doc = revit.doc
        if not doc:
            return routes.make_response(
                data={"error": "No active Revit document"}, status=503
            )
        
        with DB.Transaction(doc, "Create Structural Beam") as trans:
            trans.Start()
            
            try:
                result = _create_beam_from_data_internal(doc, beam_data)
                trans.Commit()
                return routes.make_response(data=result, status=200)
            except Exception as e:
                trans.RollBack()
                logger.error("Failed to create beam: {}".format(str(e)))
                return routes.make_response(
                    data={"error": "Failed to create beam: {}".format(str(e))}, status=500
                )
    
    except Exception as e:
        logger.error("Error in _create_beam_from_data: {}".format(str(e)))
        return routes.make_response(
            data={"error": "Internal server error: {}".format(str(e))}, status=500
        )


def _create_beam_from_data_internal(doc, beam_data):
    """Create beam from data dictionary - internal function"""
    try:
        # Find level
        level = _find_level_by_name(doc, beam_data["level_name"])
        if not level:
            return {"error": "Level '{}' not found".format(beam_data["level_name"])}
        
        # Convert points
        start_pt = DB.XYZ(
            beam_data["start_point"]["x"] / 304.8,
            beam_data["start_point"]["y"] / 304.8,
            beam_data["start_point"]["z"] / 304.8
        )
        end_pt = DB.XYZ(
            beam_data["end_point"]["x"] / 304.8,
            beam_data["end_point"]["y"] / 304.8,
            beam_data["end_point"]["z"] / 304.8
        )
        
        # Create curve
        beam_curve = DB.Line.CreateBound(start_pt, end_pt)
        
        # Create beam
        return _create_new_beam(
            doc, beam_curve, level,
            beam_data.get("family_name", "W-Wide Flange"),
            beam_data.get("type_name"),
            beam_data.get("structural_usage", "Beam"),
            beam_data.get("rotation", 0.0),
            beam_data.get("properties", {})
        )
        
    except Exception as e:
        logger.error("Failed to create beam from data: {}".format(str(e)))
        return {"error": "Failed to create beam: {}".format(str(e))}


def _extract_beam_config(beam):
    """Extract beam configuration from an existing beam element"""
    try:
        config = {
            "element_id": str(beam.Id.Value),
            "name": get_element_name(beam)
        }
        
        # Family and type information
        if hasattr(beam, 'Symbol') and beam.Symbol:
            config["family_name"] = get_element_name(beam.Symbol.Family)
            config["type_name"] = get_element_name(beam.Symbol)
            config["type_id"] = str(beam.Symbol.Id.Value)
        
        # Location information
        if hasattr(beam.Location, 'Curve') and beam.Location.Curve:
            curve = beam.Location.Curve
            start_pt = curve.GetEndPoint(0)
            end_pt = curve.GetEndPoint(1)
            
            config["start_point"] = {
                "x": round(start_pt.X * 304.8, 2),
                "y": round(start_pt.Y * 304.8, 2),
                "z": round(start_pt.Z * 304.8, 2)
            }
            config["end_point"] = {
                "x": round(end_pt.X * 304.8, 2),
                "y": round(end_pt.Y * 304.8, 2),
                "z": round(end_pt.Z * 304.8, 2)
            }
            config["length"] = round(curve.Length * 304.8, 2)
        
        # Level information
        level_param = beam.get_Parameter(DB.BuiltInParameter.INSTANCE_REFERENCE_LEVEL_PARAM)
        if level_param and level_param.HasValue:
            level_id = level_param.AsElementId()
            level = beam.Document.GetElement(level_id)
            if level:
                config["level_name"] = get_element_name(level)
                config["level_elevation"] = round(level.Elevation * 304.8, 2)
        
        # Height offset
        offset_param = beam.get_Parameter(DB.BuiltInParameter.Z_OFFSET_VALUE)
        if offset_param and offset_param.HasValue:
            config["height_offset"] = round(offset_param.AsDouble() * 304.8, 2)
        
        # Structural usage
        usage_param = beam.get_Parameter(DB.BuiltInParameter.INSTANCE_STRUCT_USAGE_PARAM)
        if usage_param and usage_param.HasValue:
            config["structural_usage"] = str(usage_param.AsValueString())
        
        # Additional parameters
        additional_params = {}
        for param_name in ["Mark", "Comments"]:
            param = beam.LookupParameter(param_name)
            if param and param.HasValue:
                if param.StorageType == DB.StorageType.String:
                    additional_params[param_name] = param.AsString()
        
        config["properties"] = additional_params
        
        return config
        
    except Exception as e:
        logger.error("Failed to extract beam config: {}".format(str(e)))
        raise


def _extract_beam_type_properties(symbol):
    """Extract comprehensive type properties from a beam family symbol"""
    try:
        type_properties = {}
        
        # ============ BASIC TYPE INFORMATION ============
        type_properties["type_name"] = get_element_name(symbol)
        type_properties["family_name"] = get_element_name(symbol.Family)
        type_properties["category"] = symbol.Category.Name if symbol.Category else "Unknown"
        
        # ============ DIMENSIONAL PROPERTIES ============
        dimensions = {}
        
        # Common structural beam dimension parameters
        dimension_param_names = [
            # Steel beam dimensions
            "d", "bf", "tf", "tw", "r", "k", "k1", "T", "kdes", "kdet",
            "Web Height", "Flange Width", "Flange Thickness", "Web Thickness",
            # Concrete beam dimensions  
            "b", "h", "Width", "Height", "Depth",
            # Timber beam dimensions
            "Nominal Width", "Nominal Depth", "Actual Width", "Actual Depth",
            # General section properties
            "Cross-Sectional Area", "Moment of Inertia Ix", "Moment of Inertia Iy",
            "Section Modulus Sx", "Section Modulus Sy", "Radius of Gyration ix", "Radius of Gyration iy",
            "Warping Constant", "Torsional Constant", "Perimeter", "Weight per Unit Length",
            # Composite properties
            "Effective Width", "Effective Depth", "Composite Area"
        ]
        
        for param_name in dimension_param_names:
            try:
                param = symbol.LookupParameter(param_name)
                if param and param.HasValue:
                    if param.StorageType == DB.StorageType.Double:
                        # Convert based on parameter type
                        value = param.AsDouble()
                        if param_name in ["d", "bf", "tf", "tw", "r", "k", "k1", "T", "kdes", "kdet", 
                                         "Web Height", "Flange Width", "Flange Thickness", "Web Thickness",
                                         "b", "h", "Width", "Height", "Depth",
                                         "Nominal Width", "Nominal Depth", "Actual Width", "Actual Depth",
                                         "Effective Width", "Effective Depth"]:
                            # Linear dimensions - convert to mm
                            dimensions[param_name] = round(value * 304.8, 2)
                        elif param_name in ["Cross-Sectional Area", "Composite Area"]:
                            # Area - convert to sq mm
                            dimensions[param_name] = round(value * 645.16, 2)  # sq ft to sq mm
                        elif param_name in ["Moment of Inertia Ix", "Moment of Inertia Iy"]:
                            # Moment of inertia - convert to mm^4
                            dimensions[param_name] = round(value * 4.162314e6, 2)  # in^4 to mm^4
                        elif param_name in ["Section Modulus Sx", "Section Modulus Sy"]:
                            # Section modulus - convert to mm^3
                            dimensions[param_name] = round(value * 16387.064, 2)  # in^3 to mm^3
                        elif param_name in ["Radius of Gyration ix", "Radius of Gyration iy"]:
                            # Radius of gyration - convert to mm
                            dimensions[param_name] = round(value * 25.4, 2)  # in to mm
                        elif param_name in ["Weight per Unit Length"]:
                            # Weight per unit length - convert to kg/m
                            dimensions[param_name] = round(value * 1.48816, 2)  # lb/ft to kg/m
                        else:
                            # Other values
                            dimensions[param_name] = round(value, 3)
                    elif param.StorageType == DB.StorageType.Integer:
                        dimensions[param_name] = param.AsInteger()
                    elif param.StorageType == DB.StorageType.String:
                        dimensions[param_name] = param.AsString()
            except:
                continue
        
        type_properties["dimensions"] = dimensions
        
        # ============ MATERIAL PROPERTIES ============
        materials = {}
        
        # Get structural material
        try:
            if hasattr(symbol, 'StructuralMaterialId') and symbol.StructuralMaterialId:
                material = symbol.Document.GetElement(symbol.StructuralMaterialId)
                if material:
                    materials["structural_material"] = {
                        "name": get_element_name(material),
                        "id": str(symbol.StructuralMaterialId.Value)
                    }
                    
                    # Get material properties
                    material_props = _extract_material_properties(material)
                    materials["structural_material"]["properties"] = material_props
        except:
            pass
        
        # Get other material parameters
        material_param_names = ["Material", "Structural Material", "Material: Identity Data"]
        
        for param_name in material_param_names:
            try:
                param = symbol.LookupParameter(param_name)
                if param and param.HasValue:
                    if param.StorageType == DB.StorageType.ElementId:
                        elem_id = param.AsElementId()
                        if elem_id and elem_id.Value != -1:
                            material = symbol.Document.GetElement(elem_id)
                            if material:
                                materials[param_name.lower().replace(":", "").replace(" ", "_")] = {
                                    "name": get_element_name(material),
                                    "id": str(elem_id.Value)
                                }
                    elif param.StorageType == DB.StorageType.String:
                        materials[param_name.lower().replace(":", "").replace(" ", "_")] = param.AsString()
            except:
                continue
        
        type_properties["materials"] = materials
        
        # ============ STRUCTURAL PROPERTIES ============
        structural = {}
        
        structural_param_names = [
            "Structural Usage", "Structural Material", "Young's Modulus", "Poisson Ratio", 
            "Shear Modulus", "Thermal Expansion Coefficient", "Unit Weight", "Damping Ratio",
            "Allowable Stress", "Yield Strength", "Ultimate Strength", "Modulus of Elasticity"
        ]
        
        for param_name in structural_param_names:
            try:
                param = symbol.LookupParameter(param_name)
                if param and param.HasValue:
                    if param.StorageType == DB.StorageType.String:
                        structural[param_name.lower().replace("'", "").replace(" ", "_")] = param.AsString()
                    elif param.StorageType == DB.StorageType.Double:
                        value = param.AsDouble()
                        if param_name == "Unit Weight":
                            # Convert to kg/m³
                            structural[param_name.lower().replace(" ", "_")] = round(value * 16.0185, 2)  # lb/ft³ to kg/m³
                        elif param_name in ["Allowable Stress", "Yield Strength", "Ultimate Strength"]:
                            # Convert to MPa
                            structural[param_name.lower().replace(" ", "_")] = round(value * 0.00689476, 2)  # psi to MPa
                        elif param_name in ["Young's Modulus", "Modulus of Elasticity"]:
                            # Convert to MPa
                            structural[param_name.lower().replace("'", "").replace(" ", "_")] = round(value * 0.00689476, 2)
                        else:
                            structural[param_name.lower().replace("'", "").replace(" ", "_")] = round(value, 3)
                    elif param.StorageType == DB.StorageType.Integer:
                        structural[param_name.lower().replace("'", "").replace(" ", "_")] = param.AsInteger()
                    elif param.StorageType == DB.StorageType.ElementId:
                        elem_id = param.AsElementId()
                        if elem_id and elem_id.Value != -1:
                            elem = symbol.Document.GetElement(elem_id)
                            structural[param_name.lower().replace(" ", "_")] = get_element_name(elem) if elem else str(elem_id.Value)
            except:
                continue
        
        type_properties["structural"] = structural
        
        # ============ IDENTITY DATA ============
        identity = {}
        
        identity_param_names = [
            "Type Name", "Type Comments", "Type Mark", "Type Image", "Description", 
            "Assembly Code", "Assembly Description", "Keynote", "Model", "Manufacturer", 
            "Cost", "URL", "Fire Rating", "Grade", "Standard"
        ]
        
        for param_name in identity_param_names:
            try:
                param = symbol.LookupParameter(param_name)
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
        
        # ============ ANALYTICAL PROPERTIES ============
        analytical = {}
        
        analytical_param_names = [
            "Analytical Alignment Method", "Start Extension", "End Extension",
            "Analytical Model", "Enable Analytical Model", "Release Start", "Release End",
            "Cantilever", "Continuous"
        ]
        
        for param_name in analytical_param_names:
            try:
                param = symbol.LookupParameter(param_name)
                if param and param.HasValue:
                    if param.StorageType == DB.StorageType.String:
                        analytical[param_name.lower().replace(" ", "_")] = param.AsString()
                    elif param.StorageType == DB.StorageType.Double:
                        # Convert extensions to mm
                        analytical[param_name.lower().replace(" ", "_")] = round(param.AsDouble() * 304.8, 2)
                    elif param.StorageType == DB.StorageType.Integer:
                        analytical[param_name.lower().replace(" ", "_")] = param.AsInteger()
            except:
                continue
        
        type_properties["analytical"] = analytical
        
        # ============ ADDITIONAL TYPE PARAMETERS ============
        additional = {}
        
        # Get all parameters not already captured
        try:
            for param in symbol.Parameters:
                param_name = param.Definition.Name
                
                # Skip if already captured in other sections
                if any(param_name in section.values() if isinstance(section, dict) else False 
                       for section in [dimensions, materials, structural, identity, analytical]):
                    continue
                
                # Skip built-in parameters that are not useful
                skip_params = ["Element ID", "Type ID", "Family Name", "Type Name", "Category"]
                if param_name in skip_params:
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
                                elem = symbol.Document.GetElement(elem_id)
                                additional[param_name.lower().replace(" ", "_")] = get_element_name(elem) if elem else str(elem_id.Value)
                except:
                    continue
        except:
            pass
        
        type_properties["additional_parameters"] = additional
        
        return type_properties
        
    except Exception as e:
        logger.warning("Could not extract beam type properties: {}".format(str(e)))
        return {
            "error": str(e),
            "dimensions": {},
            "materials": {},
            "structural": {},
            "identity": {},
            "analytical": {},
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
            "Ultimate Strength", "Modulus of Elasticity"
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
                        elif param_name in ["Compressive Strength", "Tensile Strength", "Yield Strength", "Ultimate Strength"]:
                            # Convert to MPa
                            material_props[param_name.lower().replace(" ", "_")] = round(value * 0.00689476, 2)  # psi to MPa
                        elif param_name in ["Young's Modulus", "Modulus of Elasticity"]:
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