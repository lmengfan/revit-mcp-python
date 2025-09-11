# -*- coding: UTF-8 -*-
"""
Grid Management Module for Revit MCP
Handles grid creation, editing, and querying functionality
"""

from .utils import get_element_name, RoomWarningSwallower
from pyrevit import routes, revit, DB
import json
import traceback
import logging
import math

logger = logging.getLogger(__name__)


def register_grid_management_routes(api):
    """Register all grid management routes with the API"""

    @api.route("/create_or_edit_grid/", methods=["POST"])
    @api.route("/create_or_edit_grid", methods=["POST"])
    def create_or_edit_grid(doc, request):
        """
        Create a new grid or edit an existing grid in Revit.
        
        This tool can operate in two modes:
        1. Creation Mode (when element_id is None): Creates a new grid
        2. Edit Mode (when element_id is provided): Modifies an existing grid
        
        Expected request data:
        {
            "element_id": "123456",  // Optional - for editing existing grid
            "grid_type": "linear",   // Required - "linear" or "radial"
            "name": "A",             // Optional - grid name/label
            
            // For linear grids:
            "start_point": {"x": 0, "y": 0, "z": 0},     // Required for linear
            "end_point": {"x": 5000, "y": 0, "z": 0},    // Required for linear
            
            // For radial grids:
            "center_point": {"x": 0, "y": 0, "z": 0},    // Required for radial
            "radius": 5000.0,                            // Required for radial
            "start_angle": 0.0,                          // Optional - in degrees
            "end_angle": 180.0,                          // Optional - in degrees
            
            // Common properties:
            "vertical_extents": {                        // Optional
                "bottom_level": "Level 1",
                "top_level": "Level 2"
            },
            "properties": {                              // Optional - additional parameters
                "Comments": "Created via MCP"
            }
        }
        """
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            # Parse request data
            if not request or not request.data:
                return routes.make_response(
                    data={"error": "No data provided"}, status=400
                )

            # Parse JSON if needed
            data = None
            if isinstance(request.data, str):
                try:
                    data = json.loads(request.data)
                except Exception as json_err:
                    return routes.make_response(
                        data={"error": "Invalid JSON format: {}".format(str(json_err))},
                        status=400,
                    )
            else:
                data = request.data

            # Validate data structure
            if not data or not isinstance(data, dict):
                return routes.make_response(
                    data={"error": "Invalid data format - expected JSON object"},
                    status=400,
                )

            # Extract parameters
            element_id = data.get("element_id")
            grid_type = data.get("grid_type", "linear")
            grid_name = data.get("name", "")
            start_point = data.get("start_point")
            end_point = data.get("end_point")
            center_point = data.get("center_point")
            radius = data.get("radius")
            start_angle = data.get("start_angle", 0.0)
            end_angle = data.get("end_angle", 180.0)
            vertical_extents = data.get("vertical_extents")
            properties = data.get("properties", {})

            # Basic validation
            if grid_type not in ["linear", "radial"]:
                return routes.make_response(
                    data={"error": "grid_type must be 'linear' or 'radial'"}, status=400
                )

            if grid_type == "linear" and (not start_point or not end_point):
                return routes.make_response(
                    data={"error": "start_point and end_point are required for linear grids"}, status=400
                )

            if grid_type == "radial" and (not center_point or not radius):
                return routes.make_response(
                    data={"error": "center_point and radius are required for radial grids"}, status=400
                )

            logger.info("Grid operation: {} mode, type: {}".format(
                "Edit" if element_id else "Create", grid_type
            ))

            # Check if this is an edit operation
            existing_grid = None
            if element_id:
                try:
                    elem_id = DB.ElementId(int(element_id))
                    existing_grid = doc.GetElement(elem_id)
                    if not existing_grid or not hasattr(existing_grid, 'Category') or \
                       existing_grid.Category.Id.Value != int(DB.BuiltInCategory.OST_Grids):
                        return routes.make_response(
                            data={"error": "Element with ID {} is not a grid".format(element_id)},
                            status=404,
                        )
                except:
                    return routes.make_response(
                        data={"error": "Invalid element_id: {}".format(element_id)},
                        status=400,
                    )

            # Create or convert curve based on grid type
            try:
                if grid_type == "linear":
                    curve = _create_linear_curve(start_point, end_point)
                else:  # radial
                    curve = _create_radial_curve(center_point, radius, start_angle, end_angle)
            except Exception as curve_error:
                return routes.make_response(
                    data={"error": "Failed to create grid curve: {}".format(str(curve_error))},
                    status=400,
                )

            try:
                new_grid = None
                
                if existing_grid:
                    # Edit existing grid
                    new_grid = _edit_existing_grid(
                        doc, existing_grid, curve, grid_name, vertical_extents, properties
                    )
                else:
                    # Create new grid
                    with DB.Transaction(doc, "Create Grid via MCP") as t:
                        t.Start()
                        new_grid = _create_new_grid(
                            doc, curve, grid_name, vertical_extents, properties
                        )
                        if not new_grid:
                            t.RollBack()
                            return routes.make_response(
                                data={"error": "Failed to create grid"}, status=500
                            )
                        t.Commit()

                if not new_grid:
                    return routes.make_response(
                        data={"error": "Failed to create/edit grid"}, status=500
                    )
                
                operation = "edited" if existing_grid else "created"
                grid_name_result = get_element_name(new_grid)
                
                return routes.make_response(
                    data={
                        "message": "Successfully {} grid '{}'".format(operation, grid_name_result),
                        "grid_id": str(new_grid.Id.Value),
                        "grid_name": grid_name_result,
                        "grid_type": grid_type,
                        "operation": operation
                    },
                    status=200
                )

            except Exception as creation_error:
                logger.error("Grid operation failed: {}".format(str(creation_error)))
                return routes.make_response(
                    data={"error": "Grid operation failed: {}".format(str(creation_error))},
                    status=500,
                )

        except Exception as e:
            logger.error("Grid management error: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Grid management error: {}".format(str(e))},
                status=500,
            )

    @api.route("/query_grid/", methods=["POST"])
    @api.route("/query_grid", methods=["POST"])
    def query_grid(doc, request):
        """
        Query an existing grid by ID and return its configuration.
        
        Expected request data:
        {
            "element_id": "123456"  // Required - grid element ID
        }
        """
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            # Parse request data
            if not request or not request.data:
                return routes.make_response(
                    data={"error": "No data provided"}, status=400
                )

            # Parse JSON if needed
            data = None
            if isinstance(request.data, str):
                try:
                    data = json.loads(request.data)
                except Exception as json_err:
                    return routes.make_response(
                        data={"error": "Invalid JSON format: {}".format(str(json_err))},
                        status=400,
                    )
            else:
                data = request.data

            element_id = data.get("element_id")
            if not element_id:
                return routes.make_response(
                    data={"error": "element_id is required"}, status=400
                )

            try:
                elem_id = DB.ElementId(int(element_id))
                grid = doc.GetElement(elem_id)
                if not grid or not hasattr(grid, 'Category') or \
                   grid.Category.Id.Value != int(DB.BuiltInCategory.OST_Grids):
                    return routes.make_response(
                        data={"error": "Element with ID {} is not a grid".format(element_id)},
                        status=404,
                    )
            except:
                return routes.make_response(
                    data={"error": "Invalid element_id: {}".format(element_id)},
                    status=400,
                )

            # Extract grid properties
            grid_config = _extract_grid_config(grid)
            
            return routes.make_response(
                data={
                    "message": "Successfully queried grid '{}'".format(grid_config["name"]),
                    "grid_config": grid_config
                },
                status=200
            )

        except Exception as e:
            logger.error("Grid query error: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Grid query error: {}".format(str(e))},
                status=500,
            )

    @api.route("/find_grid_intersections/", methods=["POST"])
    @api.route("/find_grid_intersections", methods=["POST"])
    def find_grid_intersections(doc, request):
        """
        Find intersection points between grids in the model.
        
        Expected request data:
        {
            "grid_ids": ["123", "456"],  // Optional - specific grid IDs, or all if empty
            "level_name": "Level 1"      // Optional - level to project intersections to
        }
        """
        try:
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            # Parse request data
            data = {}
            if request and request.data:
                if isinstance(request.data, str):
                    try:
                        data = json.loads(request.data)
                    except:
                        pass
                else:
                    data = request.data

            grid_ids = data.get("grid_ids", [])
            level_name = data.get("level_name")

            # Get grids to analyze
            grids = []
            if grid_ids:
                # Get specific grids
                for grid_id in grid_ids:
                    try:
                        elem_id = DB.ElementId(int(grid_id))
                        grid = doc.GetElement(elem_id)
                        if grid and hasattr(grid, 'Category') and \
                           grid.Category.Id.Value == int(DB.BuiltInCategory.OST_Grids):
                            grids.append(grid)
                    except:
                        continue
            else:
                # Get all grids
                grids = (
                    DB.FilteredElementCollector(doc)
                    .OfCategory(DB.BuiltInCategory.OST_Grids)
                    .WhereElementIsNotElementType()
                    .ToElements()
                )

            if len(grids) < 2:
                return routes.make_response(
                    data={"error": "At least 2 grids are required to find intersections"},
                    status=400,
                )

            # Find target level if specified
            target_level = None
            if level_name:
                levels = (
                    DB.FilteredElementCollector(doc)
                    .OfCategory(DB.BuiltInCategory.OST_Levels)
                    .WhereElementIsNotElementType()
                    .ToElements()
                )
                for level in levels:
                    try:
                        level_name_safe = get_element_name(level)
                        if level_name_safe == level_name:
                            target_level = level
                            break
                    except:
                        continue

            # Calculate intersections
            intersections = _find_grid_intersections(grids, target_level)
            
            return routes.make_response(
                data={
                    "message": "Found {} grid intersections".format(len(intersections)),
                    "intersections": intersections,
                    "grid_count": len(grids),
                    "level_name": level_name if target_level else None
                },
                status=200
            )

        except Exception as e:
            logger.error("Grid intersection error: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Grid intersection error: {}".format(str(e))},
                status=500,
            )

    @api.route("/grid_details/", methods=["GET"])
    @api.route("/grid_details", methods=["GET"])
    @api.route("/get_grid_details/", methods=["GET"])
    @api.route("/get_grid_details", methods=["GET"])
    def get_grid_details():
        """
        Get comprehensive information about selected grid elements in Revit
        
        Returns detailed information including:
        - Grid name, type, and ID information
        - Curve geometry (linear or radial)
        - Start/end points or center/radius/angles
        - Vertical extents and level information
        - Grid intersection capabilities
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
                        "grids": []
                    }
                )
            
            grids_info = []
            
            for elem_id in selected_ids:
                try:
                    element = doc.GetElement(elem_id)
                    if not element:
                        continue
                    
                    # Check if element is a grid
                    if not (hasattr(element, 'Category') and element.Category and 
                           element.Category.Id.Value == int(DB.BuiltInCategory.OST_Grids)):
                        continue
                    
                    grid_info = {
                        "id": str(elem_id.Value),
                        "name": get_element_name(element)
                    }
                    
                    # ============ GRID CURVE INFORMATION ============
                    try:
                        curve = element.Curve
                        if curve:
                            # Determine grid type based on curve type
                            if hasattr(curve, 'GetEndPoint'):
                                # Linear grid
                                grid_info["grid_type"] = "linear"
                                start_pt = curve.GetEndPoint(0)
                                end_pt = curve.GetEndPoint(1)
                                
                                grid_info["start_point"] = {
                                    "x": round(start_pt.X * 304.8, 2),  # Convert to mm
                                    "y": round(start_pt.Y * 304.8, 2),
                                    "z": round(start_pt.Z * 304.8, 2)
                                }
                                grid_info["end_point"] = {
                                    "x": round(end_pt.X * 304.8, 2),
                                    "y": round(end_pt.Y * 304.8, 2),
                                    "z": round(end_pt.Z * 304.8, 2)
                                }
                                grid_info["length"] = round(curve.Length * 304.8, 2)
                                
                                # Calculate direction vector
                                direction = end_pt - start_pt
                                if direction.GetLength() > 0:
                                    direction = direction.Normalize()
                                    grid_info["direction"] = {
                                        "x": round(direction.X, 3),
                                        "y": round(direction.Y, 3),
                                        "z": round(direction.Z, 3)
                                    }
                                
                            elif hasattr(curve, 'Center') and hasattr(curve, 'Radius'):
                                # Radial grid (Arc)
                                grid_info["grid_type"] = "radial"
                                center = curve.Center
                                
                                grid_info["center_point"] = {
                                    "x": round(center.X * 304.8, 2),
                                    "y": round(center.Y * 304.8, 2),
                                    "z": round(center.Z * 304.8, 2)
                                }
                                grid_info["radius"] = round(curve.Radius * 304.8, 2)
                                
                                # Get arc angles if available
                                try:
                                    start_angle = math.degrees(curve.GetEndParameter(0))
                                    end_angle = math.degrees(curve.GetEndParameter(1))
                                    grid_info["start_angle"] = round(start_angle, 2)
                                    grid_info["end_angle"] = round(end_angle, 2)
                                    grid_info["arc_length"] = round(curve.Length * 304.8, 2)
                                    
                                    # Calculate arc span
                                    arc_span = end_angle - start_angle
                                    if arc_span < 0:
                                        arc_span += 360
                                    grid_info["arc_span"] = round(arc_span, 2)
                                    
                                except:
                                    grid_info["start_angle"] = 0.0
                                    grid_info["end_angle"] = 180.0
                                    grid_info["arc_span"] = 180.0
                                
                                # Get start and end points for arcs
                                try:
                                    start_pt = curve.GetEndPoint(0)
                                    end_pt = curve.GetEndPoint(1)
                                    grid_info["arc_start_point"] = {
                                        "x": round(start_pt.X * 304.8, 2),
                                        "y": round(start_pt.Y * 304.8, 2),
                                        "z": round(start_pt.Z * 304.8, 2)
                                    }
                                    grid_info["arc_end_point"] = {
                                        "x": round(end_pt.X * 304.8, 2),
                                        "y": round(end_pt.Y * 304.8, 2),
                                        "z": round(end_pt.Z * 304.8, 2)
                                    }
                                except:
                                    pass
                                    
                            else:
                                grid_info["grid_type"] = "unknown"
                                grid_info["curve_type"] = str(curve.GetType().Name)
                                
                        else:
                            grid_info["grid_type"] = "unknown"
                            grid_info["curve"] = None
                            
                    except Exception as e:
                        grid_info["grid_type"] = "error"
                        grid_info["curve_error"] = str(e)
                        logger.warning("Could not get grid curve info: {}".format(str(e)))
                    
                    # ============ GRID EXTENTS AND VISIBILITY ============
                    try:
                        # Check if grid extends to all levels
                        try:
                            # Note: ExtendToAllLevels is obsolete but might still be available
                            if hasattr(element, 'ExtendToAllLevels'):
                                grid_info["extends_to_all_levels"] = element.ExtendToAllLevels
                            else:
                                grid_info["extends_to_all_levels"] = None
                        except:
                            grid_info["extends_to_all_levels"] = None
                        
                        # Get vertical extents if available
                        try:
                            # This is a simplified approach - actual vertical extent retrieval 
                            # might require more complex logic depending on Revit version
                            grid_info["vertical_extents"] = "Available via API"
                        except:
                            grid_info["vertical_extents"] = "Unknown"
                            
                    except Exception as e:
                        grid_info["extends_to_all_levels"] = None
                        grid_info["vertical_extents"] = "Error: {}".format(str(e))
                    
                    # ============ GRID BUBBLES AND LEADERS ============
                    try:
                        # Grid bubble information (simplified)
                        grid_info["has_bubble_start"] = True  # Most grids have bubbles
                        grid_info["has_bubble_end"] = True
                        grid_info["bubble_info"] = "Available via DatumPlane methods"
                        
                    except Exception as e:
                        grid_info["bubble_info"] = "Error: {}".format(str(e))
                    
                    # ============ ADDITIONAL PARAMETERS ============
                    additional_params = {}
                    param_names = [
                        "Comments", "Mark", "Type Comments", "Type Mark",
                        "Phasing Created", "Phasing Demolished"
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
                    
                    grid_info["parameters"] = additional_params
                    
                    # ============ BOUNDING BOX ============
                    try:
                        bbox = element.get_BoundingBox(None)
                        if bbox:
                            grid_info["bounding_box"] = {
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
                            grid_info["bounding_box"] = None
                    except:
                        grid_info["bounding_box"] = None
                    
                    # ============ INTERSECTION CAPABILITIES ============
                    try:
                        # Add information about intersection capabilities
                        grid_info["intersection_capable"] = True
                        grid_info["curve_available"] = True if grid_info.get("grid_type") != "unknown" else False
                        
                        # Add midpoint for linear grids
                        if grid_info.get("grid_type") == "linear" and "start_point" in grid_info and "end_point" in grid_info:
                            start = grid_info["start_point"]
                            end = grid_info["end_point"]
                            grid_info["midpoint"] = {
                                "x": round((start["x"] + end["x"]) / 2, 2),
                                "y": round((start["y"] + end["y"]) / 2, 2),
                                "z": round((start["z"] + end["z"]) / 2, 2)
                            }
                            
                    except Exception as e:
                        grid_info["intersection_capable"] = False
                        grid_info["intersection_error"] = str(e)
                    
                    grids_info.append(grid_info)
                    
                except Exception as e:
                    logger.warning("Could not process grid element {}: {}".format(elem_id, str(e)))
                    continue
            
            # ============ CALCULATE INTERSECTIONS BETWEEN SELECTED GRIDS ============
            intersections = []
            if len(grids_info) > 1:
                try:
                    # Get actual grid elements for intersection calculation
                    selected_grids = []
                    for elem_id in selected_ids:
                        element = doc.GetElement(elem_id)
                        if (element and hasattr(element, 'Category') and element.Category and 
                            element.Category.Id.Value == int(DB.BuiltInCategory.OST_Grids)):
                            selected_grids.append(element)
                    
                    # Find intersections between selected grids
                    intersections = _find_grid_intersections(selected_grids)
                    
                except Exception as e:
                    logger.warning("Could not calculate grid intersections: {}".format(str(e)))
            
            # Prepare response
            response_data = {
                "message": "Successfully retrieved {} grid elements".format(len(grids_info)),
                "selected_count": len(selected_ids),
                "grids_found": len(grids_info),
                "grids": grids_info,
                "intersections": intersections,
                "intersection_count": len(intersections)
            }
            
            return routes.make_response(data=response_data, status=200)
            
        except Exception as e:
            logger.error("Failed to get grid details: {}".format(str(e)))
            return routes.make_response(
                data={
                    "error": "Failed to retrieve grid details: {}".format(str(e))
                },
                status=500
            )


def _create_linear_curve(start_point, end_point):
    """Create a linear curve from start and end points"""
    try:
        # Convert coordinates from mm to feet
        start_xyz = DB.XYZ(
            float(start_point.get("x", 0)) / 304.8,
            float(start_point.get("y", 0)) / 304.8,
            float(start_point.get("z", 0)) / 304.8
        )
        end_xyz = DB.XYZ(
            float(end_point.get("x", 0)) / 304.8,
            float(end_point.get("y", 0)) / 304.8,
            float(end_point.get("z", 0)) / 304.8
        )
        
        return DB.Line.CreateBound(start_xyz, end_xyz)
        
    except Exception as e:
        logger.error("Failed to create linear curve: {}".format(str(e)))
        raise Exception("Invalid linear curve definition: {}".format(str(e)))


def _create_radial_curve(center_point, radius, start_angle, end_angle):
    """Create a radial (arc) curve from center, radius, and angles"""
    try:
        # Convert coordinates from mm to feet
        center_xyz = DB.XYZ(
            float(center_point.get("x", 0)) / 304.8,
            float(center_point.get("y", 0)) / 304.8,
            float(center_point.get("z", 0)) / 304.8
        )
        radius_ft = float(radius) / 304.8
        
        # Convert angles from degrees to radians
        start_angle_rad = math.radians(float(start_angle))
        end_angle_rad = math.radians(float(end_angle))
        
        # Create arc using center, radius, and angles
        # Use standard X and Y axes for the arc plane
        x_axis = DB.XYZ(1, 0, 0)
        y_axis = DB.XYZ(0, 1, 0)
        
        return DB.Arc.Create(center_xyz, radius_ft, start_angle_rad, end_angle_rad, x_axis, y_axis)
        
    except Exception as e:
        logger.error("Failed to create radial curve: {}".format(str(e)))
        raise Exception("Invalid radial curve definition: {}".format(str(e)))


def _create_new_grid(doc, curve, grid_name, vertical_extents, properties):
    """Create a new grid element"""
    try:
        # Create the grid
        new_grid = DB.Grid.Create(doc, curve)
        
        # Set grid name if provided
        if grid_name:
            new_grid.Name = str(grid_name)
        
        # Set vertical extents if provided
        if vertical_extents:
            _set_grid_vertical_extents(doc, new_grid, vertical_extents)
        
        # Set additional properties
        if properties:
            _set_grid_properties(new_grid, properties)
        
        return new_grid
        
    except Exception as e:
        logger.error("Failed to create new grid: {}".format(str(e)))
        raise


def _edit_existing_grid(doc, grid, curve, grid_name, vertical_extents, properties):
    """Edit an existing grid element"""
    try:
        with DB.Transaction(doc, "Edit Grid via MCP") as t:
            t.Start()
            
            # Update grid curve - this requires recreating the grid
            # Note: Revit doesn't allow direct curve modification, so we need to delete and recreate
            old_name = get_element_name(grid)
            old_id = grid.Id
            
            # Delete the old grid
            doc.Delete(old_id)
            
            # Create new grid with updated curve
            new_grid = DB.Grid.Create(doc, curve)
            
            # Restore or set new name
            if grid_name:
                new_grid.Name = str(grid_name)
            else:
                new_grid.Name = old_name
            
            # Set vertical extents if provided
            if vertical_extents:
                _set_grid_vertical_extents(doc, new_grid, vertical_extents)
            
            # Set additional properties
            if properties:
                _set_grid_properties(new_grid, properties)
            
            t.Commit()
            return new_grid
        
    except Exception as e:
        logger.error("Failed to edit existing grid: {}".format(str(e)))
        raise


def _set_grid_vertical_extents(doc, grid, vertical_extents):
    """Set vertical extents for a grid"""
    try:
        bottom_level_name = vertical_extents.get("bottom_level")
        top_level_name = vertical_extents.get("top_level")
        
        if not bottom_level_name or not top_level_name:
            return
        
        # Find levels
        levels = (
            DB.FilteredElementCollector(doc)
            .OfCategory(DB.BuiltInCategory.OST_Levels)
            .WhereElementIsNotElementType()
            .ToElements()
        )
        
        bottom_level = None
        top_level = None
        
        for level in levels:
            try:
                level_name_safe = get_element_name(level)
                if level_name_safe == bottom_level_name:
                    bottom_level = level
                elif level_name_safe == top_level_name:
                    top_level = level
            except:
                continue
        
        if bottom_level and top_level:
            # Set vertical extents
            grid.SetVerticalExtents(bottom_level.Id, top_level.Id)
            
    except Exception as e:
        logger.warning("Could not set grid vertical extents: {}".format(str(e)))


def _set_grid_properties(grid, properties):
    """Set additional properties on the grid element"""
    try:
        for param_name, param_value in properties.items():
            param = grid.LookupParameter(param_name)
            if param and not param.IsReadOnly:
                if param.StorageType == DB.StorageType.String:
                    param.Set(str(param_value))
                elif param.StorageType == DB.StorageType.Integer:
                    param.Set(int(param_value))
                elif param.StorageType == DB.StorageType.Double:
                    param.Set(float(param_value))
                    
    except Exception as e:
        logger.warning("Could not set grid properties: {}".format(str(e)))


def _extract_grid_config(grid):
    """Extract configuration from an existing grid"""
    try:
        config = {
            "element_id": grid.Id.Value,
            "name": get_element_name(grid),
            "grid_type": "linear",  # Default, will be updated based on curve type
        }
        
        # Get the grid curve
        curve = grid.Curve
        
        if hasattr(curve, 'GetEndPoint'):
            # Linear grid
            config["grid_type"] = "linear"
            start_pt = curve.GetEndPoint(0)
            end_pt = curve.GetEndPoint(1)
            
            config["start_point"] = {
                "x": start_pt.X * 304.8,  # Convert to mm
                "y": start_pt.Y * 304.8,
                "z": start_pt.Z * 304.8
            }
            config["end_point"] = {
                "x": end_pt.X * 304.8,
                "y": end_pt.Y * 304.8,
                "z": end_pt.Z * 304.8
            }
            
        elif hasattr(curve, 'Center'):
            # Radial grid (Arc)
            config["grid_type"] = "radial"
            center = curve.Center
            radius = curve.Radius
            
            config["center_point"] = {
                "x": center.X * 304.8,
                "y": center.Y * 304.8,
                "z": center.Z * 304.8
            }
            config["radius"] = radius * 304.8
            
            # Get start and end angles if available
            try:
                config["start_angle"] = math.degrees(curve.GetEndParameter(0))
                config["end_angle"] = math.degrees(curve.GetEndParameter(1))
            except:
                config["start_angle"] = 0.0
                config["end_angle"] = 180.0
        
        return config
        
    except Exception as e:
        logger.error("Failed to extract grid config: {}".format(str(e)))
        raise


def _find_grid_intersections(grids, target_level=None):
    """Find intersection points between grids"""
    intersections = []
    
    try:
        # Compare each grid with every other grid
        for i, grid1 in enumerate(grids):
            for j, grid2 in enumerate(grids):
                if i >= j:  # Avoid duplicate comparisons
                    continue
                
                try:
                    curve1 = grid1.Curve
                    curve2 = grid2.Curve
                    
                    # Calculate intersection point
                    intersection_point = _calculate_curve_intersection(curve1, curve2)
                    
                    if intersection_point:
                        # Project to level if specified
                        if target_level:
                            level_elevation = target_level.Elevation
                            intersection_point = DB.XYZ(
                                intersection_point.X,
                                intersection_point.Y,
                                level_elevation
                            )
                        
                        intersections.append({
                            "grid1_id": str(grid1.Id.Value),
                            "grid1_name": get_element_name(grid1),
                            "grid2_id": str(grid2.Id.Value),
                            "grid2_name": get_element_name(grid2),
                            "intersection_point": {
                                "x": intersection_point.X * 304.8,  # Convert to mm
                                "y": intersection_point.Y * 304.8,
                                "z": intersection_point.Z * 304.8
                            }
                        })
                        
                except Exception as e:
                    logger.warning("Failed to find intersection between grids {} and {}: {}".format(
                        get_element_name(grid1), get_element_name(grid2), str(e)
                    ))
                    continue
        
        return intersections
        
    except Exception as e:
        logger.error("Failed to find grid intersections: {}".format(str(e)))
        return []


def _calculate_curve_intersection(curve1, curve2):
    """Calculate intersection point between two curves"""
    try:
        # Handle Line-Line intersection
        if hasattr(curve1, 'GetEndPoint') and hasattr(curve2, 'GetEndPoint'):
            return _calculate_line_intersection(curve1, curve2)
        
        # For other curve types, use Revit's built-in intersection methods
        try:
            # Try using SetComparisonResult for intersection
            intersection_result = curve1.Intersect(curve2)
            if intersection_result == DB.SetComparisonResult.Overlap:
                # Curves intersect - need to find the actual point
                # This is a simplified approach - in practice, you might need more sophisticated methods
                pass
        except:
            pass
        
        return None
        
    except Exception as e:
        logger.warning("Failed to calculate curve intersection: {}".format(str(e)))
        return None


def _calculate_line_intersection(line1, line2):
    """Calculate intersection point between two lines"""
    try:
        # Get line endpoints
        p1 = line1.GetEndPoint(0)
        q1 = line1.GetEndPoint(1)
        p2 = line2.GetEndPoint(0)
        q2 = line2.GetEndPoint(1)
        
        # Calculate direction vectors
        v1 = q1 - p1
        v2 = q2 - p2
        w = p2 - p1
        
        # Check if lines are parallel
        denominator = v2.X * v1.Y - v2.Y * v1.X
        if abs(denominator) < 1e-10:
            return None  # Lines are parallel
        
        # Calculate intersection parameter
        c = (v2.X * w.Y - v2.Y * w.X) / denominator
        
        # Calculate intersection point
        x = p1.X + c * v1.X
        y = p1.Y + c * v1.Y
        z = (p1.Z + q1.Z) / 2  # Use average Z coordinate
        
        return DB.XYZ(x, y, z)
        
    except Exception as e:
        logger.warning("Failed to calculate line intersection: {}".format(str(e)))
        return None 