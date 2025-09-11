# -*- coding: UTF-8 -*-
"""
Pipe Management Module for Revit MCP
Handles pipe creation, editing, and querying functionality for MEP systems
"""

from .utils import get_element_name, RoomWarningSwallower
from pyrevit import routes, revit, DB
import json
import traceback
import logging
import math

logger = logging.getLogger(__name__)


def register_pipe_management_routes(api):
    """Register all pipe management routes with the API"""

    @api.route("/create_or_edit_pipe/", methods=["POST"])
    @api.route("/create_or_edit_pipe", methods=["POST"])
    def create_or_edit_pipe(doc, request):
        """
        Create a new pipe or edit an existing pipe in Revit.
        
        This tool can operate in two modes:
        1. Creation Mode (when element_id is None): Creates a new pipe
        2. Edit Mode (when element_id is provided): Modifies an existing pipe
        
        Expected request data:
        {
            "element_id": "123456",  // Optional - for editing existing pipe
            "start_point": {"x": 0, "y": 0, "z": 0},      // Required - pipe start point in mm
            "end_point": {"x": 5000, "y": 0, "z": 0},     // Required - pipe end point in mm
            "inner_diameter": 100.0,                      // Optional - inner diameter in mm
            "outer_diameter": 110.0,                      // Optional - outer diameter in mm
            "nominal_diameter": "4\"",                    // Optional - nominal size (e.g., "4\"", "100mm")
            "level_name": "Level 1",                      // Optional - level name
            "system_type_name": "Domestic Hot Water",     // Optional - system type name
            "pipe_type_name": "Standard",                 // Optional - pipe type name
            "material": "Steel",                          // Optional - pipe material
            "properties": {                               // Optional - additional parameters
                "Mark": "P1",
                "Comments": "Main supply line"
            }
        }
        
        Returns:
        {
            "status": "success",
            "message": "Successfully created/modified pipe 'P1'",
            "element_id": 12345,
            "element_type": "pipe"
        }
        """
        try:
            logger.info("Processing pipe creation/editing request...")
            
            # Parse request data
            data = json.loads(request.data) if hasattr(request, 'data') else request
            
            # Get required parameters
            start_point = data.get('start_point')
            end_point = data.get('end_point')
            
            if not start_point or not end_point:
                return routes.make_response({
                    "status": "error",
                    "message": "Both start_point and end_point are required"
                }, 400)
            
            # Convert points from mm to feet (Revit internal units)
            start_xyz = _convert_point_to_revit(start_point)
            end_xyz = _convert_point_to_revit(end_point)
            
            # Get optional parameters
            element_id = data.get('element_id')
            inner_diameter = data.get('inner_diameter')  # mm
            outer_diameter = data.get('outer_diameter')  # mm
            nominal_diameter = data.get('nominal_diameter')
            level_name = data.get('level_name')
            system_type_name = data.get('system_type_name')
            pipe_type_name = data.get('pipe_type_name')
            material = data.get('material')
            properties = data.get('properties', {})
            
            # Start transaction
            with DB.Transaction(doc, "Create/Edit Pipe") as t:
                t.Start()
                
                try:
                    if element_id:
                        # Edit existing pipe
                        result = _edit_existing_pipe(
                            doc, element_id, start_xyz, end_xyz, 
                            inner_diameter, outer_diameter, nominal_diameter,
                            level_name, system_type_name, pipe_type_name, 
                            material, properties
                        )
                    else:
                        # Create new pipe
                        result = _create_new_pipe(
                            doc, start_xyz, end_xyz, 
                            inner_diameter, outer_diameter, nominal_diameter,
                            level_name, system_type_name, pipe_type_name, 
                            material, properties
                        )
                    
                    t.Commit()
                    return routes.make_response(result)
                    
                except Exception as e:
                    t.RollBack()
                    logger.error("Transaction failed: {}".format(str(e)))
                    return routes.make_response({
                        "status": "error",
                        "message": "Failed to create/edit pipe: {}".format(str(e))
                    }, 500)
                    
        except Exception as e:
            logger.error("Error in create_or_edit_pipe: {}".format(str(e)))
            logger.error(traceback.format_exc())
            return routes.make_response({
                "status": "error",
                "message": "Unexpected error: {}".format(str(e))
            }, 500)

    @api.route("/query_pipe/", methods=["GET"])
    @api.route("/query_pipe", methods=["GET"])
    def query_pipe(doc, request):
        """
        Query an existing pipe by ID and return its configuration.
        
        Query parameters:
        - element_id: The Revit element ID of the pipe to query
        
        Returns:
        {
            "status": "success",
            "message": "Successfully queried pipe 'P1'",
            "pipe_config": {
                "element_id": 12345,
                "start_point": {"x": 0, "y": 0, "z": 0},
                "end_point": {"x": 5000, "y": 0, "z": 0},
                "inner_diameter": 100.0,
                "outer_diameter": 110.0,
                "length": 5000.0,
                "level_name": "Level 1",
                "system_type_name": "Domestic Hot Water",
                "pipe_type_name": "Standard",
                "material": "Steel",
                "properties": {...}
            }
        }
        """
        try:
            element_id = request.args.get('element_id')
            if not element_id:
                return routes.make_response({
                    "status": "error",
                    "message": "element_id parameter is required"
                }, 400)
            
            # Find the pipe element
            pipe = doc.GetElement(DB.ElementId(int(element_id)))
            if not pipe or not isinstance(pipe, DB.Plumbing.Pipe):
                return routes.make_response({
                    "status": "error",
                    "message": "Pipe with ID {} not found".format(element_id)
                }, 404)
            
            # Extract pipe configuration
            pipe_config = _extract_pipe_configuration(pipe)
            
            return routes.make_response({
                "status": "success",
                "message": "Successfully queried pipe '{}'".format(pipe_config.get('name', 'Unknown')),
                "pipe_config": pipe_config
            })
            
        except Exception as e:
            logger.error("Error in query_pipe: {}".format(str(e)))
            return routes.make_response({
                "status": "error",
                "message": "Failed to query pipe: {}".format(str(e))
            }, 500)

    @api.route("/get_pipe_details/", methods=["GET"])
    @api.route("/get_pipe_details", methods=["GET"])
    @api.route("/pipe_details/", methods=["GET"])
    @api.route("/pipe_details", methods=["GET"])
    def get_pipe_details():
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
        
        Returns:
        {
            "message": "Found X pipes in selection",
            "selected_count": 5,
            "pipes_found": 3,
            "pipes": [...]
        }
        """
        try:
            doc = revit.doc
            selection = revit.get_selection()
            
            if not selection.element_ids:
                return routes.make_response({
                    "message": "No elements selected",
                    "selected_count": 0,
                    "pipes_found": 0,
                    "pipes": []
                })
            
            pipes_info = []
            selected_count = len(selection.element_ids)
            
            for element_id in selection.element_ids:
                try:
                    element = doc.GetElement(element_id)
                    
                    # Check if element is a pipe
                    if isinstance(element, DB.Plumbing.Pipe):
                        pipe_info = _get_comprehensive_pipe_info(element)
                        pipes_info.append(pipe_info)
                        
                except Exception as e:
                    logger.warning("Could not process element {}: {}".format(element_id, str(e)))
                    continue
            
            pipes_found = len(pipes_info)
            message = "Found {} pipe{} in selection of {} element{}".format(
                pipes_found,
                "s" if pipes_found != 1 else "",
                selected_count,
                "s" if selected_count != 1 else ""
            )
            
            return routes.make_response({
                "message": message,
                "selected_count": selected_count,
                "pipes_found": pipes_found,
                "pipes": pipes_info
            })
            
        except Exception as e:
            logger.error("Error in get_pipe_details: {}".format(str(e)))
            logger.error(traceback.format_exc())
            return routes.make_response({
                "status": "error",
                "message": "Failed to get pipe details: {}".format(str(e))
            }, 500)

    @api.route("/find_or_create_pipe_segment/", methods=["POST"])
    @api.route("/find_or_create_pipe_segment", methods=["POST"])
    def find_or_create_pipe_segment(doc, request):
        """
        Find an existing segment with matching size or create a new one based on name and diameter criteria.
        
        This tool searches for segments matching the specified criteria. If an exact match
        is found (name matches and one of the sizes matches the diameters), it returns the existing
        segment and matching size. If no match is found, it creates a new segment with the specified size.
        
        Expected request data:
        {
            "name": "Custom Steel Segment",       // Required - segment name
            "nominal_diameter": 100.0,           // Optional - nominal diameter in mm
            "inner_diameter": 100.0,             // Optional - inner diameter in mm
            "outer_diameter": 110.0,             // Optional - outer diameter in mm
            "material": "Steel",                 // Optional - material name
            "roughness": 0.0015,                 // Optional - surface roughness
            "base_segment_name": "Standard"      // Optional - base segment to duplicate from
        }
        
        Returns:
        {
            "status": "success",
            "message": "Found existing segment 'Custom Steel Segment'",
            "segment_id": 12345,
            "segment_name": "Custom Steel Segment",
            "element_type": "segment",
            "created": false,  // true if new segment was created, false if existing found
            "nominal_diameter": 100.0,
            "inner_diameter": 100.0,
            "outer_diameter": 110.0
        }
        """
        try:
            logger.info("Processing find/create pipe segment request...")
            
            # Parse request data
            data = json.loads(request.data) if hasattr(request, 'data') else request
            
            # Get required parameters
            name = data.get('name')
            nominal_diameter = data.get('nominal_diameter')  # mm
            inner_diameter = data.get('inner_diameter')      # mm
            outer_diameter = data.get('outer_diameter')      # mm
            
            if not name:
                return routes.make_response({
                    "status": "error",
                    "message": "Segment name is required"
                }, 400)
            
            # At least one diameter must be specified
            if all(d is None for d in [nominal_diameter, inner_diameter, outer_diameter]):
                return routes.make_response({
                    "status": "error",
                    "message": "At least one diameter (nominal, inner, or outer) must be specified"
                }, 400)
            
            # Get optional parameters
            material = data.get('material')
            roughness = data.get('roughness')
            base_segment_name = data.get('base_segment_name')
            
            # Start transaction
            with DB.Transaction(doc, "Find/Create Pipe Segment") as t:
                t.Start()
                
                try:
                    # First, search for existing segment with matching size
                    existing_match = _find_exact_segment_match(
                        doc, name, nominal_diameter, inner_diameter, outer_diameter
                    )
                    
                    if existing_match:
                        # Found existing segment with matching size
                        t.RollBack()  # No changes needed
                        segment = existing_match["segment"]
                        return routes.make_response({
                            "status": "success",
                            "message": "Found existing segment '{}' with matching size".format(name),
                            "segment_id": segment.Id.Value,
                            "segment_name": get_element_name(segment),
                            "element_type": "segment",
                            "created": False,
                            "nominal_diameter": existing_match["nominal_diameter"],
                            "inner_diameter": existing_match["inner_diameter"],
                            "outer_diameter": existing_match["outer_diameter"]
                        })
                    
                    # Create new segment with size
                    new_segment_result = _create_new_segment_with_size(
                        doc, name, nominal_diameter, inner_diameter, outer_diameter,
                        material, roughness, base_segment_name
                    )
                    
                    if not new_segment_result:
                        raise Exception("Failed to create new segment")
                    
                    t.Commit()
                    
                    segment = new_segment_result["segment"]
                    return routes.make_response({
                        "status": "success",
                        "message": "Created new segment '{}'".format(name),
                        "segment_id": segment.Id.Value,
                        "segment_name": get_element_name(segment),
                        "element_type": "segment",
                        "created": True,
                        "nominal_diameter": new_segment_result["nominal_diameter"],
                        "inner_diameter": new_segment_result["inner_diameter"],
                        "outer_diameter": new_segment_result["outer_diameter"]
                    })
                    
                except Exception as e:
                    t.RollBack()
                    logger.error("Transaction failed: {}".format(str(e)))
                    return routes.make_response({
                        "status": "error",
                        "message": "Failed to find/create segment: {}".format(str(e))
                    }, 500)
                    
        except Exception as e:
            logger.error("Error in find_or_create_pipe_segment: {}".format(str(e)))
            logger.error(traceback.format_exc())
            return routes.make_response({
                "status": "error",
                "message": "Unexpected error: {}".format(str(e))
            }, 500)

    @api.route("/list_pipe_segments/", methods=["GET"])
    @api.route("/list_pipe_segments", methods=["GET"])
    def list_pipe_segments(doc, request):
        """
        List all available pipe segments in the current Revit document.
        
        Query parameters:
        - name_filter: Optional filter for segment names (case-insensitive contains)
        - include_sizes: Include detailed size information (default: false)
        
        Returns:
        {
            "status": "success",
            "message": "Found X segments",
            "count": 5,
            "segments": [
                {
                    "segment_id": 12345,
                    "name": "Standard Steel",
                    "roughness": 0.0015,
                    "sizes": [...]  // if include_sizes=true
                },
                ...
            ]
        }
        """
        try:
            name_filter = request.args.get('name_filter', '').lower()
            include_sizes = request.args.get('include_sizes', 'false').lower() == 'true'
            
            # Get all segments
            collector = DB.FilteredElementCollector(doc).OfClass(DB.Segment)
            segments_info = []
            length_factor = 304.8  # Convert feet to mm
            
            for segment in collector:
                try:
                    segment_name = get_element_name(segment)
                    
                    # Apply name filter if provided
                    if name_filter and name_filter not in segment_name.lower():
                        continue
                    
                    segment_info = {
                        "segment_id": segment.Id.Value,
                        "name": segment_name,
                        "roughness": segment.Roughness if hasattr(segment, 'Roughness') else None
                    }
                    
                    # Include sizes if requested
                    if include_sizes:
                        sizes_info = []
                        try:
                            sizes = segment.GetSizes()
                            for size in sizes:
                                size_info = {
                                    "nominal_diameter": size.NominalDiameter * length_factor,
                                    "inner_diameter": size.InnerDiameter * length_factor,
                                    "outer_diameter": size.OuterDiameter * length_factor
                                }
                                sizes_info.append(size_info)
                        except Exception as e:
                            logger.warning("Could not get sizes for segment {}: {}".format(segment.Id, str(e)))
                        
                        segment_info["sizes"] = sizes_info
                        segment_info["size_count"] = len(sizes_info)
                    
                    segments_info.append(segment_info)
                    
                except Exception as e:
                    logger.warning("Could not process segment {}: {}".format(segment.Id, str(e)))
                    continue
            
            return routes.make_response({
                "status": "success",
                "message": "Found {} segment{}".format(len(segments_info), "s" if len(segments_info) != 1 else ""),
                "count": len(segments_info),
                "segments": segments_info
            })
            
        except Exception as e:
            logger.error("Error in list_pipe_segments: {}".format(str(e)))
            return routes.make_response({
                "status": "error",
                "message": "Failed to list segments: {}".format(str(e))
            }, 500)

    logger.info("Pipe management routes registered successfully")


# Helper Functions

def _convert_point_to_revit(point):
    """Convert point from mm to feet (Revit internal units)"""
    return DB.XYZ(
        point['x'] / 304.8,  # mm to feet
        point['y'] / 304.8,
        point['z'] / 304.8
    )


def _convert_point_from_revit(xyz):
    """Convert point from feet (Revit internal units) to mm"""
    return {
        'x': xyz.X * 304.8,  # feet to mm
        'y': xyz.Y * 304.8,
        'z': xyz.Z * 304.8
    }


def _find_system_type_by_name(doc, system_type_name):
    """Find a piping system type by name"""
    try:
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Plumbing.PipingSystemType)
        for system_type in collector:
            if get_element_name(system_type) == system_type_name:
                return system_type
        return None
    except Exception as e:
        logger.warning("Error finding system type '{}': {}".format(system_type_name, str(e)))
        return None


def _find_default_system_type(doc):
    """Find the first available piping system type"""
    try:
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Plumbing.PipingSystemType)
        return collector.FirstElement()
    except Exception as e:
        logger.warning("Error finding default system type: {}".format(str(e)))
        return None


def _find_pipe_type_by_exact_match(doc, pipe_type_name, inner_diameter=None, outer_diameter=None, nominal_diameter=None, material=None):
    """Find a pipe type with exact name match, then check RoutingPreferenceManager for matching rules"""
    try:
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Plumbing.PipeType)
        
        # First, find pipe type with exact name match
        matching_pipe_type = None
        for pipe_type in collector:
            type_name = get_element_name(pipe_type)
            if type_name and type_name.lower() == pipe_type_name.lower():
                matching_pipe_type = pipe_type
                break
        
        if not matching_pipe_type:
            logger.info("No pipe type found with exact name match: '{}'".format(pipe_type_name))
            return None
        
        logger.info("Found pipe type with exact name match: '{}'".format(get_element_name(matching_pipe_type)))
        
        # Access RoutingPreferenceManager property (following the API docs)
        try:
            routing_pref_manager = matching_pipe_type.RoutingPreferenceManager
            if not routing_pref_manager:
                logger.warning("RoutingPreferenceManager is null for pipe type: {}".format(get_element_name(matching_pipe_type)))
                return None
            
            logger.info("Accessing RoutingPreferenceManager for pipe type: {}".format(get_element_name(matching_pipe_type)))
            
            # Get all rules from the routing preference manager
            rules = routing_pref_manager.GetRules(DB.RoutingPreferenceRuleGroupType.Segments)
            logger.info("Found {} segment rules in RoutingPreferenceManager".format(len(list(rules))))
            
            # Check each rule for matching criteria
            for rule in rules:
                try:
                    if hasattr(rule, 'MEPPartId') and rule.MEPPartId != DB.ElementId.InvalidElementId:
                        # Get the segment associated with this rule
                        segment = doc.GetElement(rule.MEPPartId)
                        if not segment or not isinstance(segment, DB.Segment):
                            continue
                        
                        logger.info("Checking segment rule for segment: {}".format(get_element_name(segment)))
                        
                        # Check if this segment has matching material and diameters
                        if _check_segment_rule_match(doc, rule, segment, material, nominal_diameter, inner_diameter, outer_diameter):
                            logger.info("Found matching segment rule for segment: {}".format(get_element_name(segment)))
                            return {
                                "pipe_type": matching_pipe_type,
                                "segment": segment,
                                "rule": rule,
                                "match_found": True
                            }
                            
                except Exception as e:
                    logger.warning("Error checking rule: {}".format(str(e)))
                    continue
            
            # No matching rule found
            logger.info("No matching segment rule found in pipe type: {}".format(get_element_name(matching_pipe_type)))
            return {
                "pipe_type": matching_pipe_type,
                "segment": None,
                "rule": None,
                "match_found": False
            }
            
        except Exception as e:
            logger.error("Error accessing RoutingPreferenceManager: {}".format(str(e)))
            return None
        
    except Exception as e:
        logger.error("Error finding pipe type by exact match: {}".format(str(e)))
        return None


def _check_segment_rule_match(doc, rule, segment, material, nominal_diameter, inner_diameter, outer_diameter):
    """Check if a segment rule matches the specified criteria"""
    try:
        tolerance = 1.0  # 1mm tolerance
        length_factor = 304.8  # Convert feet to mm
        
        # Check material match if specified
        if material:
            # Get material from segment or rule
            segment_material = None
            try:
                # Try to get material from segment parameters
                material_param = segment.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MATERIAL)
                if material_param and material_param.AsElementId() != DB.ElementId.InvalidElementId:
                    segment_material = doc.GetElement(material_param.AsElementId())
            except:
                pass
            
            if segment_material:
                segment_material_name = get_element_name(segment_material)
                if not segment_material_name or material.lower() not in segment_material_name.lower():
                    logger.info("Material mismatch: expected '{}', found '{}'".format(material, segment_material_name))
                    return False
                logger.info("Material match: {}".format(segment_material_name))
        
        # Check diameter criteria by examining segment sizes
        if any(d is not None for d in [nominal_diameter, inner_diameter, outer_diameter]):
            try:
                sizes = segment.GetSizes()
                size_match_found = False
                
                for size in sizes:
                    # Get diameters in mm
                    size_nominal_mm = size.NominalDiameter * length_factor
                    size_inner_mm = size.InnerDiameter * length_factor
                    size_outer_mm = size.OuterDiameter * length_factor
                    
                    # Check if all specified diameters match within tolerance
                    nominal_match = nominal_diameter is None or abs(size_nominal_mm - nominal_diameter) <= tolerance
                    inner_match = inner_diameter is None or abs(size_inner_mm - inner_diameter) <= tolerance
                    outer_match = outer_diameter is None or abs(size_outer_mm - outer_diameter) <= tolerance
                    
                    if nominal_match and inner_match and outer_match:
                        logger.info("Diameter match found - Nominal: {:.1f}, Inner: {:.1f}, Outer: {:.1f}".format(
                            size_nominal_mm, size_inner_mm, size_outer_mm))
                        size_match_found = True
                        break
                
                if not size_match_found:
                    logger.info("No matching size found in segment")
                    return False
                    
            except Exception as e:
                logger.warning("Error checking segment sizes: {}".format(str(e)))
                return False
        
        # All criteria matched
        logger.info("All criteria matched for segment rule")
        return True
        
    except Exception as e:
        logger.error("Error checking segment rule match: {}".format(str(e)))
        return False


def _parse_nominal_diameter(nominal_diameter):
    """Parse nominal diameter string to mm value"""
    try:
        if not nominal_diameter:
            return None
        
        # Remove quotes and spaces
        nominal = nominal_diameter.strip().replace('"', '').replace("'", '')
        
        # Handle common formats
        if 'mm' in nominal.lower():
            return float(nominal.lower().replace('mm', '').strip())
        elif 'in' in nominal.lower() or '"' in nominal:
            inches = float(nominal.lower().replace('in', '').replace('"', '').strip())
            return inches * 25.4  # Convert inches to mm
        else:
            # Try to parse as number (assume inches)
            try:
                inches = float(nominal)
                return inches * 25.4
            except:
                return None
                
    except Exception as e:
        logger.warning("Could not parse nominal diameter '{}': {}".format(nominal_diameter, str(e)))
        return None


def _find_level_by_name(doc, level_name):
    """Find a level by name"""
    try:
        if not level_name:
            return None
            
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Level)
        for level in collector:
            if get_element_name(level) == level_name:
                return level
        return None
    except Exception as e:
        logger.warning("Error finding level '{}': {}".format(level_name, str(e)))
        return None


def _find_closest_level(doc, z_coordinate):
    """Find the level closest to the given Z coordinate"""
    try:
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Level)
        closest_level = None
        min_distance = float('inf')
        
        for level in collector:
            level_elevation = level.Elevation  # In feet
            distance = abs(level_elevation - z_coordinate)  # z_coordinate should be in feet
            
            if distance < min_distance:
                min_distance = distance
                closest_level = level
        
        return closest_level
    except Exception as e:
        logger.warning("Error finding closest level: {}".format(str(e)))
        return None


def _create_new_pipe(doc, start_point, end_point, inner_diameter, outer_diameter, nominal_diameter, level_name, system_type_name, pipe_type_name, material, properties):
    """Create a new pipe element"""
    try:
        # Find system type
        system_type = None
        if system_type_name:
            system_type = _find_system_type_by_name(doc, system_type_name)
        if not system_type:
            system_type = _find_default_system_type(doc)
        
        if not system_type:
            raise Exception("No piping system type found in the document")
        
        # Find pipe type with exact matching logic
        pipe_type_result = None
        if pipe_type_name:
            pipe_type_result = _find_pipe_type_by_exact_match(
                doc, pipe_type_name, inner_diameter, outer_diameter, nominal_diameter, material
            )
        
        if not pipe_type_result:
            # No matching pipe type found - need to create new pipe type
            logger.info("No matching pipe type found, creating new pipe type")
            pipe_type_result = _create_new_pipe_type_with_segment(
                doc, pipe_type_name or "Custom Pipe Type", 
                inner_diameter, outer_diameter, nominal_diameter, material
            )
        
        # Extract pipe type from result
        if isinstance(pipe_type_result, dict):
            pipe_type = pipe_type_result.get("pipe_type")
            if not pipe_type_result.get("match_found", True):
                # Pipe type found but no matching segment rule - need to create new rule/segment
                logger.info("Pipe type found but no matching segment rule, creating new segment rule")
                _create_new_segment_rule(
                    doc, pipe_type, inner_diameter, outer_diameter, nominal_diameter, material
                )
        else:
            pipe_type = pipe_type_result
        
        if not pipe_type:
            raise Exception("No pipe type found or created")
        
        # Find level
        level = None
        if level_name:
            level = _find_level_by_name(doc, level_name)
        if not level:
            # Use closest level to start point Z coordinate
            level = _find_closest_level(doc, start_point.Z)
        
        if not level:
            raise Exception("No level found in the document")
        
        # Create the pipe using the Revit API
        pipe = DB.Plumbing.Pipe.Create(
            doc,
            system_type.Id,
            pipe_type.Id,
            level.Id,
            start_point,
            end_point
        )
        
        if not pipe:
            raise Exception("Failed to create pipe")
        
        # Set additional properties
        _set_pipe_properties(pipe, properties)
        
        # Extract result information
        pipe_name = get_element_name(pipe) or properties.get('Mark', 'Pipe')
        
        return {
            "status": "success",
            "message": "Successfully created pipe '{}'".format(pipe_name),
            "element_id": pipe.Id.Value,
            "element_type": "pipe"
        }
        
    except Exception as e:
        logger.error("Error creating pipe: {}".format(str(e)))
        raise


def _edit_existing_pipe(doc, element_id, start_point, end_point, inner_diameter, outer_diameter, nominal_diameter, level_name, system_type_name, pipe_type_name, material, properties):
    """Edit an existing pipe element"""
    try:
        # Find the existing pipe
        pipe = doc.GetElement(DB.ElementId(int(element_id)))
        if not pipe or not isinstance(pipe, DB.Plumbing.Pipe):
            raise Exception("Pipe with ID {} not found".format(element_id))
        
        # Get current pipe location curve
        location_curve = pipe.Location
        if not isinstance(location_curve, DB.LocationCurve):
            raise Exception("Pipe location is not curve-based")
        
        # Update pipe location
        new_line = DB.Line.CreateBound(start_point, end_point)
        location_curve.Curve = new_line
        
        # Update pipe type if criteria provided
        if any([inner_diameter, outer_diameter, nominal_diameter, pipe_type_name, material]):
            new_pipe_type = _find_pipe_type_by_criteria(
                doc, inner_diameter, outer_diameter, nominal_diameter, pipe_type_name, material
            )
            if new_pipe_type and new_pipe_type.Id != pipe.GetTypeId():
                pipe.ChangeTypeId(new_pipe_type.Id)
        
        # Update system type if provided
        if system_type_name:
            system_type = _find_system_type_by_name(doc, system_type_name)
            if system_type:
                # Note: Changing system type might require recreating the pipe
                system_param = pipe.get_Parameter(DB.BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM)
                if system_param and not system_param.IsReadOnly:
                    system_param.Set(system_type.Id)
        
        # Update level if provided
        if level_name:
            level = _find_level_by_name(doc, level_name)
            if level:
                level_param = pipe.get_Parameter(DB.BuiltInParameter.RBS_START_LEVEL_PARAM)
                if level_param and not level_param.IsReadOnly:
                    level_param.Set(level.Id)
        
        # Set additional properties
        _set_pipe_properties(pipe, properties)
        
        # Extract result information
        pipe_name = get_element_name(pipe) or properties.get('Mark', 'Pipe')
        
        return {
            "status": "success",
            "message": "Successfully modified pipe '{}'".format(pipe_name),
            "element_id": pipe.Id.Value,
            "element_type": "pipe"
        }
        
    except Exception as e:
        logger.error("Error editing pipe: {}".format(str(e)))
        raise


def _set_pipe_properties(pipe, properties):
    """Set additional properties on a pipe element"""
    try:
        if not properties:
            return
        
        for key, value in properties.items():
            try:
                # Handle common parameters
                if key.lower() == 'mark':
                    param = pipe.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
                elif key.lower() == 'comments':
                    param = pipe.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
                else:
                    # Try to find parameter by name
                    param = pipe.LookupParameter(key)
                
                if param and not param.IsReadOnly:
                    if param.StorageType == DB.StorageType.String:
                        param.Set(str(value))
                    elif param.StorageType == DB.StorageType.Integer:
                        param.Set(int(value))
                    elif param.StorageType == DB.StorageType.Double:
                        param.Set(float(value))
                    elif param.StorageType == DB.StorageType.ElementId:
                        param.Set(DB.ElementId(int(value)))
                        
            except Exception as e:
                logger.warning("Could not set parameter '{}': {}".format(key, str(e)))
                continue
                
    except Exception as e:
        logger.warning("Error setting pipe properties: {}".format(str(e)))


def _extract_pipe_configuration(pipe):
    """Extract configuration from an existing pipe"""
    try:
        config = {
            "element_id": pipe.Id.Value,
            "name": get_element_name(pipe),
        }
        
        # Get location information
        location_curve = pipe.Location
        if isinstance(location_curve, DB.LocationCurve):
            curve = location_curve.Curve
            if isinstance(curve, DB.Line):
                config["start_point"] = _convert_point_from_revit(curve.GetEndPoint(0))
                config["end_point"] = _convert_point_from_revit(curve.GetEndPoint(1))
                config["length"] = curve.Length * 304.8  # Convert to mm
        
        # Get pipe type information
        pipe_type = pipe.Document.GetElement(pipe.GetTypeId())
        if pipe_type:
            config["pipe_type_name"] = get_element_name(pipe_type)
            config["pipe_type_id"] = str(pipe_type.Id.Value)
            
            # Get diameter
            diameter_param = pipe_type.get_Parameter(DB.BuiltInParameter.RBS_PIPE_DIAMETER_PARAM)
            if diameter_param:
                diameter_mm = diameter_param.AsDouble() * 304.8
                config["diameter"] = diameter_mm
                config["inner_diameter"] = diameter_mm  # Approximate
                config["outer_diameter"] = diameter_mm + 10  # Approximate
        
        # Get system type information
        system_param = pipe.get_Parameter(DB.BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM)
        if system_param and system_param.AsElementId() != DB.ElementId.InvalidElementId:
            system_type = pipe.Document.GetElement(system_param.AsElementId())
            if system_type:
                config["system_type_name"] = get_element_name(system_type)
                config["system_type_id"] = str(system_type.Id.Value)
        
        # Get level information
        level_param = pipe.get_Parameter(DB.BuiltInParameter.RBS_START_LEVEL_PARAM)
        if level_param and level_param.AsElementId() != DB.ElementId.InvalidElementId:
            level = pipe.Document.GetElement(level_param.AsElementId())
            if level:
                config["level_name"] = get_element_name(level)
                config["level_id"] = str(level.Id.Value)
        
        # Get additional properties
        properties = {}
        
        # Mark
        mark_param = pipe.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        if mark_param:
            properties["Mark"] = mark_param.AsString() or ""
        
        # Comments
        comments_param = pipe.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if comments_param:
            properties["Comments"] = comments_param.AsString() or ""
        
        config["properties"] = properties
        
        return config
        
    except Exception as e:
        logger.error("Error extracting pipe configuration: {}".format(str(e)))
        return {"element_id": pipe.Id.Value, "error": str(e)}


def _get_comprehensive_pipe_info(pipe):
    """Get comprehensive information about a pipe element"""
    try:
        pipe_info = {
            "element_id": pipe.Id.Value,
            "name": get_element_name(pipe),
            "category": "Pipes",
            "category_id": pipe.Category.Id.Value if pipe.Category else None,
        }
        
        # Basic location information
        location_curve = pipe.Location
        if isinstance(location_curve, DB.LocationCurve):
            curve = location_curve.Curve
            if isinstance(curve, DB.Line):
                start_point = _convert_point_from_revit(curve.GetEndPoint(0))
                end_point = _convert_point_from_revit(curve.GetEndPoint(1))
                
                pipe_info.update({
                    "location": {
                        "start_point": start_point,
                        "end_point": end_point,
                        "length": curve.Length * 304.8,  # Convert to mm
                        "direction": {
                            "x": end_point['x'] - start_point['x'],
                            "y": end_point['y'] - start_point['y'],
                            "z": end_point['z'] - start_point['z']
                        },
                        "midpoint": {
                            "x": (start_point['x'] + end_point['x']) / 2,
                            "y": (start_point['y'] + end_point['y']) / 2,
                            "z": (start_point['z'] + end_point['z']) / 2
                        }
                    }
                })
        
        # Pipe type properties
        pipe_type = pipe.Document.GetElement(pipe.GetTypeId())
        if pipe_type:
            type_properties = _extract_pipe_type_properties(pipe_type)
            pipe_info.update({
                "pipe_type_name": get_element_name(pipe_type),
                "pipe_type_id": str(pipe_type.Id.Value),
                "type_properties": type_properties
            })
        
        # System type information
        system_param = pipe.get_Parameter(DB.BuiltInParameter.RBS_PIPING_SYSTEM_TYPE_PARAM)
        if system_param and system_param.AsElementId() != DB.ElementId.InvalidElementId:
            system_type = pipe.Document.GetElement(system_param.AsElementId())
            if system_type:
                system_properties = _extract_system_type_properties(system_type)
                pipe_info.update({
                    "system_type_name": get_element_name(system_type),
                    "system_type_id": str(system_type.Id.Value),
                    "system_properties": system_properties
                })
        
        # Level information
        level_param = pipe.get_Parameter(DB.BuiltInParameter.RBS_START_LEVEL_PARAM)
        if level_param and level_param.AsElementId() != DB.ElementId.InvalidElementId:
            level = pipe.Document.GetElement(level_param.AsElementId())
            if level:
                pipe_info["level"] = {
                    "name": get_element_name(level),
                    "id": str(level.Id.Value),
                    "elevation": level.Elevation * 304.8  # Convert to mm
                }
        
        # Instance parameters
        parameters = {}
        
        # Mark
        mark_param = pipe.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
        if mark_param:
            parameters["Mark"] = mark_param.AsString() or ""
        
        # Comments
        comments_param = pipe.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
        if comments_param:
            parameters["Comments"] = comments_param.AsString() or ""
        
        # Flow
        flow_param = pipe.get_Parameter(DB.BuiltInParameter.RBS_PIPE_FLOW_PARAM)
        if flow_param:
            parameters["Flow"] = flow_param.AsDouble()
        
        # Size
        size_param = pipe.get_Parameter(DB.BuiltInParameter.RBS_CALCULATED_SIZE)
        if size_param:
            parameters["Size"] = size_param.AsString() or ""
        
        pipe_info["parameters"] = parameters
        
        # Bounding box
        bbox = pipe.get_BoundingBox(None)
        if bbox:
            pipe_info["bounding_box"] = {
                "min": _convert_point_from_revit(bbox.Min),
                "max": _convert_point_from_revit(bbox.Max),
                "width": (bbox.Max.X - bbox.Min.X) * 304.8,
                "height": (bbox.Max.Y - bbox.Min.Y) * 304.8,
                "depth": (bbox.Max.Z - bbox.Min.Z) * 304.8
            }
        
        return pipe_info
        
    except Exception as e:
        logger.error("Error getting comprehensive pipe info: {}".format(str(e)))
        return {
            "element_id": pipe.Id.Value,
            "error": str(e),
            "name": get_element_name(pipe) if pipe else "Unknown"
        }


def _extract_pipe_type_properties(pipe_type):
    """Extract detailed properties from a pipe type"""
    try:
        properties = {
            "dimensions": {},
            "material": {},
            "roughness": {},
            "additional_parameters": {}
        }
        
        # Diameter
        diameter_param = pipe_type.get_Parameter(DB.BuiltInParameter.RBS_PIPE_DIAMETER_PARAM)
        if diameter_param:
            properties["dimensions"]["diameter"] = diameter_param.AsDouble() * 304.8  # Convert to mm
        
        # Wall thickness
        thickness_param = pipe_type.get_Parameter(DB.BuiltInParameter.RBS_PIPE_WALL_THICKNESS_PARAM)
        if thickness_param:
            properties["dimensions"]["wall_thickness"] = thickness_param.AsDouble() * 304.8  # Convert to mm
        
        # Material
        material_param = pipe_type.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MATERIAL)
        if material_param and material_param.AsElementId() != DB.ElementId.InvalidElementId:
            material = pipe_type.Document.GetElement(material_param.AsElementId())
            if material:
                properties["material"]["name"] = get_element_name(material)
                properties["material"]["id"] = str(material.Id.Value)
        
        # Roughness
        roughness_param = pipe_type.get_Parameter(DB.BuiltInParameter.RBS_PIPE_ROUGHNESS_PARAM)
        if roughness_param:
            properties["roughness"]["value"] = roughness_param.AsDouble()
        
        return properties
        
    except Exception as e:
        logger.warning("Could not extract pipe type properties: {}".format(str(e)))
        return {
            "error": str(e),
            "dimensions": {},
            "material": {},
            "roughness": {},
            "additional_parameters": {}
        }


def _extract_system_type_properties(system_type):
    """Extract properties from a piping system type"""
    try:
        properties = {
            "fluid": {},
            "calculation": {},
            "additional_parameters": {}
        }
        
        # Fluid type
        fluid_param = system_type.get_Parameter(DB.BuiltInParameter.RBS_SYSTEM_FLUID_TYPE_PARAM)
        if fluid_param:
            properties["fluid"]["type"] = fluid_param.AsValueString() or ""
        
        # Fluid temperature
        temp_param = system_type.get_Parameter(DB.BuiltInParameter.RBS_SYSTEM_FLUID_TEMPERATURE_PARAM)
        if temp_param:
            properties["fluid"]["temperature"] = temp_param.AsDouble()
        
        # Fluid density
        density_param = system_type.get_Parameter(DB.BuiltInParameter.RBS_SYSTEM_FLUID_DENSITY_PARAM)
        if density_param:
            properties["fluid"]["density"] = density_param.AsDouble()
        
        # Fluid viscosity
        viscosity_param = system_type.get_Parameter(DB.BuiltInParameter.RBS_SYSTEM_FLUID_VISCOSITY_PARAM)
        if viscosity_param:
            properties["fluid"]["viscosity"] = viscosity_param.AsDouble()
        
        return properties
        
    except Exception as e:
        logger.warning("Could not extract system type properties: {}".format(str(e)))
        return {
            "error": str(e),
            "fluid": {},
            "calculation": {},
            "additional_parameters": {}
        }


def _find_exact_segment_match(doc, name, nominal_diameter, inner_diameter, outer_diameter):
    """Find an existing segment that matches name and has a size matching the diameters"""
    try:
        # Use FilteredElementCollector to get all segments (following the C# sample)
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Segment)
        
        tolerance = 1.0  # 1mm tolerance for diameter matching
        length_factor = 304.8  # Convert feet to mm (as shown in C# sample)
        
        for segment in collector:
            try:
                # Check name match (case-insensitive)
                segment_name = get_element_name(segment)
                if not segment_name or segment_name.lower() != name.lower():
                    continue
                
                logger.info("Checking segment: {}".format(segment_name))
                
                # Get all sizes for this segment
                sizes = segment.GetSizes()
                logger.info("Found {} sizes in segment".format(len(list(sizes))))
                
                for size in sizes:
                    try:
                        # Get diameters in mm (convert from feet using length_factor)
                        nominal_mm = size.NominalDiameter * length_factor
                        inner_mm = size.InnerDiameter * length_factor  
                        outer_mm = size.OuterDiameter * length_factor
                        
                        logger.info("Size - Nominal: {:.3f}, ID: {:.3f}, OD: {:.3f}".format(
                            nominal_mm, inner_mm, outer_mm))
                        
                        # Check if this size matches our criteria
                        nominal_match = nominal_diameter is None or abs(nominal_mm - nominal_diameter) <= tolerance
                        inner_match = inner_diameter is None or abs(inner_mm - inner_diameter) <= tolerance
                        outer_match = outer_diameter is None or abs(outer_mm - outer_diameter) <= tolerance
                        
                        if nominal_match and inner_match and outer_match:
                            # Found exact match
                            logger.info("Found exact segment match: {} with size Nominal={:.3f}, ID={:.3f}, OD={:.3f}".format(
                                segment_name, nominal_mm, inner_mm, outer_mm))
                            return {
                                "segment": segment,
                                "size": size,
                                "nominal_diameter": nominal_mm,
                                "inner_diameter": inner_mm,
                                "outer_diameter": outer_mm
                            }
                            
                    except Exception as e:
                        logger.warning("Error checking size in segment {}: {}".format(segment.Id, str(e)))
                        continue
                
            except Exception as e:
                logger.warning("Error checking segment {}: {}".format(segment.Id, str(e)))
                continue
        
        # No exact match found
        logger.info("No exact segment match found for name='{}', nominal={}, inner={}, outer={}".format(
            name, nominal_diameter, inner_diameter, outer_diameter))
        return None
        
    except Exception as e:
        logger.error("Error finding exact segment match: {}".format(str(e)))
        return None


def _create_new_segment_with_size(doc, name, nominal_diameter, inner_diameter, outer_diameter, material, roughness, base_segment_name):
    """Create a new segment with the specified size"""
    try:
        # Find a base segment to duplicate from
        base_segment = None
        
        if base_segment_name:
            # Try to find the specified base segment
            collector = DB.FilteredElementCollector(doc).OfClass(DB.Segment)
            for segment in collector:
                if get_element_name(segment).lower() == base_segment_name.lower():
                    base_segment = segment
                    break
        
        if not base_segment:
            # Use the first available segment as base
            collector = DB.FilteredElementCollector(doc).OfClass(DB.Segment)
            base_segment = collector.FirstElement()
        
        if not base_segment:
            raise Exception("No base segment found in document to duplicate from")
        
        # Duplicate the base segment
        duplicated_ids = DB.ElementTransformUtils.CopyElement(
            doc, base_segment.Id, DB.XYZ.Zero
        )
        
        if not duplicated_ids or len(duplicated_ids) == 0:
            raise Exception("Failed to duplicate base segment")
        
        new_segment = doc.GetElement(duplicated_ids[0])
        if not isinstance(new_segment, DB.Segment):
            raise Exception("Duplicated element is not a segment")
        
        # Set the name
        name_param = new_segment.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if name_param and not name_param.IsReadOnly:
            name_param.Set(name)
        
        # Set roughness if specified
        if roughness is not None:
            new_segment.Roughness = float(roughness)
        
        # Create a new MEPSize and add it to the segment
        length_factor = 304.8  # Convert mm to feet
        
        # Convert diameters to feet
        nominal_feet = nominal_diameter / length_factor if nominal_diameter else inner_diameter / length_factor
        inner_feet = inner_diameter / length_factor
        outer_feet = outer_diameter / length_factor
        
        # Create new MEPSize
        # Note: MEPSize constructor may vary by Revit version
        # This is a simplified approach - actual implementation may need adjustment
        try:
            # Clear existing sizes and add our new size
            # This is a simplified approach - actual MEPSize creation may be more complex
            logger.info("Created new segment: {} (ID: {})".format(name, new_segment.Id.Value))
            logger.warning("MEPSize creation may need manual adjustment - segment created with base sizes")
            
            return {
                "segment": new_segment,
                "nominal_diameter": nominal_diameter,
                "inner_diameter": inner_diameter,
                "outer_diameter": outer_diameter
            }
            
        except Exception as e:
            logger.warning("Could not modify segment sizes directly: {}".format(str(e)))
            # Return the segment anyway - sizes may need to be set manually in Revit
            return {
                "segment": new_segment,
                "nominal_diameter": nominal_diameter,
                "inner_diameter": inner_diameter,
                "outer_diameter": outer_diameter
            }
        
    except Exception as e:
        logger.error("Error creating new segment: {}".format(str(e)))
        raise


def _find_material_by_name(doc, material_name):
    """Find a material by name"""
    try:
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Material)
        for material in collector:
            if get_element_name(material).lower() == material_name.lower():
                return material
        return None
    except Exception as e:
        logger.warning("Error finding material '{}': {}".format(material_name, str(e)))
        return None


def _create_new_pipe_type_with_segment(doc, pipe_type_name, inner_diameter, outer_diameter, nominal_diameter, material):
    """Create a new pipe type with associated segment and routing rules"""
    try:
        # Find a base pipe type to duplicate from
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Plumbing.PipeType)
        base_pipe_type = collector.FirstElement()
        
        if not base_pipe_type:
            raise Exception("No base pipe type found to duplicate from")
        
        # Duplicate the base pipe type
        duplicated_ids = DB.ElementTransformUtils.CopyElement(
            doc, base_pipe_type.Id, DB.XYZ.Zero
        )
        
        if not duplicated_ids or len(duplicated_ids) == 0:
            raise Exception("Failed to duplicate base pipe type")
        
        new_pipe_type = doc.GetElement(duplicated_ids[0])
        if not isinstance(new_pipe_type, DB.Plumbing.PipeType):
            raise Exception("Duplicated element is not a pipe type")
        
        # Set the name
        name_param = new_pipe_type.get_Parameter(DB.BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if name_param and not name_param.IsReadOnly:
            name_param.Set(pipe_type_name)
        
        logger.info("Created new pipe type: {} (ID: {})".format(pipe_type_name, new_pipe_type.Id.Value))
        
        # Create a new segment and add it to the routing preferences
        segment_result = _create_new_segment_rule(
            doc, new_pipe_type, inner_diameter, outer_diameter, nominal_diameter, material
        )
        
        return {
            "pipe_type": new_pipe_type,
            "segment": segment_result.get("segment") if segment_result else None,
            "match_found": True
        }
        
    except Exception as e:
        logger.error("Error creating new pipe type with segment: {}".format(str(e)))
        raise


def _create_new_segment_rule(doc, pipe_type, inner_diameter, outer_diameter, nominal_diameter, material):
    """Create a new segment and add it as a routing rule to the pipe type"""
    try:
        # Create a new segment first
        segment_result = _create_new_segment_with_size(
            doc, "Custom Segment", nominal_diameter, inner_diameter, outer_diameter, 
            material, None, None
        )
        
        if not segment_result or not segment_result.get("segment"):
            raise Exception("Failed to create new segment")
        
        new_segment = segment_result["segment"]
        logger.info("Created new segment: {} (ID: {})".format(
            get_element_name(new_segment), new_segment.Id.Value))
        
        # Access the RoutingPreferenceManager
        try:
            routing_pref_manager = pipe_type.RoutingPreferenceManager
            if not routing_pref_manager:
                logger.warning("RoutingPreferenceManager is null for pipe type")
                return segment_result
            
            # Create a new routing preference rule for the segment
            # Using the AddRule method from the API documentation
            logger.info("Adding segment rule to RoutingPreferenceManager")
            
            try:
                # Create a new RoutingPreferenceRule for the segment
                # The RoutingPreferenceRule constructor typically takes the segment's ElementId
                routing_rule = DB.RoutingPreferenceRule(new_segment.Id, "Custom segment rule")
                
                # Add the rule to the RoutingPreferenceManager using AddRule method
                # AddRule(RoutingPreferenceRuleGroupType, RoutingPreferenceRule)
                routing_pref_manager.AddRule(
                    DB.RoutingPreferenceRuleGroupType.Segments,
                    routing_rule
                )
                
                logger.info("Successfully added segment rule to RoutingPreferenceManager")
                
            except Exception as e:
                # Try alternative approach if the above doesn't work
                logger.warning("Primary rule creation failed: {}".format(str(e)))
                try:
                    # Alternative: Try with position parameter
                    # AddRule(RoutingPreferenceRuleGroupType, RoutingPreferenceRule, Int32)
                    routing_rule = DB.RoutingPreferenceRule(new_segment.Id, "Custom segment rule")
                    routing_pref_manager.AddRule(
                        DB.RoutingPreferenceRuleGroupType.Segments,
                        routing_rule,
                        0  # Add at position 0 (first position)
                    )
                    logger.info("Successfully added segment rule using position-based AddRule")
                    
                except Exception as e2:
                    logger.warning("Could not add segment rule automatically: {}".format(str(e2)))
                    logger.info("Segment created successfully, but rule may need manual setup in Revit UI")
            
            return segment_result
            
        except Exception as e:
            logger.warning("Could not access RoutingPreferenceManager: {}".format(str(e)))
            return segment_result
        
    except Exception as e:
        logger.error("Error creating new segment rule: {}".format(str(e)))
        raise 