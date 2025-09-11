# -*- coding: UTF-8 -*-
"""
Column Management Module for Revit MCP
Handles structural column creation, editing, and querying functionality
"""

from .utils import get_element_name, RoomWarningSwallower, find_family_symbol_safely
from pyrevit import routes, revit, DB
import json
import traceback
import logging
import math

logger = logging.getLogger(__name__)


def register_column_management_routes(api):
    """Register all column management routes with the API"""

    @api.route("/create_or_edit_column/", methods=["POST"])
    @api.route("/create_or_edit_column", methods=["POST"])
    def create_or_edit_column(doc, request):
        """
        Create a new structural column or edit an existing column in Revit.
        
        This tool can operate in two modes:
        1. Creation Mode (when element_id is None): Creates a new column
        2. Edit Mode (when element_id is provided): Modifies an existing column
        
        Expected request data:
        {
            "element_id": "123456",  // Optional - for editing existing column
            "family_name": "Concrete-Rectangular-Column",  // Required - column family name
            "type_name": "600 x 600mm",  // Optional - column type name
            "location": {"x": 0, "y": 0, "z": 0},  // Required - column location in mm
            "base_level": "Level 1",  // Required - base level name
            "top_level": "Level 2",  // Optional - top level name (if not provided, uses height)
            "height": 3000.0,  // Optional - column height in mm (if top_level not provided)
            "base_offset": 0.0,  // Optional - offset from base level in mm
            "top_offset": 0.0,  // Optional - offset from top level in mm
            "rotation": 0.0,  // Optional - rotation angle in degrees
            "structural_type": "Column",  // Optional - "Column", "Beam", "Brace", "NonStructural"
            "structural_usage": "Other",  // Optional - "Other", "Girder", "Purlin", etc.
            "properties": {  // Optional - additional parameters
                "Mark": "C1",
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
            family_name = data.get("family_name")
            type_name = data.get("type_name")
            location = data.get("location", {})
            base_level_name = data.get("base_level")
            top_level_name = data.get("top_level")
            height = data.get("height")
            base_offset = data.get("base_offset", 0.0)
            top_offset = data.get("top_offset", 0.0)
            rotation = data.get("rotation", 0.0)
            structural_type = data.get("structural_type", "Column")
            structural_usage = data.get("structural_usage", "Other")
            properties = data.get("properties", {})

            # Basic validation
            if not family_name:
                return routes.make_response(
                    data={"error": "family_name is required"}, status=400
                )

            if not base_level_name:
                return routes.make_response(
                    data={"error": "base_level is required"}, status=400
                )

            if not location or "x" not in location or "y" not in location:
                return routes.make_response(
                    data={"error": "location with x and y coordinates is required"}, status=400
                )

            if not top_level_name and not height:
                return routes.make_response(
                    data={"error": "Either top_level or height must be specified"}, status=400
                )

            logger.info("Column operation: {} mode, family: {}".format(
                "Edit" if element_id else "Create", family_name
            ))

            # Find the base level
            base_level = None
            levels = (
                DB.FilteredElementCollector(doc)
                .OfCategory(DB.BuiltInCategory.OST_Levels)
                .WhereElementIsNotElementType()
                .ToElements()
            )

            for level in levels:
                try:
                    level_name_safe = get_element_name(level)
                    if level_name_safe == base_level_name:
                        base_level = level
                        break
                except:
                    continue

            if not base_level:
                return routes.make_response(
                    data={"error": "Base level not found: {}".format(base_level_name)},
                    status=404,
                )

            # Find the top level if specified
            top_level = None
            if top_level_name:
                for level in levels:
                    try:
                        level_name_safe = get_element_name(level)
                        if level_name_safe == top_level_name:
                            top_level = level
                            break
                    except:
                        continue

                if not top_level:
                    return routes.make_response(
                        data={"error": "Top level not found: {}".format(top_level_name)},
                        status=404,
                    )

            # Find column family symbol
            column_symbol = find_family_symbol_safely(doc, family_name, type_name)
            if not column_symbol:
                return routes.make_response(
                    data={"error": "Column family/type not found: {} - {}".format(family_name, type_name or "default")},
                    status=404,
                )

            # Check if this is an edit operation
            existing_column = None
            if element_id:
                try:
                    elem_id = DB.ElementId(int(element_id))
                    existing_column = doc.GetElement(elem_id)
                    if not existing_column or not isinstance(existing_column, DB.FamilyInstance) or \
                       existing_column.Category.Id.Value != int(DB.BuiltInCategory.OST_StructuralColumns):
                        return routes.make_response(
                            data={"error": "Element with ID {} is not a structural column".format(element_id)},
                            status=404,
                        )
                except:
                    return routes.make_response(
                        data={"error": "Invalid element_id: {}".format(element_id)},
                        status=400,
                    )

            try:
                new_column = None
                
                if existing_column:
                    # Edit existing column
                    new_column = _edit_existing_column(
                        doc, existing_column, column_symbol, location, 
                        base_level, top_level, height, base_offset, top_offset, 
                        rotation, structural_type, structural_usage, properties
                    )
                else:
                    # Create new column
                    with DB.Transaction(doc, "Create Column via MCP") as t:
                        t.Start()
                        new_column = _create_new_column(
                            doc, column_symbol, location, base_level, top_level, 
                            height, base_offset, top_offset, rotation, 
                            structural_type, structural_usage, properties
                        )
                        if not new_column:
                            t.RollBack()
                            return routes.make_response(
                                data={"error": "Failed to create column"}, status=500
                            )
                        t.Commit()

                if not new_column:
                    return routes.make_response(
                        data={"error": "Failed to create/edit column"}, status=500
                    )
                
                operation = "edited" if existing_column else "created"
                column_name = get_element_name(new_column)
                
                return routes.make_response(
                    data={
                        "message": "Successfully {} column '{}'".format(operation, column_name),
                        "column_id": str(new_column.Id.Value),
                        "column_name": column_name,
                        "family_name": family_name,
                        "type_name": type_name or "default",
                        "base_level": base_level_name,
                        "top_level": top_level_name,
                        "operation": operation
                    },
                    status=200
                )

            except Exception as creation_error:
                logger.error("Column operation failed: {}".format(str(creation_error)))
                return routes.make_response(
                    data={"error": "Column operation failed: {}".format(str(creation_error))},
                    status=500,
                )

        except Exception as e:
            logger.error("Column management error: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Column management error: {}".format(str(e))},
                status=500,
            )

    @api.route("/query_column/", methods=["POST"])
    @api.route("/query_column", methods=["POST"])
    def query_column(doc, request):
        """
        Query an existing column by ID and return its configuration.
        
        Expected request data:
        {
            "element_id": "123456"  // Required - column element ID
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
                column = doc.GetElement(elem_id)
                if not column or not isinstance(column, DB.FamilyInstance) or \
                   column.Category.Id.Value != int(DB.BuiltInCategory.OST_StructuralColumns):
                    return routes.make_response(
                        data={"error": "Element with ID {} is not a structural column".format(element_id)},
                        status=404,
                    )
            except:
                return routes.make_response(
                    data={"error": "Invalid element_id: {}".format(element_id)},
                    status=400,
                )

            # Extract column properties
            column_config = _extract_column_config(column, doc)
            
            return routes.make_response(
                data={
                    "message": "Successfully queried column '{}'".format(column_config["name"]),
                    "column_config": column_config
                },
                status=200
            )

        except Exception as e:
            logger.error("Column query error: {}".format(str(e)))
            return routes.make_response(
                data={"error": "Column query error: {}".format(str(e))},
                status=500,
            )

    @api.route("/column_details/", methods=["GET"])
    @api.route("/column_details", methods=["GET"])
    @api.route("/get_column_details/", methods=["GET"])
    @api.route("/get_column_details", methods=["GET"])
    def get_column_details():
        """
        Get comprehensive information about selected structural column elements in Revit
        
        Returns detailed information including:
        - Column name, family, type, and ID information
        - Location and geometry information
        - Base and top level information with offsets
        - Structural properties (type, usage, material)
        - Cross-section properties and dimensions
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
                        "columns": []
                    }
                )
            
            columns_info = []
            
            for elem_id in selected_ids:
                try:
                    element = doc.GetElement(elem_id)
                    if not element:
                        continue
                    
                    # Check if element is a structural column
                    if not (isinstance(element, DB.FamilyInstance) and 
                           element.Category and element.Category.Id.Value == int(DB.BuiltInCategory.OST_StructuralColumns)):
                        continue
                    
                    column_info = {
                        "id": str(elem_id.Value),
                        "name": get_element_name(element)
                    }
                    
                    # ============ FAMILY AND TYPE INFORMATION ============
                    try:
                        symbol = element.Symbol
                        if symbol:
                            column_info["family_name"] = get_element_name(symbol.Family)
                            column_info["type_name"] = get_element_name(symbol)
                            column_info["type_id"] = str(symbol.Id.Value)
                            
                            # Get detailed type properties
                            type_properties = _extract_type_properties(symbol)
                            column_info["type_properties"] = type_properties
                        else:
                            column_info["family_name"] = "Unknown"
                            column_info["type_name"] = "Unknown"
                            column_info["type_id"] = "Unknown"
                            column_info["type_properties"] = {}
                    except Exception as e:
                        column_info["family_name"] = "Unknown"
                        column_info["type_name"] = "Unknown"
                        column_info["type_id"] = "Unknown"
                        column_info["type_properties"] = {}
                        column_info["type_error"] = str(e)
                    
                    # ============ LOCATION INFORMATION ============
                    try:
                        location = element.Location
                        if location and hasattr(location, 'Point'):
                            # Point-based column
                            point = location.Point
                            column_info["location"] = {
                                "x": round(point.X * 304.8, 2),  # Convert to mm
                                "y": round(point.Y * 304.8, 2),
                                "z": round(point.Z * 304.8, 2)
                            }
                            column_info["location_type"] = "point"
                            
                            # Get rotation if available
                            if hasattr(location, 'Rotation'):
                                column_info["rotation"] = round(math.degrees(location.Rotation), 2)
                            else:
                                column_info["rotation"] = 0.0
                                
                        elif location and hasattr(location, 'Curve'):
                            # Line-based column (slanted)
                            curve = location.Curve
                            start_pt = curve.GetEndPoint(0)
                            end_pt = curve.GetEndPoint(1)
                            
                            column_info["location_type"] = "line"
                            column_info["start_point"] = {
                                "x": round(start_pt.X * 304.8, 2),
                                "y": round(start_pt.Y * 304.8, 2),
                                "z": round(start_pt.Z * 304.8, 2)
                            }
                            column_info["end_point"] = {
                                "x": round(end_pt.X * 304.8, 2),
                                "y": round(end_pt.Y * 304.8, 2),
                                "z": round(end_pt.Z * 304.8, 2)
                            }
                            column_info["length"] = round(curve.Length * 304.8, 2)
                            
                        else:
                            column_info["location"] = None
                            column_info["location_type"] = "unknown"
                            
                    except Exception as e:
                        column_info["location"] = None
                        column_info["location_type"] = "error"
                        column_info["location_error"] = str(e)
                    
                    # ============ LEVEL INFORMATION ============
                    try:
                        # Base level
                        if hasattr(element, 'LevelId') and element.LevelId:
                            base_level = doc.GetElement(element.LevelId)
                            if base_level:
                                column_info["base_level"] = get_element_name(base_level)
                                column_info["base_level_id"] = str(element.LevelId.Value)
                                column_info["base_level_elevation"] = round(base_level.Elevation * 304.8, 2)
                            else:
                                column_info["base_level"] = "Unknown"
                                column_info["base_level_id"] = "Unknown"
                                column_info["base_level_elevation"] = 0
                        else:
                            column_info["base_level"] = "None"
                            column_info["base_level_id"] = "None"
                            column_info["base_level_elevation"] = 0
                            
                        # Top level (if available)
                        top_level_param = element.LookupParameter("Top Level")
                        if top_level_param and top_level_param.HasValue:
                            top_level_id = top_level_param.AsElementId()
                            if top_level_id and top_level_id.Value != -1:
                                top_level = doc.GetElement(top_level_id)
                                if top_level:
                                    column_info["top_level"] = get_element_name(top_level)
                                    column_info["top_level_id"] = str(top_level_id.Value)
                                    column_info["top_level_elevation"] = round(top_level.Elevation * 304.8, 2)
                                else:
                                    column_info["top_level"] = "Unknown"
                                    column_info["top_level_id"] = "Unknown"
                                    column_info["top_level_elevation"] = 0
                            else:
                                column_info["top_level"] = "None"
                                column_info["top_level_id"] = "None"
                                column_info["top_level_elevation"] = 0
                        else:
                            column_info["top_level"] = "None"
                            column_info["top_level_id"] = "None"
                            column_info["top_level_elevation"] = 0
                            
                    except Exception as e:
                        column_info["base_level"] = "Error"
                        column_info["top_level"] = "Error"
                        column_info["level_error"] = str(e)
                    
                    # ============ OFFSET INFORMATION ============
                    try:
                        # Base offset
                        base_offset_param = element.LookupParameter("Base Offset")
                        if base_offset_param and base_offset_param.HasValue:
                            column_info["base_offset"] = round(base_offset_param.AsDouble() * 304.8, 2)
                        else:
                            column_info["base_offset"] = 0.0
                            
                        # Top offset
                        top_offset_param = element.LookupParameter("Top Offset")
                        if top_offset_param and top_offset_param.HasValue:
                            column_info["top_offset"] = round(top_offset_param.AsDouble() * 304.8, 2)
                        else:
                            column_info["top_offset"] = 0.0
                            
                        # Unconnected height
                        height_param = element.LookupParameter("Unconnected Height")
                        if height_param and height_param.HasValue:
                            column_info["height"] = round(height_param.AsDouble() * 304.8, 2)
                        else:
                            column_info["height"] = 0.0
                            
                    except Exception as e:
                        column_info["base_offset"] = 0.0
                        column_info["top_offset"] = 0.0
                        column_info["height"] = 0.0
                        column_info["offset_error"] = str(e)
                    
                    # ============ STRUCTURAL PROPERTIES ============
                    try:
                        # Structural type
                        if hasattr(element, 'StructuralType'):
                            column_info["structural_type"] = str(element.StructuralType).split(".")[-1]
                        else:
                            column_info["structural_type"] = "Unknown"
                            
                        # Structural usage
                        if hasattr(element, 'StructuralUsage'):
                            column_info["structural_usage"] = str(element.StructuralUsage).split(".")[-1]
                        else:
                            column_info["structural_usage"] = "Unknown"
                            
                        # Structural material
                        if hasattr(element, 'StructuralMaterialId') and element.StructuralMaterialId:
                            material = doc.GetElement(element.StructuralMaterialId)
                            if material:
                                column_info["structural_material"] = get_element_name(material)
                            else:
                                column_info["structural_material"] = "Unknown"
                        else:
                            column_info["structural_material"] = "None"
                            
                        # Is slanted column
                        if hasattr(element, 'IsSlantedColumn'):
                            column_info["is_slanted"] = element.IsSlantedColumn
                        else:
                            column_info["is_slanted"] = False
                            
                    except Exception as e:
                        column_info["structural_type"] = "Error"
                        column_info["structural_usage"] = "Error"
                        column_info["structural_material"] = "Error"
                        column_info["is_slanted"] = False
                        column_info["structural_error"] = str(e)
                    
                    # ============ CROSS-SECTION PROPERTIES ============
                    try:
                        # Get cross-section dimensions from family parameters
                        cross_section = {}
                        
                        # Common dimension parameters
                        dimension_params = ["b", "h", "Width", "Height", "Diameter", "d", "bf", "tf", "tw"]
                        
                        for param_name in dimension_params:
                            try:
                                param = element.LookupParameter(param_name)
                                if not param:
                                    # Try symbol parameter
                                    param = element.Symbol.LookupParameter(param_name)
                                    
                                if param and param.HasValue and param.StorageType == DB.StorageType.Double:
                                    cross_section[param_name] = round(param.AsDouble() * 304.8, 2)  # Convert to mm
                            except:
                                continue
                                
                        column_info["cross_section"] = cross_section
                        
                    except Exception as e:
                        column_info["cross_section"] = {}
                        column_info["cross_section_error"] = str(e)
                    
                    # ============ ADDITIONAL PARAMETERS ============
                    additional_params = {}
                    param_names = [
                        "Mark", "Comments", "Volume", "Length", "Area", 
                        "Structural Material", "Phasing Created", "Phasing Demolished"
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
                                    # Convert length/area/volume to metric
                                    if param_name in ["Length", "Height"]:
                                        value = round(param.AsDouble() * 304.8, 2)  # ft to mm
                                    elif param_name == "Area":
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
                                    additional_params[param_name] = str(value).strip()
                        except:
                            continue
                    
                    column_info["parameters"] = additional_params
                    
                    # ============ BOUNDING BOX ============
                    try:
                        bbox = element.get_BoundingBox(None)
                        if bbox:
                            column_info["bounding_box"] = {
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
                            column_info["bounding_box"] = None
                    except:
                        column_info["bounding_box"] = None
                    
                    columns_info.append(column_info)
                    
                except Exception as e:
                    logger.warning("Could not process column element {}: {}".format(elem_id, str(e)))
                    continue
            
            # Prepare response
            response_data = {
                "message": "Successfully retrieved {} column elements".format(len(columns_info)),
                "selected_count": len(selected_ids),
                "columns_found": len(columns_info),
                "columns": columns_info
            }
            
            return routes.make_response(data=response_data, status=200)
            
        except Exception as e:
            logger.error("Failed to get column details: {}".format(str(e)))
            return routes.make_response(
                data={
                    "error": "Failed to retrieve column details: {}".format(str(e))
                },
                status=500
            )


def _create_new_column(doc, column_symbol, location, base_level, top_level, height, 
                      base_offset, top_offset, rotation, structural_type, structural_usage, properties):
    """Create a new structural column element"""
    try:
        # Ensure the symbol is activated
        if not column_symbol.IsActive:
            column_symbol.Activate()
            doc.Regenerate()

        # Convert coordinates from mm to feet
        point = DB.XYZ(
            float(location.get("x", 0)) / 304.8,
            float(location.get("y", 0)) / 304.8,
            float(location.get("z", 0)) / 304.8
        )

        # Convert structural type string to enum
        struct_type = _get_structural_type_enum(structural_type)

        # Create the column
        if top_level:
            # Column between two levels
            new_column = doc.Create.NewFamilyInstance(
                point, column_symbol, base_level, struct_type
            )
            
            # Set top level
            top_level_param = new_column.LookupParameter("Top Level")
            if top_level_param and not top_level_param.IsReadOnly:
                top_level_param.Set(top_level.Id)
                
        else:
            # Column with specified height
            new_column = doc.Create.NewFamilyInstance(
                point, column_symbol, base_level, struct_type
            )
            
            # Set unconnected height
            if height:
                height_ft = float(height) / 304.8
                height_param = new_column.LookupParameter("Unconnected Height")
                if height_param and not height_param.IsReadOnly:
                    height_param.Set(height_ft)

        # Set base offset if specified
        if base_offset != 0:
            base_offset_ft = float(base_offset) / 304.8
            base_offset_param = new_column.LookupParameter("Base Offset")
            if base_offset_param and not base_offset_param.IsReadOnly:
                base_offset_param.Set(base_offset_ft)

        # Set top offset if specified
        if top_offset != 0:
            top_offset_ft = float(top_offset) / 304.8
            top_offset_param = new_column.LookupParameter("Top Offset")
            if top_offset_param and not top_offset_param.IsReadOnly:
                top_offset_param.Set(top_offset_ft)

        # Apply rotation if specified
        if rotation != 0:
            rotation_rad = math.radians(float(rotation))
            location_obj = new_column.Location
            if location_obj and hasattr(location_obj, 'Rotate'):
                axis = DB.Line.CreateBound(point, point + DB.XYZ.BasisZ)
                location_obj.Rotate(axis, rotation_rad)

        # Set structural usage
        if structural_usage != "Other":
            struct_usage = _get_structural_usage_enum(structural_usage)
            if hasattr(new_column, 'StructuralUsage'):
                new_column.StructuralUsage = struct_usage

        # Set additional properties
        if properties:
            _set_column_properties(new_column, properties)

        return new_column
        
    except Exception as e:
        logger.error("Failed to create new column: {}".format(str(e)))
        raise


def _edit_existing_column(doc, column, column_symbol, location, base_level, top_level, 
                         height, base_offset, top_offset, rotation, structural_type, 
                         structural_usage, properties):
    """Edit an existing structural column element"""
    try:
        with DB.Transaction(doc, "Edit Column via MCP") as t:
            t.Start()
            
            # Update column type if different
            if column.Symbol.Id.Value != column_symbol.Id.Value:
                column.Symbol = column_symbol
            
            # Update location if specified
            if location and "x" in location and "y" in location:
                new_point = DB.XYZ(
                    float(location.get("x", 0)) / 304.8,
                    float(location.get("y", 0)) / 304.8,
                    float(location.get("z", 0)) / 304.8
                )
                
                location_obj = column.Location
                if location_obj and hasattr(location_obj, 'Point'):
                    location_obj.Point = new_point
            
            # Update base level if different
            if column.LevelId.Value != base_level.Id.Value:
                level_param = column.LookupParameter("Base Level")
                if level_param and not level_param.IsReadOnly:
                    level_param.Set(base_level.Id)
            
            # Update top level
            if top_level:
                top_level_param = column.LookupParameter("Top Level")
                if top_level_param and not top_level_param.IsReadOnly:
                    top_level_param.Set(top_level.Id)
            
            # Update height if specified and no top level
            if height and not top_level:
                height_ft = float(height) / 304.8
                height_param = column.LookupParameter("Unconnected Height")
                if height_param and not height_param.IsReadOnly:
                    height_param.Set(height_ft)
            
            # Update offsets
            if base_offset != 0:
                base_offset_ft = float(base_offset) / 304.8
                base_offset_param = column.LookupParameter("Base Offset")
                if base_offset_param and not base_offset_param.IsReadOnly:
                    base_offset_param.Set(base_offset_ft)
            
            if top_offset != 0:
                top_offset_ft = float(top_offset) / 304.8
                top_offset_param = column.LookupParameter("Top Offset")
                if top_offset_param and not top_offset_param.IsReadOnly:
                    top_offset_param.Set(top_offset_ft)
            
            # Update rotation if specified
            if rotation != 0:
                rotation_rad = math.radians(float(rotation))
                location_obj = column.Location
                if location_obj and hasattr(location_obj, 'Rotate'):
                    point = location_obj.Point
                    axis = DB.Line.CreateBound(point, point + DB.XYZ.BasisZ)
                    location_obj.Rotate(axis, rotation_rad)
            
            # Update structural properties
            if structural_type and hasattr(column, 'StructuralType'):
                struct_type = _get_structural_type_enum(structural_type)
                column.StructuralType = struct_type
            
            if structural_usage and hasattr(column, 'StructuralUsage'):
                struct_usage = _get_structural_usage_enum(structural_usage)
                column.StructuralUsage = struct_usage
            
            # Set additional properties
            if properties:
                _set_column_properties(column, properties)
            
            t.Commit()
            return column
        
    except Exception as e:
        logger.error("Failed to edit existing column: {}".format(str(e)))
        raise


def _get_structural_type_enum(structural_type_str):
    """Convert structural type string to Revit enum"""
    try:
        if structural_type_str == "Column":
            return DB.Structure.StructuralType.Column
        elif structural_type_str == "Beam":
            return DB.Structure.StructuralType.Beam
        elif structural_type_str == "Brace":
            return DB.Structure.StructuralType.Brace
        elif structural_type_str == "NonStructural":
            return DB.Structure.StructuralType.NonStructural
        else:
            return DB.Structure.StructuralType.Column  # Default
    except:
        return DB.Structure.StructuralType.Column


def _get_structural_usage_enum(structural_usage_str):
    """Convert structural usage string to Revit enum"""
    try:
        if structural_usage_str == "Girder":
            return DB.Structure.StructuralInstanceUsage.Girder
        elif structural_usage_str == "Purlin":
            return DB.Structure.StructuralInstanceUsage.Purlin
        elif structural_usage_str == "Joist":
            return DB.Structure.StructuralInstanceUsage.Joist
        elif structural_usage_str == "Kicker":
            return DB.Structure.StructuralInstanceUsage.Kicker
        elif structural_usage_str == "Other":
            return DB.Structure.StructuralInstanceUsage.Other
        else:
            return DB.Structure.StructuralInstanceUsage.Other  # Default
    except:
        return DB.Structure.StructuralInstanceUsage.Other


def _set_column_properties(column, properties):
    """Set additional properties on the column element"""
    try:
        for param_name, param_value in properties.items():
            param = column.LookupParameter(param_name)
            if param and not param.IsReadOnly:
                if param.StorageType == DB.StorageType.String:
                    param.Set(str(param_value))
                elif param.StorageType == DB.StorageType.Integer:
                    param.Set(int(param_value))
                elif param.StorageType == DB.StorageType.Double:
                    param.Set(float(param_value))
                    
    except Exception as e:
        logger.warning("Could not set column properties: {}".format(str(e)))


def _extract_column_config(column, doc):
    """Extract configuration from an existing column"""
    try:
        config = {
            "element_id": column.Id.Value,
            "name": get_element_name(column),
        }
        
        # Get family and type information
        symbol = column.Symbol
        if symbol:
            config["family_name"] = get_element_name(symbol.Family)
            config["type_name"] = get_element_name(symbol)
        
        # Get location
        location = column.Location
        if location and hasattr(location, 'Point'):
            point = location.Point
            config["location"] = {
                "x": round(point.X * 304.8, 2),
                "y": round(point.Y * 304.8, 2),
                "z": round(point.Z * 304.8, 2)
            }
            
            if hasattr(location, 'Rotation'):
                config["rotation"] = round(math.degrees(location.Rotation), 2)
        
        # Get level information
        if hasattr(column, 'LevelId') and column.LevelId:
            base_level = doc.GetElement(column.LevelId)
            if base_level:
                config["base_level"] = get_element_name(base_level)
        
        # Get top level
        top_level_param = column.LookupParameter("Top Level")
        if top_level_param and top_level_param.HasValue:
            top_level_id = top_level_param.AsElementId()
            if top_level_id and top_level_id.Value != -1:
                top_level = doc.GetElement(top_level_id)
                if top_level:
                    config["top_level"] = get_element_name(top_level)
        
        # Get offsets and height
        base_offset_param = column.LookupParameter("Base Offset")
        if base_offset_param and base_offset_param.HasValue:
            config["base_offset"] = round(base_offset_param.AsDouble() * 304.8, 2)
        
        top_offset_param = column.LookupParameter("Top Offset")
        if top_offset_param and top_offset_param.HasValue:
            config["top_offset"] = round(top_offset_param.AsDouble() * 304.8, 2)
        
        height_param = column.LookupParameter("Unconnected Height")
        if height_param and height_param.HasValue:
            config["height"] = round(height_param.AsDouble() * 304.8, 2)
        
        # Get structural properties
        if hasattr(column, 'StructuralType'):
            config["structural_type"] = str(column.StructuralType).split(".")[-1]
        
        if hasattr(column, 'StructuralUsage'):
            config["structural_usage"] = str(column.StructuralUsage).split(".")[-1]
        
        return config
        
    except Exception as e:
        logger.error("Failed to extract column config: {}".format(str(e)))
        raise


def _extract_type_properties(symbol):
    """Extract comprehensive type properties from a column family symbol"""
    try:
        type_properties = {}
        
        # ============ BASIC TYPE INFORMATION ============
        type_properties["type_name"] = get_element_name(symbol)
        type_properties["family_name"] = get_element_name(symbol.Family)
        type_properties["category"] = symbol.Category.Name if symbol.Category else "Unknown"
        
        # ============ DIMENSIONAL PROPERTIES ============
        dimensions = {}
        
        # Common structural column dimension parameters
        dimension_param_names = [
            # Concrete columns
            "b", "h", "Width", "Height", "Depth",
            # Steel columns  
            "d", "bf", "tf", "tw", "r", "k", "k1",
            # Round columns
            "Diameter", "Radius", "r_outer", "r_inner",
            # General dimensions
            "Cross-Sectional Area", "Moment of Inertia Ix", "Moment of Inertia Iy",
            "Section Modulus Sx", "Section Modulus Sy", "Radius of Gyration ix", "Radius of Gyration iy",
            "Warping Constant", "Torsional Constant", "Perimeter", "Weight per Unit Length"
        ]
        
        for param_name in dimension_param_names:
            try:
                param = symbol.LookupParameter(param_name)
                if param and param.HasValue:
                    if param.StorageType == DB.StorageType.Double:
                        # Convert based on parameter type
                        value = param.AsDouble()
                        if param_name in ["b", "h", "Width", "Height", "Depth", "d", "bf", "tf", "tw", "r", "k", "k1", "Diameter", "Radius", "r_outer", "r_inner"]:
                            # Linear dimensions - convert to mm
                            dimensions[param_name] = round(value * 304.8, 2)
                        elif param_name in ["Cross-Sectional Area"]:
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
            "Shear Modulus", "Thermal Expansion Coefficient", "Unit Weight", "Damping Ratio"
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
            "Cost", "URL", "Fire Rating"
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
            "Analytical Model", "Enable Analytical Model"
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
        logger.warning("Could not extract type properties: {}".format(str(e)))
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
            "Compressive Strength", "Tensile Strength", "Yield Strength"
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