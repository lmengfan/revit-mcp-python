# -*- coding: UTF-8 -*-
"""
Model Info Module for Revit MCP
Provides comprehensive model information for architects and designers
"""

from pyrevit import routes, revit, DB
from pyrevit.revit.db import ProjectInfo as RevitProjectInfo
import pyrevit.revit.db.query as q
import logging

from utils import normalize_string, get_element_name

logger = logging.getLogger(__name__)


def register_model_info_routes(api):
    """Register all model information routes with the API"""

    @api.route("/model_info/", methods=["GET"])
    @api.route("/model_info", methods=["GET"])
    def get_model_info():
        """
        Get comprehensive information about the current Revit model

        Returns architect-focused information including:
        - Project details (name, number, client)
        - Element counts by major categories
        - Basic warnings count
        - Views and sheets overview
        - Room information with levels
        - Link status
        """
        try:
            doc = revit.doc
            if not doc:
                return routes.make_response(
                    data={"error": "No active Revit document"}, status=503
                )

            # ============ PROJECT INFORMATION ============
            try:
                revit_project_info = RevitProjectInfo(doc)
                project_info = {
                    "name": normalize_string(revit_project_info.name),
                    "number": normalize_string(revit_project_info.number),
                    "client": normalize_string(revit_project_info.client_name),
                    "file_name": normalize_string(doc.Title),
                }
            except Exception as e:
                logger.warning("Could not get full project info: {}".format(str(e)))
                project_info = {
                    "name": normalize_string(doc.Title),
                    "number": "Not Set",
                    "client": "Not Set",
                    "file_name": normalize_string(doc.Title),
                }

            # ============ ELEMENT COUNTS ============
            element_categories = {
                "Walls": DB.BuiltInCategory.OST_Walls,
                "Floors": DB.BuiltInCategory.OST_Floors,
                "Ceilings": DB.BuiltInCategory.OST_Ceilings,
                "Roofs": DB.BuiltInCategory.OST_Roofs,
                "Doors": DB.BuiltInCategory.OST_Doors,
                "Windows": DB.BuiltInCategory.OST_Windows,
                "Stairs": DB.BuiltInCategory.OST_Stairs,
                "Railings": DB.BuiltInCategory.OST_Railings,
                "Columns": DB.BuiltInCategory.OST_Columns,
                "Structural_Framing": DB.BuiltInCategory.OST_StructuralFraming,
                "Furniture": DB.BuiltInCategory.OST_Furniture,
                "Lighting_Fixtures": DB.BuiltInCategory.OST_LightingFixtures,
                "Plumbing_Fixtures": DB.BuiltInCategory.OST_PlumbingFixtures,
            }

            element_counts = {}
            total_elements = 0

            for name, category in element_categories.items():
                try:
                    count = (
                        DB.FilteredElementCollector(doc)
                        .OfCategory(category)
                        .WhereElementIsNotElementType()
                        .GetElementCount()
                    )
                    element_counts[name] = count
                    total_elements += count
                except:
                    element_counts[name] = 0

            # ============ WARNINGS ============
            try:
                warnings = doc.GetWarnings()
                warnings_count = len(warnings)
                # Count critical warnings (simplified check)
                critical_warnings = sum(
                    1 for w in warnings if w.GetSeverity() == DB.WarningType.Error
                )
            except:
                warnings_count = 0
                critical_warnings = 0

            # ============ LEVELS ============
            try:
                levels_collector = (
                    DB.FilteredElementCollector(doc)
                    .OfCategory(DB.BuiltInCategory.OST_Levels)
                    .WhereElementIsNotElementType()
                    .ToElements()
                )

                levels_info = []
                for level in levels_collector:
                    level_name = get_element_name(level)
                    try:
                        elevation = level.Elevation
                        levels_info.append(
                            {
                                "name": normalize_string(level_name),
                                "elevation": round(elevation, 2),
                            }
                        )
                    except:
                        levels_info.append(
                            {
                                "name": normalize_string(level_name),
                                "elevation": "Unknown",
                            }
                        )

                # Sort by elevation if available
                try:
                    levels_info.sort(
                        key=lambda x: (
                            x["elevation"]
                            if isinstance(x["elevation"], (int, float))
                            else 0
                        )
                    )
                except:
                    pass

            except Exception as e:
                logger.warning("Could not get levels: {}".format(str(e)))
                levels_info = []

            # ============ ROOMS ============
            try:
                rooms_collector = (
                    DB.FilteredElementCollector(doc)
                    .OfCategory(DB.BuiltInCategory.OST_Rooms)
                    .WhereElementIsNotElementType()
                    .ToElements()
                )

                rooms_info = []
                unplaced_rooms = 0

                for room in rooms_collector:
                    try:
                        # Get room name safely
                        name_param = room.LookupParameter("Name")
                        room_name = (
                            name_param.AsString()
                            if name_param and name_param.HasValue
                            else "Unnamed Room"
                        )

                        # Get room number safely
                        number_param = room.LookupParameter("Number")
                        room_number = (
                            number_param.AsString()
                            if number_param and number_param.HasValue
                            else ""
                        )

                        # Get room level
                        level_name = "Unknown Level"
                        try:
                            level = doc.GetElement(room.LevelId)
                            if level:
                                level_name = get_element_name(level)
                        except:
                            pass

                        # Check if room is placed
                        try:
                            area = room.Area
                            is_placed = area > 0
                            if not is_placed:
                                unplaced_rooms += 1
                        except:
                            is_placed = False
                            unplaced_rooms += 1

                        room_info = {
                            "name": normalize_string(room_name),
                            "number": normalize_string(room_number),
                            "level": normalize_string(level_name),
                            "is_placed": is_placed,
                        }

                        if is_placed:
                            try:
                                room_info["area"] = round(area, 2)
                            except:
                                room_info["area"] = "Unknown"

                        rooms_info.append(room_info)

                    except Exception as e:
                        logger.warning("Could not process room: {}".format(str(e)))
                        continue

            except Exception as e:
                logger.warning("Could not get rooms: {}".format(str(e)))
                rooms_info = []
                unplaced_rooms = 0

            # ============ VIEWS AND SHEETS ============
            try:
                # Get sheets
                sheets_count = (
                    DB.FilteredElementCollector(doc)
                    .OfCategory(DB.BuiltInCategory.OST_Sheets)
                    .WhereElementIsNotElementType()
                    .GetElementCount()
                )

                # Get views (excluding templates and invalid types)
                all_views = (
                    DB.FilteredElementCollector(doc).OfClass(DB.View).ToElements()
                )

                valid_views = [
                    v
                    for v in all_views
                    if hasattr(v, "IsTemplate")
                    and not v.IsTemplate
                    and v.ViewType != DB.ViewType.Internal
                    and v.ViewType != DB.ViewType.ProjectBrowser
                ]

                views_count = len(valid_views)

                # Count major view types
                floor_plans = sum(
                    1 for v in valid_views if v.ViewType == DB.ViewType.FloorPlan
                )
                elevations = sum(
                    1 for v in valid_views if v.ViewType == DB.ViewType.Elevation
                )
                sections = sum(
                    1 for v in valid_views if v.ViewType == DB.ViewType.Section
                )
                threed_views = sum(
                    1 for v in valid_views if v.ViewType == DB.ViewType.ThreeD
                )
                schedules = sum(
                    1 for v in valid_views if v.ViewType == DB.ViewType.Schedule
                )

            except Exception as e:
                logger.warning("Could not get views/sheets: {}".format(str(e)))
                sheets_count = 0
                views_count = 0
                floor_plans = elevations = sections = threed_views = schedules = 0

            # ============ LINKED MODELS ============
            try:
                linked_models = []
                rvt_links = q.get_linked_model_instances(doc).ToElements()

                for link_instance in rvt_links:
                    try:
                        link_doc = link_instance.GetLinkDocument()
                        link_name = (
                            q.get_rvt_link_instance_name(link_instance)
                            if hasattr(q, "get_rvt_link_instance_name")
                            else "Unknown Link"
                        )

                        # Get load status
                        link_type = doc.GetElement(link_instance.GetTypeId())
                        status = (
                            str(link_type.GetLinkedFileStatus()).split(".")[-1]
                            if link_type
                            else "Unknown"
                        )

                        # Check if pinned
                        is_pinned = getattr(link_instance, "Pinned", False)

                        linked_models.append(
                            {
                                "name": normalize_string(link_name),
                                "status": status,
                                "is_loaded": link_doc is not None,
                                "is_pinned": is_pinned,
                            }
                        )

                    except Exception as e:
                        logger.warning(
                            "Could not process linked model: {}".format(str(e))
                        )
                        continue

            except Exception as e:
                logger.warning("Could not get linked models: {}".format(str(e)))
                linked_models = []

            # ============ COMPILE RESPONSE ============
            model_data = {
                "project_info": project_info,
                "element_summary": {
                    "total_elements": total_elements,
                    "by_category": element_counts,
                },
                "model_health": {
                    "total_warnings": warnings_count,
                    "critical_warnings": critical_warnings,
                    "unplaced_rooms": unplaced_rooms,
                },
                "spatial_organization": {
                    "levels": levels_info,
                    "rooms": rooms_info,
                    "room_count": len(rooms_info),
                },
                "documentation": {
                    "total_views": views_count,
                    "view_breakdown": {
                        "floor_plans": floor_plans,
                        "elevations": elevations,
                        "sections": sections,
                        "3d_views": threed_views,
                        "schedules": schedules,
                    },
                    "sheets_count": sheets_count,
                },
                "linked_models": {"count": len(linked_models), "models": linked_models},
            }

            return routes.make_response(data=model_data, status=200)

        except Exception as e:
            logger.error("Failed to get model info: {}".format(str(e)))
            return routes.make_response(
                data={
                    "error": "Failed to retrieve model information: {}".format(str(e))
                },
                status=500,
            )

    @api.route("/selected_elements/", methods=["GET"])
    @api.route("/selected_elements", methods=["GET"])
    def get_selected_elements():
        """
        Get information about currently selected elements in Revit
        
        Returns detailed information about each selected element including:
        - Element ID, name, and type
        - Category and category ID
        - Level information (if applicable)
        - Location information (point or curve)
        - Key parameters
        - Summary statistics grouped by category
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
                        "elements": [],
                        "summary": {}
                    }
                )
            
            logger.info("Processing {} selected elements".format(len(selected_ids)))
            
            elements_info = []
            category_summary = {}
            
            for elem_id in selected_ids:
                try:
                    element = doc.GetElement(elem_id)
                    if not element:
                        continue
                    
                    # Basic element information
                    element_info = {
                        "id": str(elem_id.IntegerValue),
                        "name": normalize_string(get_element_name(element)),
                        "type": normalize_string(element.GetType().Name)
                    }
                    
                    # Category information
                    try:
                        if hasattr(element, 'Category') and element.Category:
                            category_name = normalize_string(element.Category.Name)
                            category_id = str(element.Category.Id.IntegerValue)
                            element_info["category"] = category_name
                            element_info["category_id"] = category_id
                            
                            # Update category summary
                            if category_name in category_summary:
                                category_summary[category_name] += 1
                            else:
                                category_summary[category_name] = 1
                        else:
                            element_info["category"] = "Unknown"
                            element_info["category_id"] = "Unknown"
                    except:
                        element_info["category"] = "Unknown"
                        element_info["category_id"] = "Unknown"
                    
                    # Level information
                    try:
                        if hasattr(element, 'LevelId') and element.LevelId:
                            level = doc.GetElement(element.LevelId)
                            if level:
                                element_info["level"] = normalize_string(get_element_name(level))
                                element_info["level_id"] = str(element.LevelId.IntegerValue)
                            else:
                                element_info["level"] = "Unknown"
                                element_info["level_id"] = "Unknown"
                        else:
                            # Try to get level from location
                            level_param = element.LookupParameter("Level")
                            if level_param and level_param.HasValue:
                                level_id = level_param.AsElementId()
                                level = doc.GetElement(level_id)
                                if level:
                                    element_info["level"] = normalize_string(get_element_name(level))
                                    element_info["level_id"] = str(level_id.IntegerValue)
                                else:
                                    element_info["level"] = "None"
                                    element_info["level_id"] = "None"
                            else:
                                element_info["level"] = "None"
                                element_info["level_id"] = "None"
                    except:
                        element_info["level"] = "Unknown"
                        element_info["level_id"] = "Unknown"
                    
                    # Location information
                    try:
                        if hasattr(element, 'Location') and element.Location:
                            location = element.Location
                            if hasattr(location, 'Point') and location.Point:
                                # Point-based element
                                point = location.Point
                                element_info["location"] = {
                                    "type": "Point",
                                    "x": round(point.X, 3),
                                    "y": round(point.Y, 3),
                                    "z": round(point.Z, 3)
                                }
                            elif hasattr(location, 'Curve') and location.Curve:
                                # Line-based element
                                curve = location.Curve
                                start_point = curve.GetEndPoint(0)
                                end_point = curve.GetEndPoint(1)
                                element_info["location"] = {
                                    "type": "Curve",
                                    "start": {
                                        "x": round(start_point.X, 3),
                                        "y": round(start_point.Y, 3),
                                        "z": round(start_point.Z, 3)
                                    },
                                    "end": {
                                        "x": round(end_point.X, 3),
                                        "y": round(end_point.Y, 3),
                                        "z": round(end_point.Z, 3)
                                    },
                                    "length": round(curve.Length, 3)
                                }
                            else:
                                element_info["location"] = {"type": "Unknown"}
                        else:
                            element_info["location"] = {"type": "None"}
                    except Exception as e:
                        element_info["location"] = {"type": "Error", "details": str(e)}
                    
                    # Key parameters
                    key_parameters = {}
                    parameter_names = ["Mark", "Comments", "Type Name", "Family", "Type Comments"]
                    
                    for param_name in parameter_names:
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
                                    if elem_id_val and elem_id_val.IntegerValue != -1:
                                        ref_elem = doc.GetElement(elem_id_val)
                                        value = normalize_string(get_element_name(ref_elem)) if ref_elem else str(elem_id_val.IntegerValue)
                                    else:
                                        value = "None"
                                else:
                                    value = str(param.AsValueString()) if param.AsValueString() else "Unknown"
                                
                                if value and str(value).strip():
                                    key_parameters[param_name] = normalize_string(str(value))
                        except:
                            continue
                    
                    element_info["parameters"] = key_parameters
                    
                    # Family and type information for family instances
                    try:
                        if hasattr(element, 'Symbol') and element.Symbol:
                            symbol = element.Symbol
                            element_info["family_name"] = normalize_string(symbol.Family.Name)
                            element_info["type_name"] = normalize_string(symbol.Name)
                        elif hasattr(element, 'Name'):
                            # For types themselves
                            element_info["type_name"] = normalize_string(element.Name)
                    except:
                        pass
                    
                    elements_info.append(element_info)
                    
                except Exception as e:
                    logger.warning("Could not process selected element {}: {}".format(elem_id, str(e)))
                    continue
            
            # Prepare response
            response_data = {
                "message": "Successfully retrieved {} selected elements".format(len(elements_info)),
                "selected_count": len(elements_info),
                "total_selected_ids": len(selected_ids),
                "elements": elements_info,
                "summary": {
                    "by_category": category_summary,
                    "total_processed": len(elements_info)
                }
            }
            
            return routes.make_response(data=response_data, status=200)
            
        except Exception as e:
            logger.error("Failed to get selected elements: {}".format(str(e)))
            return routes.make_response(
                data={
                    "error": "Failed to retrieve selected elements: {}".format(str(e))
                },
                status=500
            )

    @api.route("/floor_details/", methods=["GET"])
    @api.route("/floor_details", methods=["GET"])
    @api.route("/get_floor_details/", methods=["GET"])
    @api.route("/get_floor_details", methods=["GET"])
    def get_floor_details():
        """
        Get comprehensive information about selected floor elements in Revit
        
        Returns detailed information including:
        - Family Name and Type information
        - Thickness and material properties  
        - Boundary curves and geometry points
        - Level information and height offset
        - Level elevation and Z-coordinate
        - Structural properties and construction details
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
                        "floors": []
                    }
                )
            
            floors_info = []
            
            for elem_id in selected_ids:
                try:
                    element = doc.GetElement(elem_id)
                    if not element:
                        continue
                    
                    # Check if element is a floor
                    if not (hasattr(element, 'Category') and element.Category and 
                           element.Category.Id.IntegerValue == int(DB.BuiltInCategory.OST_Floors)):
                        continue
                    
                    floor_info = {
                        "id": str(elem_id.IntegerValue),
                        "name": normalize_string(get_element_name(element))
                    }
                    
                    # ============ FAMILY AND TYPE INFORMATION ============
                    try:
                        if hasattr(element, 'FloorType') and element.FloorType:
                            floor_type = element.FloorType
                            floor_info["family_name"] = normalize_string(floor_type.Family.Name) if floor_type.Family else "Unknown"
                            floor_info["type_name"] = normalize_string(floor_type.Name)
                            floor_info["type_id"] = str(floor_type.Id.IntegerValue)
                        else:
                            floor_info["family_name"] = "Unknown"
                            floor_info["type_name"] = "Unknown"
                            floor_info["type_id"] = "Unknown"
                    except:
                        floor_info["family_name"] = "Unknown"
                        floor_info["type_name"] = "Unknown"
                        floor_info["type_id"] = "Unknown"
                    
                    # ============ LEVEL INFORMATION ============
                    try:
                        if hasattr(element, 'LevelId') and element.LevelId:
                            level = doc.GetElement(element.LevelId)
                            if level:
                                floor_info["level_name"] = normalize_string(get_element_name(level))
                                floor_info["level_id"] = str(element.LevelId.IntegerValue)
                                floor_info["level_elevation"] = round(level.Elevation * 304.8, 2)  # Convert to mm
                            else:
                                floor_info["level_name"] = "Unknown"
                                floor_info["level_id"] = "Unknown"
                                floor_info["level_elevation"] = 0
                        else:
                            floor_info["level_name"] = "None"
                            floor_info["level_id"] = "None"
                            floor_info["level_elevation"] = 0
                    except:
                        floor_info["level_name"] = "Unknown"
                        floor_info["level_id"] = "Unknown"
                        floor_info["level_elevation"] = 0
                    
                    # ============ HEIGHT OFFSET ============
                    try:
                        height_offset_param = element.LookupParameter("Height Offset From Level")
                        if height_offset_param and height_offset_param.HasValue:
                            floor_info["height_offset"] = round(height_offset_param.AsDouble() * 304.8, 2)  # Convert to mm
                        else:
                            floor_info["height_offset"] = 0
                    except:
                        floor_info["height_offset"] = 0
                    
                    # ============ THICKNESS AND MATERIAL ============
                    try:
                        if hasattr(element, 'FloorType') and element.FloorType:
                            floor_type = element.FloorType
                            
                            # Get compound structure for thickness
                            compound_structure = floor_type.GetCompoundStructure()
                            if compound_structure:
                                total_thickness = compound_structure.GetWidth() * 304.8  # Convert to mm
                                floor_info["thickness"] = round(total_thickness, 2)
                                
                                # Get layer information
                                layers = []
                                for i in range(compound_structure.LayerCount):
                                    layer = compound_structure.GetLayers()[i]
                                    layer_thickness = layer.Width * 304.8  # Convert to mm
                                    
                                    # Get material
                                    material_id = layer.MaterialId
                                    material_name = "Unknown"
                                    if material_id and material_id.IntegerValue != -1:
                                        material = doc.GetElement(material_id)
                                        if material:
                                            material_name = normalize_string(material.Name)
                                    
                                    layers.append({
                                        "thickness": round(layer_thickness, 2),
                                        "material": material_name,
                                        "function": str(layer.Function).split(".")[-1]
                                    })
                                
                                floor_info["layers"] = layers
                            else:
                                floor_info["thickness"] = 0
                                floor_info["layers"] = []
                        else:
                            floor_info["thickness"] = 0
                            floor_info["layers"] = []
                    except Exception as e:
                        floor_info["thickness"] = 0
                        floor_info["layers"] = []
                        logger.warning("Could not get floor thickness: {}".format(str(e)))
                    
                    # ============ BOUNDARY CURVES ============
                    try:
                        boundary_curves = []
                        
                        # Try to get sketch from floor
                        sketch = None
                        if hasattr(element, 'GetSketch'):
                            try:
                                sketch = element.GetSketch()
                            except:
                                pass
                        
                        if sketch and hasattr(sketch, 'Profile'):
                            # Get curves from sketch profile
                            for curve_array in sketch.Profile:
                                for curve in curve_array:
                                    start_pt = curve.GetEndPoint(0)
                                    end_pt = curve.GetEndPoint(1)
                                    
                                    curve_info = {
                                        "type": str(curve.GetType().Name),
                                        "start_point": {
                                            "x": round(start_pt.X * 304.8, 2),
                                            "y": round(start_pt.Y * 304.8, 2),
                                            "z": round(start_pt.Z * 304.8, 2)
                                        },
                                        "end_point": {
                                            "x": round(end_pt.X * 304.8, 2),
                                            "y": round(end_pt.Y * 304.8, 2),
                                            "z": round(end_pt.Z * 304.8, 2)
                                        },
                                        "length": round(curve.Length * 304.8, 2)
                                    }
                                    
                                    # Add arc-specific information
                                    if hasattr(curve, 'Center') and hasattr(curve, 'Radius'):
                                        try:
                                            center = curve.Center
                                            curve_info["center"] = {
                                                "x": round(center.X * 304.8, 2),
                                                "y": round(center.Y * 304.8, 2),
                                                "z": round(center.Z * 304.8, 2)
                                            }
                                            curve_info["radius"] = round(curve.Radius * 304.8, 2)
                                        except:
                                            pass
                                    
                                    boundary_curves.append(curve_info)
                        
                        # If no sketch, try to get from geometry
                        if not boundary_curves:
                            options = DB.Options()
                            geometry = element.get_Geometry(options)
                            
                            for geom_obj in geometry:
                                if isinstance(geom_obj, DB.Solid):
                                    for face in geom_obj.Faces:
                                        if face.Area > 0:
                                            edge_loops = face.EdgeLoops
                                            for edge_loop in edge_loops:
                                                for edge in edge_loop:
                                                    curve = edge.AsCurve()
                                                    start_pt = curve.GetEndPoint(0)
                                                    end_pt = curve.GetEndPoint(1)
                                                    
                                                    curve_info = {
                                                        "type": str(curve.GetType().Name),
                                                        "start_point": {
                                                            "x": round(start_pt.X * 304.8, 2),
                                                            "y": round(start_pt.Y * 304.8, 2),
                                                            "z": round(start_pt.Z * 304.8, 2)
                                                        },
                                                        "end_point": {
                                                            "x": round(end_pt.X * 304.8, 2),
                                                            "y": round(end_pt.Y * 304.8, 2),
                                                            "z": round(end_pt.Z * 304.8, 2)
                                                        },
                                                        "length": round(curve.Length * 304.8, 2)
                                                    }
                                                    boundary_curves.append(curve_info)
                                                break  # Only get first edge loop
                                        break  # Only get first face with area
                                    break  # Only get first solid
                        
                        floor_info["boundary_curves"] = boundary_curves
                        floor_info["boundary_curves_count"] = len(boundary_curves)
                        
                    except Exception as e:
                        floor_info["boundary_curves"] = []
                        floor_info["boundary_curves_count"] = 0
                        logger.warning("Could not get boundary curves: {}".format(str(e)))
                    
                    # ============ ADDITIONAL PARAMETERS ============
                    additional_params = {}
                    param_names = [
                        "Area", "Perimeter", "Volume", "Comments", "Mark", 
                        "Structural", "Room Bounding", "Slope", "Structural Material"
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
                                    # Convert area and volume to metric
                                    if param_name == "Area":
                                        value = round(param.AsDouble() * 0.092903, 2)  # sq ft to sq m
                                    elif param_name == "Volume":
                                        value = round(param.AsDouble() * 0.0283168, 2)  # cu ft to cu m
                                    elif param_name in ["Perimeter", "Slope"]:
                                        value = round(param.AsDouble() * 304.8, 2)  # ft to mm
                                    else:
                                        value = round(param.AsDouble(), 3)
                                elif param.StorageType == DB.StorageType.ElementId:
                                    elem_id_val = param.AsElementId()
                                    if elem_id_val and elem_id_val.IntegerValue != -1:
                                        ref_elem = doc.GetElement(elem_id_val)
                                        value = normalize_string(get_element_name(ref_elem)) if ref_elem else str(elem_id_val.IntegerValue)
                                    else:
                                        value = "None"
                                else:
                                    value = str(param.AsValueString()) if param.AsValueString() else "Unknown"
                                
                                if value and str(value).strip():
                                    additional_params[param_name] = normalize_string(str(value))
                        except:
                            continue
                    
                    floor_info["parameters"] = additional_params
                    
                    # ============ BOUNDING BOX ============
                    try:
                        bbox = element.get_BoundingBox(None)
                        if bbox:
                            floor_info["bounding_box"] = {
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
                            floor_info["bounding_box"] = None
                    except:
                        floor_info["bounding_box"] = None
                    
                    floors_info.append(floor_info)
                    
                except Exception as e:
                    logger.warning("Could not process floor element {}: {}".format(elem_id, str(e)))
                    continue
            
            # Prepare response
            response_data = {
                "message": "Successfully retrieved {} floor elements".format(len(floors_info)),
                "selected_count": len(selected_ids),
                "floors_found": len(floors_info),
                "floors": floors_info
            }
            
            return routes.make_response(data=response_data, status=200)
            
        except Exception as e:
            logger.error("Failed to get floor details: {}".format(str(e)))
            return routes.make_response(
                data={
                    "error": "Failed to retrieve floor details: {}".format(str(e))
                },
                status=500
            )

    logger.info("Model info routes registered successfully")
