# -*- coding: UTF-8 -*-
"""
Pipe Management Module for Revit
Handles pipe creation, editing, and querying functionality for MEP systems
"""

from utils import get_element_name, RoomWarningSwallower
from pyrevit import routes, revit, DB
from System import Int64
import json
import traceback
import logging
import math

logger = logging.getLogger(__name__)
swallower = RoomWarningSwallower()

def register_pipe_management_routes(api):
    """Register all pipe management routes with the API"""

    @api.route("/create_or_edit_multiple_pipes/", methods=["POST"])
    @api.route("/create_or_edit_multiple_pipes", methods=["POST"])
    def create_or_edit_multiple_pipes_route(doc, request):
        """
        Create or edit multiple pipes using a list of PipeConfig objects.
        
        This tool allows you to create multiple pipes at once using different layout strategies.
        It's useful for creating pipe runs, distribution systems, or any pattern of multiple pipes.
        
        Expected request data:
        {
            "pipe_configs": [
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
                    }
                },
                // ... more pipe configurations
            ],
            "naming_pattern": "P{}",  // Optional - pattern for auto-naming pipes
            "system_type_name": "Domestic Hot Water",  // Optional - default system type for all pipes
            "pipe_type_name": "Standard"  // Optional - default pipe type for all pipes
        }
        """
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
        pipe_configs_data = data.get("pipe_configs", [])
        naming_pattern = data.get("naming_pattern", "P{}")
        default_system_type = data.get("system_type_name")
        default_pipe_type = data.get("pipe_type_name")

        # Validate pipe_configs
        if not pipe_configs_data or not isinstance(pipe_configs_data, list):
            return routes.make_response(
                data={"error": "pipe_configs must be a non-empty list"}, status=400
            )

        if len(pipe_configs_data) == 0:
            return routes.make_response(
                data={"error": "At least one pipe configuration is required"}, status=400
            )

        logger.info("Creating/editing {} pipes via MCP".format(len(pipe_configs_data)))

        # Convert data to PipeConfig objects
        pipe_configs = []
        for i, config_data in enumerate(pipe_configs_data):
            try:
                # Validate required fields
                if not config_data.get("start_point") or not config_data.get("end_point"):
                    return routes.make_response(
                        data={"error": "Pipe config {}: start_point and end_point are required".format(i)},
                        status=400,
                    )

                # Create PipeConfig object with defaults
                pipe_config = PipeConfig(
                    start_point=config_data.get("start_point"),
                    end_point=config_data.get("end_point"),
                    element_id=config_data.get("element_id"),
                    inner_diameter=config_data.get("inner_diameter"),
                    outer_diameter=config_data.get("outer_diameter"),
                    nominal_diameter=config_data.get("nominal_diameter"),
                    level_name=config_data.get("level_name"),
                    system_type_name=config_data.get("system_type_name") or default_system_type,
                    pipe_type_name=config_data.get("pipe_type_name") or default_pipe_type,
                    material=config_data.get("material"),
                    properties=config_data.get("properties", {})
                )

                # Apply naming pattern if no Mark is provided and no element_id (new pipe)
                if not pipe_config.element_id and "Mark" not in pipe_config.properties:
                    pipe_config.properties["Mark"] = naming_pattern.format(i + 1)

                pipe_configs.append(pipe_config)

            except Exception as config_error:
                return routes.make_response(
                    data={"error": "Invalid pipe config {}: {}".format(i, str(config_error))},
                    status=400,
                )

        
        # Call the existing function to create/edit multiple pipes
        batch_result = create_or_edit_multiple_pipes(doc, pipe_configs)
        
        if not batch_result:
            return routes.make_response(
                data={"error": "Failed to process pipes - no result returned"}, status=500
            )

        # Format the response - ensure all data is JSON serializable
        def make_serializable(obj):
            """Convert PipeConfig objects to dictionaries recursively"""
            if isinstance(obj, PipeConfig):
                return obj.to_dict()
            elif isinstance(obj, list):
                return [make_serializable(item) for item in obj]
            elif isinstance(obj, dict):
                return {key: make_serializable(value) for key, value in obj.items()}
            else:
                return obj
        
        response_data = {
            "message": batch_result.get("message", "Pipe processing completed"),
            "status": batch_result.get("status", "unknown"),
            "total_requested": batch_result.get("total_requested", 0),
            "successful_count": batch_result.get("successful_count", 0),
            "failed_count": batch_result.get("failed_count", 0),
            "results": make_serializable(batch_result.get("results", [])),
            "successful_pipes": batch_result.get("successful_pipes", []),
            "failed_configs": make_serializable(batch_result.get("failed_configs", []))
        }

        # Determine HTTP status based on result
        if batch_result.get("status") == "success":
            http_status = 200
        elif batch_result.get("status") == "partial":
            http_status = 207  # Multi-status
        else:
            http_status = 500

        logger.info("Pipe batch operation completed: {} successful, {} failed".format(
            batch_result.get("successful_count", 0),
            batch_result.get("failed_count", 0)
        ))

        return routes.make_response(data=response_data, status=http_status)


class PipeConfig(object):
    """Configuration object for pipe creation and editing"""
    
    def __init__(self, start_point=None, end_point=None, element_id=None, 
                 inner_diameter=None, outer_diameter=None, nominal_diameter=None,
                 level_name=None, system_type_name=None, pipe_type_name=None, 
                 material=None, properties=None):
        """
        Initialize pipe configuration
        
        Args:
            start_point (dict): Pipe start point in mm {"x": 0, "y": 0, "z": 0}
            end_point (dict): Pipe end point in mm {"x": 5000, "y": 0, "z": 0}
            element_id (str, optional): Element ID of existing pipe to edit
            inner_diameter (float, optional): Inner diameter in mm
            outer_diameter (float, optional): Outer diameter in mm
            nominal_diameter (str, optional): Nominal size (e.g., "4\"", "100mm")
            level_name (str, optional): Level name
            system_type_name (str, optional): System type name
            pipe_type_name (str, optional): Pipe type name
            material (str, optional): Pipe material
            properties (dict, optional): Additional parameters
        """
        self.start_point = start_point 
        self.end_point = end_point 
        self.element_id = element_id
        self.inner_diameter = inner_diameter
        self.outer_diameter = outer_diameter
        self.nominal_diameter = nominal_diameter
        self.level_name = level_name
        self.system_type_name = system_type_name
        self.pipe_type_name = pipe_type_name
        self.material = material
        self.properties = properties or {}
    
    def validate(self):
        """
        Validate pipe configuration
        
        Returns:
            tuple: (is_valid, error_messages)
        """
        errors = []
        
        if not self.start_point:
            errors.append("start_point is required")
        elif not isinstance(self.start_point, dict) or not all(k in self.start_point for k in ['x', 'y', 'z']):
            errors.append("start_point must be a dict with x, y, z keys")
        
        if not self.end_point:
            errors.append("end_point is required")
        elif not isinstance(self.end_point, dict) or not all(k in self.end_point for k in ['x', 'y', 'z']):
            errors.append("end_point must be a dict with x, y, z keys")
        
        # Check that at least one diameter is specified for new pipes
        if not self.element_id and not any([self.inner_diameter, self.outer_diameter, self.nominal_diameter]):
            errors.append("At least one diameter (inner, outer, or nominal) must be specified for new pipes")
        
        return len(errors) == 0, errors
    
    def get_length_mm(self):
        """Calculate pipe length in millimeters"""
        try:
            if not self.start_point or not self.end_point:
                return 0
            
            dx = self.end_point['x'] - self.start_point['x']
            dy = self.end_point['y'] - self.start_point['y']
            dz = self.end_point['z'] - self.start_point['z']
            
            return math.sqrt(dx*dx + dy*dy + dz*dz)
        except:
            return 0
    
    def is_horizontal(self, tolerance=1.0):
        """Check if pipe is horizontal within tolerance (mm)"""
        try:
            if not self.start_point or not self.end_point:
                return False
            
            dz = abs(self.end_point['z'] - self.start_point['z'])
            return dz <= tolerance
        except:
            return False
    
    def is_vertical(self, tolerance=1.0):
        """Check if pipe is vertical within tolerance (mm)"""
        try:
            if not self.start_point or not self.end_point:
                return False
            
            dx = abs(self.end_point['x'] - self.start_point['x'])
            dy = abs(self.end_point['y'] - self.start_point['y'])
            
            return dx <= tolerance and dy <= tolerance
        except:
            return False
    
    def copy(self):
        """Create a copy of this pipe configuration"""
        return PipeConfig(
            start_point=self.start_point.copy() if self.start_point else None,
            end_point=self.end_point.copy() if self.end_point else None,
            element_id=self.element_id,
            inner_diameter=self.inner_diameter,
            outer_diameter=self.outer_diameter,
            nominal_diameter=self.nominal_diameter,
            level_name=self.level_name,
            system_type_name=self.system_type_name,
            pipe_type_name=self.pipe_type_name,
            material=self.material,
            properties=self.properties.copy() if self.properties else {}
        )
    
    def to_dict(self):
        """Convert PipeConfig to a JSON-serializable dictionary"""
        return {
            "start_point": self.start_point,
            "end_point": self.end_point,
            "element_id": self.element_id,
            "inner_diameter": self.inner_diameter,
            "outer_diameter": self.outer_diameter,
            "nominal_diameter": self.nominal_diameter,
            "level_name": self.level_name,
            "system_type_name": self.system_type_name,
            "pipe_type_name": self.pipe_type_name,
            "material": self.material,
            "properties": self.properties
        }
    
    def __str__(self):
        return "PipeConfig(start={}, end={}, length={:.1f}mm, material={})".format(
            self.start_point, self.end_point, self.get_length_mm(), self.material or "Unknown"
        )


def create_or_edit_pipe_from_config(doc, pipe_config, transaction=None):
    """
    Create or edit a pipe using a PipeConfig object
    
    Args:
        doc: Revit document
        pipe_config (PipeConfig): Pipe configuration object
        transaction (Transaction, optional): Existing transaction to use. If None, creates its own transaction.
    
    Returns:
        dict: {
            "status": "success",
            "message": "Successfully created/modified pipe 'P1'",
            "element_id": 12345,
            "element_type": "pipe"
        }
    
    Raises:
        ValueError: If pipe_config is invalid
        Exception: If pipe creation/editing fails
    """
    try:
        if not isinstance(pipe_config, PipeConfig):
            raise ValueError("pipe_config must be a PipeConfig object")
        
        # Validate the configuration
        is_valid, errors = pipe_config.validate()
        if not is_valid:
            raise ValueError("Invalid pipe configuration: {}".format(", ".join(errors)))
        
        # Call the original function with unpacked parameters
        return create_or_edit_pipe(
            doc=doc,
            start_point=pipe_config.start_point,
            end_point=pipe_config.end_point,
            element_id=pipe_config.element_id,
            inner_diameter=pipe_config.inner_diameter,
            outer_diameter=pipe_config.outer_diameter,
            nominal_diameter=pipe_config.nominal_diameter,
            level_name=pipe_config.level_name,
            system_type_name=pipe_config.system_type_name,
            pipe_type_name=pipe_config.pipe_type_name,
            material=pipe_config.material,
            properties=pipe_config.properties,
            transaction=transaction
        )
        
    except Exception as e:
        print("Error in create_or_edit_pipe_from_config: {}".format(str(e)))
        raise


def create_or_edit_multiple_pipes(doc, pipe_configs):
    """
    Create or edit multiple pipes using a list of PipeConfig objects
    
    Args:
        doc: Revit document
        pipe_configs (list): List of PipeConfig objects
    
    Returns:
        dict: {
            "status": "success" or "partial" or "failed",
            "message": "Summary message",
            "total_requested": 5,
            "successful_count": 4,
            "failed_count": 1,
            "results": [
                {"status": "success", "element_id": 12345, "config_index": 0},
                {"status": "error", "error": "validation failed", "config_index": 1},
                ...
            ],
            "successful_pipes": [12345, 12346, 12347, 12348],
            "failed_configs": [{"index": 1, "error": "validation failed", "config": PipeConfig(...)}]
        }
    
    Raises:
        ValueError: If pipe_configs is not a list or is empty
        Exception: If critical error occurs during processing
    """
    try:
        # Validate input
        if not isinstance(pipe_configs, list):
            raise ValueError("pipe_configs must be a list of PipeConfig objects")
        
        if not pipe_configs:
            raise ValueError("pipe_configs list cannot be empty")
        
        total_requested = len(pipe_configs)
        
        # Initialize results tracking
        results = []
        successful_pipes = []
        failed_configs = []
        successful_count = 0
        failed_count = 0
        
        # Use a single transaction for all pipes for better performance
        with DB.Transaction(doc, "Create/Edit Multiple Pipes") as batch_transaction:
            batch_transaction.Start()
        
            # Process each pipe configuration
            for index, pipe_config in enumerate(pipe_configs):
                try:
                    # Validate individual config
                    if not isinstance(pipe_config, PipeConfig):
                        error_msg = "Item at index {} is not a PipeConfig object".format(index)
                        print("[ERROR] {}".format(error_msg))
                        results.append({
                            "status": "error",
                            "error": error_msg,
                            "config_index": index,
                            "element_id": None
                        })
                        failed_configs.append({
                            "index": index,
                            "error": error_msg,
                            "config": pipe_config.to_dict() if isinstance(pipe_config, PipeConfig) else pipe_config
                        })
                        failed_count += 1
                        continue
                    
                    # Validate pipe configuration
                    is_valid, errors = pipe_config.validate()
                    if not is_valid:
                        error_msg = "Validation failed: {}".format(", ".join(errors))
                        print("[ERROR] Config {}: {}".format(index, error_msg))
                        results.append({
                            "status": "error",
                            "error": error_msg,
                            "config_index": index,
                            "element_id": pipe_config.element_id
                        })
                        failed_configs.append({
                            "index": index,
                            "error": error_msg,
                            "config": pipe_config.to_dict() if isinstance(pipe_config, PipeConfig) else pipe_config
                        })
                        failed_count += 1
                        continue
                    
                    # Create/edit the pipe using the shared transaction
                    result = create_or_edit_pipe_from_config(doc, pipe_config, batch_transaction)
                    
                    if result and result.get("status") == "success":
                        element_id = result.get("element_id")
                        results.append({
                            "status": "success",
                            "element_id": element_id,
                            "config_index": index,
                            "message": result.get("message", "")
                        })
                        successful_pipes.append(element_id)
                        successful_count += 1
                    else:
                        error_msg = result.get("message", "Unknown error") if result else "No result returned"
                        print("[ERROR] Config {} failed: {}".format(index, error_msg))
                        results.append({
                            "status": "error",
                            "error": error_msg,
                            "config_index": index,
                            "element_id": pipe_config.element_id
                        })
                        failed_configs.append({
                            "index": index,
                            "error": error_msg,
                            "config": pipe_config.to_dict() if isinstance(pipe_config, PipeConfig) else pipe_config
                        })
                        failed_count += 1
                    
                except Exception as e:
                    error_msg = "Exception during processing: {}".format(str(e))
                    print("[ERROR] Config {}: {}".format(index, error_msg))
                    results.append({
                        "status": "error",
                        "error": error_msg,
                        "config_index": index,
                        "element_id": pipe_config.element_id if isinstance(pipe_config, PipeConfig) else None
                    })
                    failed_configs.append({
                        "index": index,
                        "error": error_msg,
                        "config": pipe_config
                    })
                    failed_count += 1
                    continue
            
            # Determine overall status
            if successful_count == total_requested:
                overall_status = "success"
                message = "All {} pipes processed successfully".format(total_requested)
            elif successful_count > 0:
                overall_status = "partial"
                message = "{} of {} pipes processed successfully, {} failed".format(
                    successful_count, total_requested, failed_count)
            else:
                overall_status = "failed"
                message = "All {} pipe processing attempts failed".format(total_requested)
            
            batch_transaction.Commit()
        return {
            "status": overall_status,
            "message": message,
            "total_requested": total_requested,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "results": results,
            "successful_pipes": successful_pipes,
            "failed_configs": failed_configs
        }
        
    except Exception as e:
        print("Error in create_or_edit_multiple_pipes: {}".format(str(e)))
        raise


def create_or_edit_pipe(doc, start_point, end_point, element_id=None, inner_diameter=None, 
                       outer_diameter=None, nominal_diameter=None, level_name=None, 
                       system_type_name=None, pipe_type_name=None, material=None, 
                       properties=None, transaction=None):
    """
    Create a new pipe or edit an existing pipe in Revit.
    
    This function can operate in two modes:
    1. Creation Mode (when element_id is None): Creates a new pipe
    2. Edit Mode (when element_id is provided): Modifies an existing pipe
    
    Args:
        doc: Revit document
        start_point (dict): Pipe start point in mm {"x": 0, "y": 0, "z": 0}
        end_point (dict): Pipe end point in mm {"x": 5000, "y": 0, "z": 0}
        element_id (str, optional): Element ID of existing pipe to edit
        inner_diameter (float, optional): Inner diameter in mm
        outer_diameter (float, optional): Outer diameter in mm
        nominal_diameter (str, optional): Nominal size (e.g., "4\"", "100mm")
        level_name (str, optional): Level name
        system_type_name (str, optional): System type name
        pipe_type_name (str, optional): Pipe type name
        material (str, optional): Pipe material
        properties (dict, optional): Additional parameters {"Mark": "P1", "Comments": "Main supply line"}
        transaction (Transaction, optional): Existing transaction to use. If None, creates its own transaction.
    
    Returns:
        dict: {
            "status": "success",
            "message": "Successfully created/modified pipe 'P1'",
            "element_id": 12345,
            "element_type": "pipe"
        }
    
    Raises:
        ValueError: If required parameters are missing
        Exception: If pipe creation/editing fails
    """
    try:
        # Validate required parameters
        if not start_point or not end_point:
            raise ValueError("Both start_point and end_point are required")
        
        # Convert points from mm to feet (Revit internal units)
        start_xyz = _convert_point_to_revit(start_point)
        end_xyz = _convert_point_to_revit(end_point)
        
        # Set default properties if not provided
        if properties is None:
            properties = {}
        
        # Handle transaction management
        if transaction is not None:
            # Use provided transaction - caller manages it
            if(element_id):
                rvt_element_id = find_pipe_by_mark(doc, element_id) 
            else:
                rvt_element_id = None
                
            if rvt_element_id:
                # Edit existing pipe
                result = _edit_existing_pipe(
                    doc, rvt_element_id, start_xyz, end_xyz, 
                    inner_diameter, outer_diameter, nominal_diameter,
                    level_name, system_type_name, pipe_type_name, 
                    material, properties
                )
            else:
                # Create new pipe
                result = _create_new_pipe(
                    doc, element_id, start_xyz, end_xyz, 
                    inner_diameter, outer_diameter, nominal_diameter,
                    level_name, system_type_name, pipe_type_name, 
                    material, properties
                )
            return result
        else:
            # Create and manage our own transaction
            with DB.Transaction(doc, "Create/Edit Pipe") as t:
                t.Start()
                if(element_id):
                    rvt_element_id = find_pipe_by_mark(doc, element_id) 
                else:
                    rvt_element_id = None
                if rvt_element_id:
                    # Edit existing pipe
                    result = _edit_existing_pipe(
                        doc, rvt_element_id, start_xyz, end_xyz, 
                        inner_diameter, outer_diameter, nominal_diameter,
                        level_name, system_type_name, pipe_type_name, 
                        material, properties
                    )
                else:
                    # Create new pipe
                    result = _create_new_pipe(
                        doc, element_id, start_xyz, end_xyz, 
                        inner_diameter, outer_diameter, nominal_diameter,
                        level_name, system_type_name, pipe_type_name, 
                        material, properties
                    )
                
                t.Commit()
                return result
                
    except Exception as e:
        print("Error in create_or_edit_pipe: {}".format(str(e)))
        print(traceback.format_exc())
        raise


def query_pipe(doc, element_id):
    """
    Query an existing pipe by ID and return its configuration.
    
    Args:
        doc: Revit document
        element_id (str): The Revit element ID of the pipe to query
    
    Returns:
        dict: {
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
    
    Raises:
        ValueError: If element_id is not provided
        Exception: If pipe is not found or query fails
    """
    try:
        if not element_id:
            raise ValueError("element_id parameter is required")
        
        # Find the pipe element
        pipe = doc.GetElement(DB.ElementId(int(element_id)))
        if not pipe or not isinstance(pipe, DB.Plumbing.Pipe):
            raise Exception("Pipe with ID {} not found".format(element_id))
        
        # Extract pipe configuration
        pipe_config = _extract_pipe_configuration(pipe)
        
        return {
            "status": "success",
            "message": "Successfully queried pipe '{}'".format(pipe_config.get('name', 'Unknown')),
            "pipe_config": pipe_config
        }
        
    except Exception as e:
        print("Error in query_pipe: {}".format(str(e)))
        raise


def find_pipe_by_mark(doc, mark_id):
    """
    Find a pipe by its Mark parameter value and return the element ID.
    
    This function searches all pipes in the document and compares their 
    DB.BuiltInParameter.ALL_MODEL_MARK parameter value against the provided string ID.
    Returns the element ID of the first matching pipe found.
    
    Args:
        doc: Revit document
        mark_id (str): The Mark value to search for
    
    Returns:
        int or None: Element ID of the matching pipe, or None if not found
    
    Raises:
        ValueError: If mark_id is not provided
        Exception: If search fails
    """
    try:
        if not mark_id:
            raise ValueError("mark_id parameter is required")
        
        # Get all pipes in the document
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Plumbing.Pipe)
        pipes = collector.WhereElementIsNotElementType().ToElements()
        
        # Search through all pipes
        for pipe in pipes:
            try:
                # Get the Mark parameter
                mark_param = pipe.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
                
                if mark_param:
                    # Get the parameter value as string
                    mark_value = mark_param.AsString()
                    
                    # Compare with the search string (case-sensitive match)
                    if mark_value == mark_id:
                        return str(pipe.Id.Value)
                        
            except Exception as e:
                print("Error checking pipe {}: {}".format(str(pipe.Id.Value), str(e)))
                continue
        
        # No matching pipe found
        return None
        
    except Exception as e:
        print("Error in find_pipe_by_mark: {}".format(str(e)))
        raise


def get_pipe_details(doc=None):
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
    
    Args:
        doc: Revit document (optional, uses revit.doc if not provided)
    
    Returns:
        dict: {
            "message": "Found X pipes in selection",
            "selected_count": 5,
            "pipes_found": 3,
            "pipes": [...]
        }
    
    Raises:
        Exception: If getting pipe details fails
    """
    try:
        if doc is None:
            doc = revit.doc
        selection = revit.get_selection()
        
        if not selection.element_ids:
            return {
                "message": "No elements selected",
                "selected_count": 0,
                "pipes_found": 0,
                "pipes": []
            }
        
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
                print("Could not process element {}: {}".format(element_id, str(e)))
                continue
        
        pipes_found = len(pipes_info)
        message = "Found {} pipe{} in selection of {} element{}".format(
            pipes_found,
            "s" if pipes_found != 1 else "",
            selected_count,
            "s" if selected_count != 1 else ""
        )
        
        return {
            "message": message,
            "selected_count": selected_count,
            "pipes_found": pipes_found,
            "pipes": pipes_info
        }
        
    except Exception as e:
        print("Error in get_pipe_details: {}".format(str(e)))
        print(traceback.format_exc())
        raise


def find_or_create_pipe_segment(doc, name, nominal_diameter=None, inner_diameter=None, 
                               outer_diameter=None, material=None, roughness=None, 
                               base_segment_name=None):
    """
    Find an existing segment with matching size or create a new one based on name and diameter criteria.
    
    This function searches for segments matching the specified criteria. If an exact match
    is found (name matches and one of the sizes matches the diameters), it returns the existing
    segment and matching size. If no match is found, it creates a new segment with the specified size.
    
    Args:
        doc: Revit document
        name (str): Segment name (required)
        nominal_diameter (float, optional): Nominal diameter in mm
        inner_diameter (float, optional): Inner diameter in mm
        outer_diameter (float, optional): Outer diameter in mm
        material (str, optional): Material name
        roughness (float, optional): Surface roughness
        base_segment_name (str, optional): Base segment to duplicate from
    
    Returns:
        dict: {
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
    
    Raises:
        ValueError: If required parameters are missing
        Exception: If segment creation fails
    """
    try:
        # Validate required parameters
        if not name:
            raise ValueError("Segment name is required")
        
        # At least one diameter must be specified
        if all(d is None for d in [nominal_diameter, inner_diameter, outer_diameter]):
            raise ValueError("At least one diameter (nominal, inner, or outer) must be specified")
        
        # Start transaction
        with DB.Transaction(doc, "Find/Create Pipe Segment") as t:
            t.Start()
            
            try:
                # First, search for existing segment with matching size
                existing_match = _find_exact_segment_match(
                    doc, material, nominal_diameter, inner_diameter, outer_diameter, roughness, base_segment_name
                )
                
                if existing_match:
                    # Found existing segment with matching size
                    t.RollBack()  # No changes needed
                    segment = existing_match["segment"]
                    return {
                        "status": "success",
                        "message": "Found existing segment '{}' with matching size".format(name),
                        "segment_id": str(segment.Id.Value),
                        "segment_name": get_element_name(segment),
                        "element_type": "segment",
                        "created": False,
                        "nominal_diameter": existing_match["nominal_diameter"],
                        "inner_diameter": existing_match["inner_diameter"],
                        "outer_diameter": existing_match["outer_diameter"]
                    }
                
                # Create new segment with size
                new_segment_result = _create_new_segment_with_size(
                    doc, material, nominal_diameter, inner_diameter, outer_diameter,
                    roughness, base_segment_name
                )
                
                if not new_segment_result:
                    raise Exception("Failed to create new segment")
                
                t.Commit()
                
                segment = new_segment_result["segment"]
                return {
                    "status": "success",
                    "message": "Created new segment '{}'".format(name),
                    "segment_id": str(segment.Id.Value),
                    "segment_name": get_element_name(segment),
                    "element_type": "segment",
                    "created": True,
                    "nominal_diameter": new_segment_result["nominal_diameter"],
                    "inner_diameter": new_segment_result["inner_diameter"],
                    "outer_diameter": new_segment_result["outer_diameter"]
                }
                
            except Exception as e:
                t.RollBack()
                print("Transaction failed: {}".format(str(e)))
                raise Exception("Failed to find/create segment: {}".format(str(e)))
                
    except Exception as e:
        print("Error in find_or_create_pipe_segment: {}".format(str(e)))
        print(traceback.format_exc())
        raise


def list_pipe_segments(doc, name_filter=None, include_sizes=False):
    """
    List all available pipe segments in the current Revit document.
    
    Args:
        doc: Revit document
        name_filter (str, optional): Filter for segment names (case-insensitive contains)
        include_sizes (bool, optional): Include detailed size information (default: False)
    
    Returns:
        dict: {
            "status": "success",
            "message": "Found X segments",
            "count": 5,
            "segments": [
                {
                    "segment_id": 12345,
                    "name": "Standard Steel",
                    "roughness": 0.0015,
                    "sizes": [...]  // if include_sizes=True
                },
                ...
            ]
        }
    
    Raises:
        Exception: If listing segments fails
    """
    try:
        if name_filter:
            name_filter = name_filter.lower()
        
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
                    "segment_id": str(segment.Id.Value),
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
                        print("Could not get sizes for segment {}: {}".format(segment.Id, str(e)))
                    
                    segment_info["sizes"] = sizes_info
                    segment_info["size_count"] = len(sizes_info)
                
                segments_info.append(segment_info)
                
            except Exception as e:
                print("Could not process segment {}: {}".format(segment.Id, str(e)))
                continue
        
        return {
            "status": "success",
            "message": "Found {} segment{}".format(len(segments_info), "s" if len(segments_info) != 1 else ""),
            "count": len(segments_info),
            "segments": segments_info
        }
        
    except Exception as e:
        print("Error in list_pipe_segments: {}".format(str(e)))
        raise


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
        print("Error finding system type '{}': {}".format(system_type_name, str(e)))
        return None


def _find_default_system_type(doc):
    """Find the first available piping system type"""
    try:
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Plumbing.PipingSystemType)
        return collector.FirstElement()
    except Exception as e:
        print("Error finding default system type: {}".format(str(e)))
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
            return None
        
        # Access RoutingPreferenceManager property (following the API docs)
        try:
            routing_pref_manager = matching_pipe_type.RoutingPreferenceManager
            if not routing_pref_manager:
                print("RoutingPreferenceManager is null for pipe type: {}".format(get_element_name(matching_pipe_type)))
                return None
            
            # Get all rules from the routing preference manager using iterative GetRule
            rules = []
            group_type = DB.RoutingPreferenceRuleGroupType.Segments
            index = 0
            while True:
                try:
                    rule = routing_pref_manager.GetRule(group_type, index)
                    rules.append(rule)
                    index += 1
                except Exception:
                    # When we get an exception, we've reached the end of the rules
                    break
            
            # Check each rule for matching criteria
            for rule in rules:
                try:
                    if hasattr(rule, 'MEPPartId') and rule.MEPPartId != DB.ElementId.InvalidElementId:
                        # Get the segment associated with this rule
                        segment = doc.GetElement(rule.MEPPartId)
                        if not segment or not isinstance(segment, DB.Segment):
                            continue
                        
                        # Check if this segment has matching material and diameters
                        if _check_segment_rule_match(doc, rule, segment, material, nominal_diameter, inner_diameter, outer_diameter):
                            return {
                                "pipe_type": matching_pipe_type,
                                "segment": segment,
                                "rule": rule,
                                "match_found": True
                            }
                            
                except Exception as e:
                    print("Error checking rule: {}".format(str(e)))
                    continue
            
            # No matching rule found
            return {
                "pipe_type": matching_pipe_type,
                "segment": None,
                "rule": None,
                "match_found": False
            }
            
        except Exception as e:
            print("Error accessing RoutingPreferenceManager: {}".format(str(e)))
            return None
        
    except Exception as e:
        print("Error finding pipe type by exact match: {}".format(str(e)))
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
                    return False
        
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
                        size_match_found = True
                        break
                
                if not size_match_found:
                    return False
                    
            except Exception as e:
                print("Error checking segment sizes: {}".format(str(e)))
                return False
        
        # All criteria matched
        return True
        
    except Exception as e:
        print("Error checking segment rule match: {}".format(str(e)))
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
        print("Could not parse nominal diameter '{}': {}".format(nominal_diameter, str(e)))
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
        print("Error finding level '{}': {}".format(level_name, str(e)))
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
        print("Error finding closest level: {}".format(str(e)))
        return None


def _create_new_pipe(doc, source_object_id, start_point, end_point, inner_diameter, outer_diameter, nominal_diameter, level_name, system_type_name, pipe_type_name, material, properties):
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
            pipe_type_result = _create_new_pipe_type_with_segment(
                doc, pipe_type_name or "Custom Pipe Type", 
                inner_diameter, outer_diameter, nominal_diameter, material
            )
        
        # Extract pipe type from result
        if isinstance(pipe_type_result, dict):
            pipe_type = pipe_type_result.get("pipe_type")
            if not pipe_type_result.get("match_found", True):
                # Pipe type found but no matching segment rule - need to create new rule/segment
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
        _set_pipe_properties(pipe, source_object_id, properties, nominal_diameter, material)
        
        # Extract result information
        pipe_name = get_element_name(pipe) or properties.get('Mark', 'Pipe')
        
        return {
            "status": "success",
            "message": "Successfully created pipe '{}'".format(pipe_name),
            "element_id": str(pipe.Id.Value),
            "element_type": "pipe"
        }
        
    except Exception as e:
        print("Error creating pipe: {}".format(str(e)))
        raise


def _edit_existing_pipe(doc, element_id, start_point, end_point, inner_diameter, outer_diameter, nominal_diameter, level_name, system_type_name, pipe_type_name, material, properties):
    """Edit an existing pipe element"""
    try:
        # Find the existing pipe
        pipe = doc.GetElement(DB.ElementId(Int64(element_id)))
        if not pipe or not isinstance(pipe, DB.Plumbing.Pipe):
            raise Exception("Pipe with ID {} not found".format(element_id))
        
        # Get current pipe location curve
        location_curve = pipe.Location
        if not isinstance(location_curve, DB.LocationCurve):
            raise Exception("Pipe location is not curve-based")
        
        # Update pipe location
        new_line = DB.Line.CreateBound(start_point, end_point)
        location_curve.Curve = new_line
        
        # Update pipe type if criteria provided - using same logic as create new pipe
        if any([inner_diameter, outer_diameter, nominal_diameter, pipe_type_name, material]):
            # Find pipe type with exact matching logic (same as create new pipe)
            pipe_type_result = None
            if pipe_type_name:
                pipe_type_result = _find_pipe_type_by_exact_match(
                    doc, pipe_type_name, inner_diameter, outer_diameter, nominal_diameter, material
                )
            
            if not pipe_type_result:
                # No matching pipe type found - need to create new pipe type
                pipe_type_result = _create_new_pipe_type_with_segment(
                    doc, pipe_type_name or "Custom Pipe Type", 
                    inner_diameter, outer_diameter, nominal_diameter, material
                )
            
            # Extract pipe type from result
            if isinstance(pipe_type_result, dict):
                new_pipe_type = pipe_type_result.get("pipe_type")
                if not pipe_type_result.get("match_found", True):
                    # Pipe type found but no matching segment rule - need to create new rule/segment
                    _create_new_segment_rule(
                        doc, new_pipe_type, inner_diameter, outer_diameter, nominal_diameter, material
                    )
            else:
                new_pipe_type = pipe_type_result
            
            # Change pipe type if different from current
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
        _set_pipe_properties(pipe, None, properties, nominal_diameter, material)
        
        # Extract result information
        pipe_name = get_element_name(pipe) or properties.get('Mark', 'Pipe')
        
        return {
            "status": "success",
            "message": "Successfully modified pipe '{}'".format(pipe_name),
            "element_id": str(pipe.Id.Value),
            "element_type": "pipe"
        }
        
    except Exception as e:
        print("Error editing pipe: {}".format(str(e)))
        raise


def _set_pipe_properties(pipe, source_object_id, properties, nominal_diameter=None, material=None):
    """Set additional properties on a pipe element"""
    try:
        # Set segment to RBS_PIPE_SEGMENT_PARAM if provided (find segment by material name)
        if material is not None:
            try:
                # Find the segment element by material name
                segment_element = _find_segment_by_material_name(pipe.Document, material)
                if segment_element:
                    segment_param = pipe.get_Parameter(DB.BuiltInParameter.RBS_PIPE_SEGMENT_PARAM)
                    if segment_param and not segment_param.IsReadOnly:
                        segment_param.Set(segment_element.Id)
                    else:
                        print("Could not set pipe segment - parameter is read-only or not found")
                else:
                    print("Could not find segment with material name '{}' in document".format(material))
            except Exception as e:
                print("Error setting pipe segment: {}".format(str(e)))
        
        # Set nominal diameter to RBS_PIPE_DIAMETER_PARAM if provided
        if nominal_diameter is not None:
            try:
                # Convert nominal diameter from mm to feet (Revit internal units)
                nominal_diameter_feet = nominal_diameter / 304.8 if nominal_diameter else None
                if nominal_diameter_feet:
                    diameter_param = pipe.get_Parameter(DB.BuiltInParameter.RBS_PIPE_DIAMETER_PARAM)
                    if diameter_param and not diameter_param.IsReadOnly:
                        diameter_param.Set(nominal_diameter_feet)
                    else:
                        print("Could not set pipe diameter - parameter is read-only or not found")
            except Exception as e:
                print("Error setting pipe diameter: {}".format(str(e)))

        if source_object_id:
            param = pipe.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)
            if param and not param.IsReadOnly:
                param.Set(source_object_id)

        if not properties:
            return
        
        for key, value in properties.items():
            try:
                # Handle common parameters
                if key.lower() == 'mark':
                    continue
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
                        param.Set(DB.ElementId(Int64(value)))
                        
            except Exception as e:
                print("Could not set parameter '{}': {}".format(key, str(e)))
                continue
                
    except Exception as e:
        print("Error setting pipe properties: {}".format(str(e)))


def _extract_pipe_configuration(pipe):
    """Extract configuration from an existing pipe"""
    try:
        config = {
            "element_id": str(pipe.Id.Value),
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
        print("Error extracting pipe configuration: {}".format(str(e)))
        return {"element_id": str(pipe.Id.Value), "error": str(e)}


def _get_comprehensive_pipe_info(pipe):
    """Get comprehensive information about a pipe element"""
    try:
        pipe_info = {
            "element_id": str(pipe.Id.Value),
            "name": get_element_name(pipe),
            "category": "Pipes",
            "category_id": str(pipe.Category.Id.Value) if pipe.Category else None,
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
        print("Error getting comprehensive pipe info: {}".format(str(e)))
        return {
            "element_id": str(pipe.Id.Value),
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
        print("Could not extract pipe type properties: {}".format(str(e)))
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
        print("Could not extract system type properties: {}".format(str(e)))
        return {
            "error": str(e),
            "fluid": {},
            "calculation": {},
            "additional_parameters": {}
        }


def _find_exact_segment_match(doc, material, nominal_diameter, inner_diameter, outer_diameter, roughness=None, base_segment_name=None):
    """Find an existing segment that matches material name and has a size matching the diameters
    
    Args:
        doc: Revit document
        material (str): Material name to match (used as segment name)
        nominal_diameter (float): Nominal diameter in mm
        inner_diameter (float): Inner diameter in mm
        outer_diameter (float): Outer diameter in mm
        roughness (float, optional): Surface roughness (not used for matching, for signature compatibility)
        base_segment_name (str, optional): Base segment name (not used for matching, for signature compatibility)
    """
    try:
        # Use FilteredElementCollector to get all segments (following the C# sample)
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Segment)
        
        tolerance = 1.0  # 1mm tolerance for diameter matching
        length_factor = 304.8  # Convert feet to mm (as shown in C# sample)
        
        for segment in collector:
            try:
                # Check material/name match (case-insensitive)
                segment_name = get_element_name(segment)
                if not segment_name or segment_name.lower() != material.lower():
                    continue
                
                # Get all sizes for this segment
                sizes = segment.GetSizes()
                
                for size in sizes:
                    try:
                        # Get diameters in mm (convert from feet using length_factor)
                        nominal_mm = size.NominalDiameter * length_factor
                        inner_mm = size.InnerDiameter * length_factor  
                        outer_mm = size.OuterDiameter * length_factor
                        
                        # Check if this size matches our criteria
                        nominal_match = nominal_diameter is None or abs(nominal_mm - nominal_diameter) <= tolerance
                        inner_match = inner_diameter is None or abs(inner_mm - inner_diameter) <= tolerance
                        outer_match = outer_diameter is None or abs(outer_mm - outer_diameter) <= tolerance
                        
                        if nominal_match and inner_match and outer_match:
                            # Found exact match
                            return {
                                "segment": segment,
                                "size": size,
                                "nominal_diameter": nominal_mm,
                                "inner_diameter": inner_mm,
                                "outer_diameter": outer_mm
                            }
                            
                    except Exception as e:
                        print("Error checking size in segment {}: {}".format(segment.Id, str(e)))
                        continue
                
            except Exception as e:
                print("Error checking segment {}: {}".format(segment.Id, str(e)))
                continue
        
        # No exact match found
        return None
        
    except Exception as e:
        print("Error finding exact segment match: {}".format(str(e)))
        return None


def _create_new_segment_with_size(doc, material, nominal_diameter, inner_diameter, outer_diameter, roughness, base_segment_name):
    """Create a new segment with the specified size or edit existing segment with same name"""
    try:
        # First, check if a segment with the same name already exists
        existing_segment = None
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Segment)
        for segment in collector:
            segment_name = get_element_name(segment)
            if segment_name and material and segment_name.lower() == material.lower():
                existing_segment = segment
                break
        
        if existing_segment:
            # Use the existing segment and add new size to it
            new_segment = existing_segment
        else:
            # Create a new segment since none exists with this name
            
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
            
            # Set the name for the new segment
            new_segment.Name = material
        
        # Set roughness if specified (for both new and existing segments)
        if roughness is not None:
            new_segment.Roughness = float(roughness)
        
        # Create a new MEPSize and add it to the segment
        length_factor = 304.8  # Convert mm to feet
        
        # Convert diameters to feet
        nominal_feet = nominal_diameter / length_factor if nominal_diameter else inner_diameter / length_factor
        inner_feet = inner_diameter / length_factor
        outer_feet = outer_diameter / length_factor
        
        # Create and add new MEPSize to the segment
        try:
            if existing_segment:
                # For existing segments, first check if this size already exists
                
                # Check if size already exists
                size_already_exists = False
                tolerance = 1.0  # 1mm tolerance
                try:
                    existing_sizes = list(new_segment.GetSizes())
                    for existing_size in existing_sizes:
                        existing_nominal_mm = existing_size.NominalDiameter * length_factor
                        existing_inner_mm = existing_size.InnerDiameter * length_factor
                        existing_outer_mm = existing_size.OuterDiameter * length_factor
                        
                        # Check if all diameters match within tolerance
                        nominal_match = nominal_diameter is None or abs(existing_nominal_mm - nominal_diameter) <= tolerance
                        inner_match = inner_diameter is None or abs(existing_inner_mm - inner_diameter) <= tolerance
                        outer_match = outer_diameter is None or abs(existing_outer_mm - outer_diameter) <= tolerance
                        
                        if nominal_match and inner_match and outer_match:
                            size_already_exists = True
                            break
                            
                except Exception as e:
                    print("Error checking existing sizes: {}".format(str(e)))
                
                if size_already_exists:
                    success = True  # Consider this successful since size exists
                else:
                    # Add the new size to existing segment
                    success = _add_mep_size_to_segment(new_segment, nominal_feet, inner_feet, outer_feet)
                
                if not success:
                    print("Used existing segment: {} (ID: {}) but could not add custom size".format(material, str(new_segment.Id.Value)))
            else:
                # For new segments, replace all existing sizes with our custom size
                
                # Step 1: Get all existing sizes first
                existing_nominal_diameters = _get_existing_sizes_from_segment(new_segment)
                
                # Step 2: Add our custom MEPSize
                success = _add_mep_size_to_segment(new_segment, nominal_feet, inner_feet, outer_feet)
                
                # Step 3: Remove the old sizes we captured earlier (now that we have our new size in place)
                if success and existing_nominal_diameters:
                    _remove_sizes_by_nominal_diameter(new_segment, existing_nominal_diameters)
                    
                if not success:
                    print("Created new segment: {} (ID: {}) but could not add custom size".format(material, str(new_segment.Id.Value)))
            
            return {
                "segment": new_segment,
                "nominal_diameter": nominal_diameter,
                "inner_diameter": inner_diameter,
                "outer_diameter": outer_diameter
            }
            
        except Exception as e:
            print("Could not modify segment sizes directly: {}".format(str(e)))
            # Return the segment anyway - sizes may need to be set manually in Revit
            return {
                "segment": new_segment,
                "nominal_diameter": nominal_diameter,
                "inner_diameter": inner_diameter,
                "outer_diameter": outer_diameter
            }
        
    except Exception as e:
        print("Error creating new segment: {}".format(str(e)))
        raise


def _get_existing_sizes_from_segment(segment):
    """
    Get all existing MEPSizes from a segment.
    
    Args:
        segment: The Revit segment element
    
    Returns:
        list: List of nominal diameters (in feet) of existing sizes
    """
    try:
        existing_sizes = list(segment.GetSizes())
        nominal_diameters = [size.NominalDiameter for size in existing_sizes]
        
        return nominal_diameters
        
    except Exception as e:
        print("Error getting existing sizes from segment: {}".format(str(e)))
        return []


def _remove_sizes_by_nominal_diameter(segment, nominal_diameters_to_remove):
    """
    Remove specific MEPSizes from a segment by their nominal diameters.
    
    Args:
        segment: The Revit segment element
        nominal_diameters_to_remove: List of nominal diameters (in feet) to remove
    
    Returns:
        int: Number of sizes successfully removed
    """
    try:
        sizes_removed = 0
        
        if not nominal_diameters_to_remove:
            return 0
        
        for nominal_diameter_feet in nominal_diameters_to_remove:
            try:
                segment.RemoveSize(nominal_diameter_feet)
                sizes_removed += 1
            except Exception as e:
                print("Could not remove size {:.3f}ft: {}".format(nominal_diameter_feet, str(e)))
        
        return sizes_removed
        
    except Exception as e:
        print("Error removing sizes from segment: {}".format(str(e)))
        return 0


def _add_mep_size_to_segment(segment, nominal_diameter_feet, inner_diameter_feet, outer_diameter_feet):
    """
    Create and add a MEPSize to a segment.
    
    Args:
        segment: The Revit segment element
        nominal_diameter_feet (float): Nominal diameter in feet (Revit internal units)
        inner_diameter_feet (float): Inner diameter in feet (Revit internal units)  
        outer_diameter_feet (float): Outer diameter in feet (Revit internal units)
    
    Returns:
        bool: True if MEPSize was successfully added, False otherwise
    """
    try:
        # Create MEPSize using the constructor parameters from Revit API docs
        # MEPSize(nominalDiameter, innerDiameter, outerDiameter, usedInSizeLists, usedInSizing)
        mep_size = DB.MEPSize(
            nominal_diameter_feet,  # nominalDiameter (Double) - in feet
            inner_diameter_feet,    # innerDiameter (Double) - in feet  
            outer_diameter_feet,    # outerDiameter (Double) - in feet
            True,                   # usedInSizeLists (Boolean) - whether it's used in size lists
            True                    # usedInSizing (Boolean) - whether it's used in sizing
        )
        
        # Add the MEPSize to the segment using AddSize method
        segment.AddSize(mep_size)
        
        return True
        
    except Exception as e:
        print("Error adding MEPSize to segment: {}".format(str(e)))
        return False


def _find_segment_by_material_name(doc, material_name):
    """Find a segment by material name (searches segment names that contain the material name)"""
    try:
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Segment)
        
        # First try exact match
        for segment in collector:
            segment_name = get_element_name(segment)
            if segment_name and segment_name.lower() == material_name.lower():
                return segment
        
        # Then try partial match (segment name contains material name)
        collector = DB.FilteredElementCollector(doc).OfClass(DB.Segment)
        for segment in collector:
            segment_name = get_element_name(segment)
            if segment_name and material_name.lower() in segment_name.lower():
                return segment
        
        return None
    except Exception as e:
        print("Error finding segment by material name '{}': {}".format(material_name, str(e)))
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
        new_pipe_type.Name = pipe_type_name
        
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
        print("Error creating new pipe type with segment: {}".format(str(e)))
        raise


def _get_existing_routing_rules(routing_pref_manager, group_type):
    """
    Get all existing routing preference rules from a specific group.
    
    Args:
        routing_pref_manager: The RoutingPreferenceManager
        group_type: The RoutingPreferenceRuleGroupType (e.g., DB.RoutingPreferenceRuleGroupType.Segments)
    
    Returns:
        list: List of existing RoutingPreferenceRule objects
    """
    try:
        existing_rules = []
        
        # Since there's no GetRules method, we need to iterate through indices
        # until we get an ArgumentException (index out of bounds)
        index = 0
        while True:
            try:
                rule = routing_pref_manager.GetRule(group_type, index)
                existing_rules.append(rule)
                index += 1
            except Exception:
                # When we get an exception, we've reached the end of the rules
                break
        
        return existing_rules
        
    except Exception as e:
        print("Error getting existing routing rules: {}".format(str(e)))
        return []


def _edit_elbow_rules_for_nominal_diameter(elbow_rules, nominal_diameter):
    """
    Edit existing elbow routing preference rules to set nominal diameter criteria.
    
    Args:
        elbow_rules (list): List of RoutingPreferenceRule objects for elbows
        nominal_diameter (float): Nominal diameter in mm to set as criteria
        
    Returns:
        int: Number of rules successfully edited
    """
    try:
        if not elbow_rules or nominal_diameter is None:
            return 0
        
        # Convert nominal diameter from mm to feet (Revit internal units)
        nominal_diameter_feet = nominal_diameter / 304.8
        rules_edited = 0
        
        for i, rule in enumerate(elbow_rules):
            try:
                # Get existing criteria count
                existing_criteria_count = rule.NumberOfCriteria
                
                # Remove all existing criteria first (to avoid conflicts)
                for j in range(existing_criteria_count):
                    try:
                        # Always remove from index 0 since criteria shift down after removal
                        rule.RemoveCriteron(0)
                    except Exception as e:
                        print("Error removing criterion {}: {}".format(j, str(e)))
                        break
                
                # Add new nominal diameter criterion
                try:
                    # Create a RoutingCriterionBase object for nominal diameter
                    criterion = DB.PrimarySizeCriterion(nominal_diameter_feet, nominal_diameter_feet)
                    
                    rule.AddCriterion(criterion)
                    rules_edited += 1
                    
                except Exception as e:
                    print("Error adding nominal diameter criterion to rule {}: {}".format(i + 1, str(e)))
                    # Try alternative approach - create criterion with range/tolerance
                    try:
                        # Alternative: Try creating criterion with range
                        min_diameter = nominal_diameter_feet * 0.99  # 1% tolerance
                        max_diameter = nominal_diameter_feet * 1.01
                        criterion = criterion = DB.PrimarySizeCriterion(nominal_diameter_feet, nominal_diameter_feet)(min_diameter, max_diameter)
                        rule.AddCriterion(criterion)
                        rules_edited += 1
                    except Exception as e2:
                        print("Alternative criterion creation also failed: {}".format(str(e2)))
                
            except Exception as e:
                print("Error editing elbow rule {}: {}".format(i + 1, str(e)))
                continue
        
        return rules_edited
        
    except Exception as e:
        print("Error in _edit_elbow_rules_for_nominal_diameter: {}".format(str(e)))
        return 0

def _find_fitting_family_id(doc):
    # TODO: Need to refine based on size and name
    collector = DB.FilteredElementCollector(doc).OfClass(DB.FamilySymbol).OfCategory(DB.BuiltInCategory.OST_PipeFitting)

    for family_symbol in collector:
        if family_symbol.FamilyName == "M_Elbow - Welded - Generic":
            return family_symbol.Id
    return DB.ElementId.InvalidElementId

def _create_new_elbow_rule(doc, routing_pref_manager, group_type, nominal_diameter):
    """
    Create a new elbow routing preference rule with nominal diameter criteria.
    
    Args:
        routing_pref_manager: The RoutingPreferenceManager
        group_type: DB.RoutingPreferenceRuleGroupType.Elbows
        nominal_diameter (float): Nominal diameter in mm to set as criteria
        
    Returns:
        bool: True if rule was created successfully, False otherwise
    """
    try:
        if nominal_diameter is None:
            return False
        
        # Convert nominal diameter from mm to feet (Revit internal units)
        nominal_diameter_feet = nominal_diameter / 304.8
        # Create a new RoutingPreferenceRule for elbows
        # Use InvalidElementId since we're creating a general rule (not tied to specific elbow)
        # TODO: Search for family and replace invalid element id.
        routing_rule = DB.RoutingPreferenceRule(_find_fitting_family_id(doc), "Custom elbow rule for diameter")
        
        # Add nominal diameter criterion to the rule
        try:
            # Create a RoutingCriterionBase object for nominal diameter
            # Use the appropriate constructor for routing criterion
            criterion = DB.PrimarySizeCriterion(nominal_diameter_feet, nominal_diameter_feet)
            
            routing_rule.AddCriterion(criterion)
            
        except Exception as e:
            print("Error adding nominal diameter criterion: {}".format(str(e)))
            # Try alternative approach - create criterion with different method
            try:
                # Alternative: Try creating criterion with range/tolerance
                min_diameter = nominal_diameter_feet * 0.99  # 1% tolerance
                max_diameter = nominal_diameter_feet * 1.01
                criterion = DB.PrimarySizeCriterion(min_diameter, max_diameter)
                routing_rule.AddCriterion(criterion)
            except Exception as e2:
                print("Alternative criterion creation also failed: {}".format(str(e2)))
                return False
        
        # Add the rule to the RoutingPreferenceManager
        try:
            routing_pref_manager.AddRule(group_type, routing_rule)
            return True
            
        except Exception as e:
            print("Primary elbow rule addition failed: {}".format(str(e)))
            # Try alternative approach with position parameter
            try:
                routing_pref_manager.AddRule(group_type, routing_rule, 0)
                return True
            except Exception as e2:
                print("Alternative elbow rule addition also failed: {}".format(str(e2)))
                return False
        
    except Exception as e:
        print("Error in _create_new_elbow_rule: {}".format(str(e)))
        return False


def _remove_routing_rules_by_count(routing_pref_manager, group_type, rule_count_to_remove):
    """
    Remove existing routing preference rules from a group by removing from index 0.
    
    Since RemoveRule uses index-based removal, we remove from index 0 repeatedly.
    When a rule at index 0 is removed, all subsequent rules shift down by one index.
    
    Args:
        routing_pref_manager: The RoutingPreferenceManager
        group_type: The RoutingPreferenceRuleGroupType
        rule_count_to_remove: Number of rules to remove from the beginning
    
    Returns:
        int: Number of rules successfully removed
    """
    try:
        rules_removed = 0
        
        if rule_count_to_remove <= 0:
            return 0
        
        # Remove rules starting from index 0, repeatedly
        # Each removal shifts remaining rules down, so we always remove index 0
        for i in range(rule_count_to_remove):
            try:
                # Always remove from index 0 since rules shift down after each removal
                routing_pref_manager.RemoveRule(group_type, 0)
                rules_removed += 1
            except Exception as e:
                print("Could not remove routing rule at index 0: {}".format(str(e)))
                break  # Stop if we can't remove any more rules
        
        return rules_removed
        
    except Exception as e:
        print("Error removing routing rules: {}".format(str(e)))
        return 0


def _create_new_segment_rule(doc, pipe_type, inner_diameter, outer_diameter, nominal_diameter, material):
    """Create a new segment and add it as a routing rule to the pipe type"""
    try:
        # Create a new segment first
        segment_result = _create_new_segment_with_size(
            doc, material, nominal_diameter, inner_diameter, outer_diameter, 
            None, None
        )
        
        if not segment_result or not segment_result.get("segment"):
            raise Exception("Failed to create new segment")
        
        new_segment = segment_result["segment"]
        
        # Access the RoutingPreferenceManager
        try:
            routing_pref_manager = pipe_type.RoutingPreferenceManager
            if not routing_pref_manager:
                return segment_result
            
            # Step 1: Get existing routing rules first
            group_type = DB.RoutingPreferenceRuleGroupType.Segments
            existing_rules = _get_existing_routing_rules(routing_pref_manager, group_type)
            
            # Step 2: Create and add new routing preference rule for the segment
            
            try:
                # Create a new RoutingPreferenceRule for the segment
                # The RoutingPreferenceRule constructor requires ElementId and description
                routing_rule = DB.RoutingPreferenceRule(new_segment.Id, "Custom segment rule")
                
                # Add the rule to the RoutingPreferenceManager using AddRule method
                routing_pref_manager.AddRule(group_type, routing_rule)
                
                # Step 3: Remove old routing rules now that we have our new one in place
                if existing_rules:
                    _remove_routing_rules_by_count(routing_pref_manager, group_type, len(existing_rules))
                
            except Exception as e:
                # Try alternative approach if the above doesn't work
                print("Primary rule creation failed: {}".format(str(e)))
                try:
                    # Alternative: Try with position parameter
                    routing_rule = DB.RoutingPreferenceRule(new_segment.Id, "Custom segment rule")
                    routing_pref_manager.AddRule(group_type, routing_rule, 0)
                    
                    # Remove old rules after successful addition
                    if existing_rules:
                        _remove_routing_rules_by_count(routing_pref_manager, group_type, len(existing_rules))
                    
                except Exception as e2:
                    print("Could not add segment rule automatically: {}".format(str(e2)))
                    print("Segment created successfully, but rule may need manual setup in Revit UI")
            
            # Step 4: Handle Elbow routing rules - get existing and edit for nominal diameter
            try:
                elbow_group_type = DB.RoutingPreferenceRuleGroupType.Elbows
                existing_elbow_rules = _get_existing_routing_rules(routing_pref_manager, elbow_group_type)
                
                if nominal_diameter is not None:
                    if existing_elbow_rules:
                        # Edit existing elbow rules to set nominal diameter criteria
                        _edit_elbow_rules_for_nominal_diameter(existing_elbow_rules, nominal_diameter)
                    else:
                        # No existing elbow rules found - create a new one
                        _create_new_elbow_rule(doc, routing_pref_manager, elbow_group_type, nominal_diameter)
                    
            except Exception as e:
                print("Error handling elbow routing rules: {}".format(str(e)))
            
            return segment_result
            
        except Exception as e:
            print("Could not access RoutingPreferenceManager: {}".format(str(e)))
            return segment_result
        
    except Exception as e:
        print("Error creating new segment rule: {}".format(str(e)))
        raise 