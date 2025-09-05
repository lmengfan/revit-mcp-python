# -*- coding: UTF-8 -*-
"""
Floor Management Module for Revit MCP
Handles floor creation and editing functionality
"""

from .utils import get_element_name, RoomWarningSwallower
from pyrevit import routes, revit, DB
import json
import traceback
import logging
import math

logger = logging.getLogger(__name__)


def register_floor_management_routes(api):
    """Register all floor management routes with the API"""

    @api.route("/create_or_edit_floor/", methods=["POST"])
    @api.route("/create_or_edit_floor", methods=["POST"])
    def create_or_edit_floor(doc, request):
        """
        Create a new floor or edit an existing floor in Revit.
        
        This tool can operate in two modes:
        1. Creation Mode (when element_id is None): Creates a new floor
        2. Edit Mode (when element_id is provided): Modifies an existing floor
        
        Expected request data:
        {
            "element_id": "123456",  // Optional - for editing existing floor
            "level_name": "Level 1",  // Required - target level
            "height_offset": 100.0,  // Optional - offset from level in mm
            "transformation": {  // Optional - transformation to apply
                "origin": {"x": 0, "y": 0, "z": 0},
                "x_axis": {"x": 1, "y": 0, "z": 0},
                "y_axis": {"x": 0, "y": 1, "z": 0},
                "z_axis": {"x": 0, "y": 0, "z": 1}
            },
            "boundary_curves": [  // Required - array of curve definitions
                {
                    "type": "Line",  // "Line", "Arc", or "Spline"
                    "start_point": {"x": 0, "y": 0, "z": 0},
                    "end_point": {"x": 5000, "y": 0, "z": 0}
                },
                // For arcs, also include:
                // "center": {"x": 0, "y": 0, "z": 0},
                // "radius": 1000.0
            ],
            "thickness": 200.0,  // Optional - floor thickness in mm
            "floor_type_name": "Generic - 200mm",  // Optional - floor type
            "properties": {  // Optional - additional parameters
                "Mark": "F1",
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
            level_name = data.get("level_name")
            height_offset = data.get("height_offset", 0.0)
            transformation = data.get("transformation")
            boundary_curves = data.get("boundary_curves", [])
            thickness = data.get("thickness")
            floor_type_name = data.get("floor_type_name")
            properties = data.get("properties", {})

            # Basic validation
            if not level_name:
                return routes.make_response(
                    data={"error": "level_name is required"}, status=400
                )

            if not boundary_curves or len(boundary_curves) < 3:
                return routes.make_response(
                    data={"error": "At least 3 boundary curves are required"}, status=400
                )

            logger.info("Floor operation: {} mode".format(
                "Edit" if element_id else "Create"
            ))

            # Find the target level
            target_level = None
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

            if not target_level:
                return routes.make_response(
                    data={"error": "Level not found: {}".format(level_name)},
                    status=404,
                )

            # Find floor type if specified
            target_floor_type = None
            if floor_type_name:
                floor_types = (
                    DB.FilteredElementCollector(doc)
                    .OfCategory(DB.BuiltInCategory.OST_Floors)
                    .WhereElementIsElementType()
                    .ToElements()
                )

                for floor_type in floor_types:
                    try:
                        type_name_safe = get_element_name(floor_type)
                        if type_name_safe == floor_type_name:
                            target_floor_type = floor_type
                            break
                    except:
                        continue

                if not target_floor_type:
                    logger.warning("Floor type not found: {}, using default".format(floor_type_name))

            # Check if this is an edit operation
            existing_floor = None
            if element_id:
                try:
                    elem_id = DB.ElementId(int(element_id))
                    existing_floor = doc.GetElement(elem_id)
                    if not existing_floor or not hasattr(existing_floor, 'Category') or \
                       existing_floor.Category.Id.IntegerValue != int(DB.BuiltInCategory.OST_Floors):
                        return routes.make_response(
                            data={"error": "Element with ID {} is not a floor".format(element_id)},
                            status=404,
                        )
                except:
                    return routes.make_response(
                        data={"error": "Invalid element_id: {}".format(element_id)},
                        status=400,
                    )

            # Convert boundary curves to Revit curves
            revit_curves = []
            try:
                revit_curves = _convert_boundary_curves_to_revit(boundary_curves, transformation)
            except Exception as curve_error:
                return routes.make_response(
                    data={"error": "Failed to process boundary curves: {}".format(str(curve_error))},
                    status=400,
                )
            try:
                new_floor = None
                
                if existing_floor:
                    # Edit existing floor using the correct pattern
                    new_floor = _edit_existing_floor(
                        doc, existing_floor, revit_curves, target_level, 
                        height_offset, target_floor_type, thickness, properties
                    )
                else:
                    # Create new floor
                    with DB.Transaction(doc, "Create Floor via MCP") as t:
                        t.Start()
                        new_floor = _create_new_floor(
                            doc, revit_curves, target_level, height_offset, 
                            target_floor_type, thickness, properties
                        )
                        if not new_floor:
                            t.RollBack()
                            return routes.make_response(
                                data={"error": "Failed to create floor"}, status=500
                            )
                        t.Commit()

                if not new_floor:
                    return routes.make_response(
                        data={"error": "Failed to create/edit floor"}, status=500
                    )
                
                operation = "edited" if existing_floor else "created"
                floor_name = get_element_name(new_floor)
                
                return routes.make_response(
                    data={
                        "message": "Successfully {} floor '{}'".format(operation, floor_name),
                        "floor_id": str(new_floor.Id.IntegerValue),
                        "floor_name": floor_name,
                        "level_name": level_name,
                        "height_offset": height_offset,
                        "operation": operation
                    },
                    status=200
                )

            except Exception as creation_error:
                logger.error("Floor operation failed: {}".format(str(creation_error)))
                return routes.make_response(
                    data={"error": "Floor operation failed: {}".format(str(creation_error))},
                    status=500,
                )

        except Exception as e:
            logger.error("Floor management error: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Floor management error: {}".format(str(e))},
                status=500,
            )

    @api.route("/create_rectangular_floor/", methods=["POST"])
    @api.route("/create_rectangular_floor", methods=["POST"])
    def create_rectangular_floor(doc, request):
        """
        Create a rectangular floor with specified dimensions.
        
        This is a convenience tool that automatically generates boundary curves
        for a rectangular floor based on width, length, and origin point.
        
        Expected request data:
        {
            "level_name": "Level 1",  // Required
            "width": 5000.0,  // Required - width in mm (X direction)
            "length": 3000.0,  // Required - length in mm (Y direction)
            "origin_x": 0.0,  // Optional - X origin in mm
            "origin_y": 0.0,  // Optional - Y origin in mm
            "origin_z": 0.0,  // Optional - Z origin in mm
            "height_offset": 0.0,  // Optional - offset from level in mm
            "thickness": 200.0,  // Optional - floor thickness in mm
            "floor_type_name": "Generic - 200mm",  // Optional
            "properties": {}  // Optional - additional parameters
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

            # Extract parameters
            level_name = data.get("level_name")
            width = data.get("width")
            length = data.get("length")
            origin_x = data.get("origin_x", 0.0)
            origin_y = data.get("origin_y", 0.0)
            origin_z = data.get("origin_z", 0.0)
            height_offset = data.get("height_offset", 0.0)
            thickness = data.get("thickness")
            floor_type_name = data.get("floor_type_name")
            properties = data.get("properties", {})

            # Validation
            if not level_name:
                return routes.make_response(
                    data={"error": "level_name is required"}, status=400
                )
            if not width or not length:
                return routes.make_response(
                    data={"error": "width and length are required"}, status=400
                )

            # Convert to feet for Revit API
            width_ft = float(width) / 304.8
            length_ft = float(length) / 304.8
            origin_x_ft = float(origin_x) / 304.8
            origin_y_ft = float(origin_y) / 304.8
            origin_z_ft = float(origin_z) / 304.8

            # Generate rectangular boundary curves
            boundary_curves = [
                {
                    "type": "Line",
                    "start_point": {"x": origin_x, "y": origin_y, "z": origin_z},
                    "end_point": {"x": origin_x + width, "y": origin_y, "z": origin_z}
                },
                {
                    "type": "Line", 
                    "start_point": {"x": origin_x + width, "y": origin_y, "z": origin_z},
                    "end_point": {"x": origin_x + width, "y": origin_y + length, "z": origin_z}
                },
                {
                    "type": "Line",
                    "start_point": {"x": origin_x + width, "y": origin_y + length, "z": origin_z},
                    "end_point": {"x": origin_x, "y": origin_y + length, "z": origin_z}
                },
                {
                    "type": "Line",
                    "start_point": {"x": origin_x, "y": origin_y + length, "z": origin_z},
                    "end_point": {"x": origin_x, "y": origin_y, "z": origin_z}
                }
            ]

            # Create the floor data
            floor_data = {
                "level_name": level_name,
                "height_offset": height_offset,
                "boundary_curves": boundary_curves,
                "thickness": thickness,
                "floor_type_name": floor_type_name,
                "properties": properties
            }

            # Create a mock request object
            mock_request = type('MockRequest', (), {'data': floor_data})()
            
            # Call the main create_or_edit_floor function directly
            return create_or_edit_floor(doc, mock_request)

        except Exception as e:
            logger.error("Rectangular floor creation error: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Rectangular floor creation error: {}".format(str(e))},
                status=500,
            )


def _convert_boundary_curves_to_revit(boundary_curves, transformation=None):
    """Convert boundary curve definitions to Revit curve objects"""
    revit_curves = []
    
    for curve_def in boundary_curves:
        try:
            curve_type = curve_def.get("type", "Line")
            start_pt = curve_def.get("start_point", {})
            end_pt = curve_def.get("end_point", {})
            
            # Convert coordinates from mm to feet
            start_xyz = DB.XYZ(
                float(start_pt.get("x", 0)) / 304.8,
                float(start_pt.get("y", 0)) / 304.8,
                float(start_pt.get("z", 0)) / 304.8
            )
            end_xyz = DB.XYZ(
                float(end_pt.get("x", 0)) / 304.8,
                float(end_pt.get("y", 0)) / 304.8,
                float(end_pt.get("z", 0)) / 304.8
            )
            
            # Apply transformation if provided
            if transformation:
                start_xyz = _apply_transformation(start_xyz, transformation)
                end_xyz = _apply_transformation(end_xyz, transformation)
            
            # Create the appropriate curve type
            if curve_type == "Line":
                curve = DB.Line.CreateBound(start_xyz, end_xyz)
            elif curve_type == "Arc":
                center = curve_def.get("center", {})
                radius = curve_def.get("radius", 1000.0)
                
                center_xyz = DB.XYZ(
                    float(center.get("x", 0)) / 304.8,
                    float(center.get("y", 0)) / 304.8,
                    float(center.get("z", 0)) / 304.8
                )
                
                if transformation:
                    center_xyz = _apply_transformation(center_xyz, transformation)
                
                radius_ft = float(radius) / 304.8
                curve = DB.Arc.Create(start_xyz, end_xyz, center_xyz)
            else:
                # Default to line if type not recognized
                curve = DB.Line.CreateBound(start_xyz, end_xyz)
            
            revit_curves.append(curve)
            
        except Exception as e:
            logger.error("Failed to convert curve: {}".format(str(e)))
            raise Exception("Invalid curve definition: {}".format(str(e)))
    
    return revit_curves


def _apply_transformation(point, transformation):
    """Apply transformation matrix to a point"""
    try:
        origin = transformation.get("origin", {"x": 0, "y": 0, "z": 0})
        x_axis = transformation.get("x_axis", {"x": 1, "y": 0, "z": 0})
        y_axis = transformation.get("y_axis", {"x": 0, "y": 1, "z": 0})
        z_axis = transformation.get("z_axis", {"x": 0, "y": 0, "z": 1})
        
        # Convert to feet
        origin_xyz = DB.XYZ(
            float(origin["x"]) / 304.8,
            float(origin["y"]) / 304.8,
            float(origin["z"]) / 304.8
        )
        x_axis_xyz = DB.XYZ(float(x_axis["x"]), float(x_axis["y"]), float(x_axis["z"]))
        y_axis_xyz = DB.XYZ(float(y_axis["x"]), float(y_axis["y"]), float(y_axis["z"]))
        z_axis_xyz = DB.XYZ(float(z_axis["x"]), float(z_axis["y"]), float(z_axis["z"]))
        
        # Create transformation
        transform = DB.Transform.CreateTranslation(origin_xyz)
        transform.BasisX = x_axis_xyz
        transform.BasisY = y_axis_xyz
        transform.BasisZ = z_axis_xyz
        
        return transform.OfPoint(point)
        
    except Exception as e:
        logger.warning("Failed to apply transformation: {}".format(str(e)))
        return point


def _create_new_floor(doc, curves, level, height_offset, floor_type, thickness, properties):
    """Create a new floor element"""
    try:
        # Create curve loop from curves
        curve_loop = DB.CurveLoop()
        for curve in curves:
            curve_loop.Append(curve)
        
        # Create list of curve loops (profile) - convert to .NET List
        from System.Collections.Generic import List
        curve_loops = List[DB.CurveLoop]()
        curve_loops.Add(curve_loop)
        
        # Convert height offset from mm to feet
        height_offset_ft = float(height_offset) / 304.8
        
        # Create the floor using the new API
        if floor_type:
            new_floor = DB.Floor.Create(doc, curve_loops, floor_type.Id, level.Id)
        else:
            # Use default floor type
            default_floor_type = doc.GetDefaultElementTypeId(DB.ElementTypeGroup.FloorType)
            if default_floor_type and default_floor_type.IntegerValue != DB.ElementId.InvalidElementId.IntegerValue:
                new_floor = DB.Floor.Create(doc, curve_loops, default_floor_type, level.Id)
            else:
                # Find any available floor type
                floor_types = (
                    DB.FilteredElementCollector(doc)
                    .OfCategory(DB.BuiltInCategory.OST_Floors)
                    .WhereElementIsElementType()
                    .FirstElement()
                )
                if floor_types:
                    new_floor = DB.Floor.Create(doc, curve_loops, floor_types.Id, level.Id)
                else:
                    raise Exception("No floor types available in the document")
        
        # Set height offset if specified
        if height_offset != 0:
            height_param = new_floor.LookupParameter("Height Offset From Level")
            if height_param and not height_param.IsReadOnly:
                height_param.Set(height_offset_ft)
        
        # Handle thickness if specified and no floor type was provided
        if thickness and not floor_type:
            _set_floor_thickness(new_floor, thickness)
        
        return new_floor
        
    except Exception as e:
        logger.error("Failed to create new floor: {}".format(str(e)))
        raise


def _edit_existing_floor(doc, floor, curves, level, height_offset, floor_type, thickness, properties):
    """Edit an existing floor element"""
    try:
        # Get the floor's sketch using SketchId
        sketch_id = floor.SketchId
        if sketch_id.IntegerValue == DB.ElementId.InvalidElementId.IntegerValue:
            raise Exception("Cannot edit floor - no sketch ID available")
        
        sketch = doc.GetElement(sketch_id)
        if not sketch:
            raise Exception("Cannot edit floor - sketch not found")
        
        # Use SketchEditScope to edit the floor (outside of any transaction)
        sketch_scope = DB.SketchEditScope(doc, "Edit Floor via MCP")
        sketch_scope.Start(sketch_id)
        sketch = doc.GetElement(sketch_id)
        plane = sketch.SketchPlane
        origin = plane.GetPlane().Origin
        height = origin.Z
        swallower = RoomWarningSwallower()
        
        # Update the floor boundary curves within a transaction
        with DB.Transaction(doc, "Update Floor Boundaries") as t:
            t.Start()
            # Delete existing sketch elements
            for elementId in sketch.GetAllElements():
                doc.Delete(elementId)
            # Create new model curves for the boundary - project curves onto the sketch plane height
            for curve in curves:
                # Project the curve onto the sketch plane height
                projected_curve = _project_curve_to_plane_height(curve, height)
                doc.Create.NewModelCurve(projected_curve, plane)
            t.Commit()
        
        # Commit the sketch changes
        sketch_scope.Commit(swallower)
        
        # Update other properties in separate transactions (outside of sketch scope)
        # Update level if different
        if floor.LevelId.IntegerValue != level.Id.IntegerValue:
            with DB.Transaction(doc, "Update Floor Level") as t:
                t.Start()
                level_param = floor.LookupParameter("Level")
                if level_param and not level_param.IsReadOnly:
                    level_param.Set(level.Id)
                t.Commit()
        
        # Update height offset and other properties
        if height_offset != 0 or floor_type or thickness or properties:
            with DB.Transaction(doc, "Update Floor Properties") as t:
                t.Start()
                
                # Update height offset
                if height_offset != 0:
                    height_offset_ft = float(height_offset) / 304.8
                    height_param = floor.LookupParameter("Height Offset From Level")
                    if height_param and not height_param.IsReadOnly:
                        height_param.Set(height_offset_ft)
                
                # Update floor type if specified
                if floor_type and floor.FloorType.Id.IntegerValue != floor_type.Id.IntegerValue:
                    floor.FloorType = floor_type
                
                # Update thickness if specified
                if thickness:
                    _set_floor_thickness(floor, thickness)
                
                # Set additional properties
                if properties:
                    _set_floor_properties(floor, properties)
                
                t.Commit()
        
        return floor
        
    except Exception as e:
        logger.error("Failed to edit existing floor: {}".format(str(e)))
        raise


def _set_floor_thickness(floor, thickness_mm):
    """Set floor thickness by modifying the floor type"""
    try:
        thickness_ft = float(thickness_mm) / 304.8
        
        # Get the floor type
        floor_type = floor.FloorType
        if not floor_type:
            return
        
        # Try to modify the compound structure
        compound_structure = floor_type.GetCompoundStructure()
        if compound_structure and compound_structure.LayerCount > 0:
            # Modify the first structural layer
            layers = list(compound_structure.GetLayers())
            for i, layer in enumerate(layers):
                if layer.Function == DB.MaterialFunctionAssignment.Structure:
                    layer.Width = thickness_ft
                    compound_structure.SetLayer(i, layer)
                    floor_type.SetCompoundStructure(compound_structure)
                    break
        
    except Exception as e:
        logger.warning("Could not set floor thickness: {}".format(str(e)))


def _project_curve_to_plane_height(curve, plane_height):
    """Project a curve to a specific plane height (Z coordinate)"""
    try:
        if hasattr(curve, 'GetEndPoint'):
            # Handle Line curves
            start_point = curve.GetEndPoint(0)
            end_point = curve.GetEndPoint(1)
            
            # Create new points with the plane height
            new_start = DB.XYZ(start_point.X, start_point.Y, plane_height)
            new_end = DB.XYZ(end_point.X, end_point.Y, plane_height)
            
            return DB.Line.CreateBound(new_start, new_end)
            
        elif hasattr(curve, 'Center'):
            # Handle Arc curves
            center = curve.Center
            radius = curve.Radius
            start_point = curve.GetEndPoint(0)
            end_point = curve.GetEndPoint(1)
            
            # Create new points with the plane height
            new_center = DB.XYZ(center.X, center.Y, plane_height)
            new_start = DB.XYZ(start_point.X, start_point.Y, plane_height)
            new_end = DB.XYZ(end_point.X, end_point.Y, plane_height)
            
            return DB.Arc.Create(new_start, new_end, new_center)
            
        else:
            # For other curve types, try to get tessellated points and recreate
            logger.warning("Unsupported curve type for height projection, using original curve")
            return curve
            
    except Exception as e:
        logger.warning("Failed to project curve to plane height: {}".format(str(e)))
        return curve


def _set_floor_properties(floor, properties):
    """Set additional properties on the floor element"""
    try:
        for param_name, param_value in properties.items():
            param = floor.LookupParameter(param_name)
            if param and not param.IsReadOnly:
                if param.StorageType == DB.StorageType.String:
                    param.Set(str(param_value))
                elif param.StorageType == DB.StorageType.Integer:
                    param.Set(int(param_value))
                elif param.StorageType == DB.StorageType.Double:
                    param.Set(float(param_value))
                    
    except Exception as e:
        logger.warning("Could not set floor properties: {}".format(str(e))) 