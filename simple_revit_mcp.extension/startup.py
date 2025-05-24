# -*- coding: UTF-8 -*-
from pyrevit import routes, revit, DB
import json
import tempfile
import os
import traceback
import logging  

import System
from System.IO import Path

from System.Collections.Generic import List
from Autodesk.Revit.DB import (
    FilteredElementCollector,
    BuiltInCategory,
    ViewFamilyType,
    ViewFamily,
    ImageExportOptions,
    ImageFileType,
    View as RevitView,  # Renaming to avoid conflict with flask view
    ExportRange,
    ImageResolution,
    FitDirectionType,
    ZoomFitType,
    StorageType,
    XYZ,
    FamilySymbol,
    Structure,
    Line
)

# Get a logger instance for this module
logger = logging.getLogger(__name__)
doc = revit.doc
api = routes.API('revit_mcp')


def normalize_string(element_string):
    """
    Normalizes a string by removing non-ASCII characters.
    This helps prevent potential encoding issues when processing or displaying the string.
    """
    if element_string is None:
        return None

    normalized_string = element_string.encode('ascii', 'ignore').decode('ascii')
    return normalized_string


@api.route('/status/', methods=["GET"])
def api_status():
    """Returns API status to check if it's registered"""
    return routes.make_response(data={
        "status": "active",
        "api_name": "revit_mcp"
    })


@api.route('/model_info/', methods=["GET"])
def get_model_elements():
    """
    Get information about the current Revit model and its elements.
    """
    doc = revit.doc

    model_name = doc.Title
    
    # Get various categories of elements
    walls = FilteredElementCollector(doc)\
        .OfCategory(BuiltInCategory.OST_Walls)\
        .WhereElementIsNotElementType()\
        .ToElements()
        
    doors = FilteredElementCollector(doc)\
        .OfCategory(BuiltInCategory.OST_Doors)\
        .WhereElementIsNotElementType()\
        .ToElements()
        
    windows = FilteredElementCollector(doc)\
        .OfCategory(BuiltInCategory.OST_Windows)\
        .WhereElementIsNotElementType()\
        .ToElements()
        
    furniture = FilteredElementCollector(doc)\
        .OfCategory(BuiltInCategory.OST_Furniture)\
        .WhereElementIsNotElementType()\
        .ToElements()
    
    rooms = FilteredElementCollector(doc)\
        .OfCategory(BuiltInCategory.OST_Rooms)\
        .WhereElementIsNotElementType()\
        .ToElements()
    
    levels = FilteredElementCollector(doc)\
        .OfCategory(BuiltInCategory.OST_Levels)\
        .WhereElementIsNotElementType()\
        .ToElements()
    
    # Gather model information
    model_info = {
        "Model Name": normalize_string(model_name),
        "Element Counts": {
            "Walls": len(list(walls)),
            "Doors": len(list(doors)),
            "Windows": len(list(windows)),
            "Furniture": len(list(furniture)),
            "Rooms": len(list(rooms)),
            "Levels": len(list(levels))
        },
        "Rooms": [normalize_string(room.LookupParameter("Name").AsString()) 
                  for room in rooms
                  if room.LookupParameter("Name") is not None 
                  and room.LookupParameter("Name").HasValue],
                  
        "Levels": [normalize_string(level.Name)
                  for level in levels]
    }

    return model_info


@api.route('/get_view/<view_name>')
def get_view(doc, view_name):  # Add doc parameter to signal MCP that this needs Revit context
    """Export a named Revit view as a PNG image and return the image data"""
    try:
        # Define a fixed output folder 
        output_folder = os.path.join(tempfile.gettempdir(), "RevitExports")
        
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            
        # Create a simple filename prefix
        file_path_prefix = os.path.join(output_folder, "export")
        
        # Find the view by name
        target_view = None
        all_views = FilteredElementCollector(doc).OfClass(RevitView).ToElements()
        
        for view in all_views:
            if view.Name == view_name:
                target_view = view
                break
        
        if not target_view:
            return routes.make_response(
                data={"error": "View not found"},
                status=404
            )
        
        # Set up export options
        ieo = ImageExportOptions()
        ieo.ExportRange = ExportRange.SetOfViews
        viewIds = List[DB.ElementId]()
        viewIds.Add(target_view.Id)
        ieo.SetViewsAndSheets(viewIds)
        ieo.FilePath = file_path_prefix
        ieo.HLRandWFViewsFileType = ImageFileType.PNG
        ieo.ShadowViewsFileType = ImageFileType.PNG
        ieo.ImageResolution = ImageResolution.DPI_150
        ieo.ZoomType = ZoomFitType.Zoom
        ieo.Zoom = 100
        
        # Export the image
        doc.ExportImage(ieo)
        
        # Find the exported file (most recent PNG in folder)
        matching_files = [os.path.join(output_folder, f) for f in os.listdir(output_folder) 
                         if f.endswith('.png')]
        matching_files.sort(key=lambda x: os.path.getctime(x), reverse=True)
        
        if not matching_files:
            return routes.make_response(
                data={"error": "Export failed - no image found"},
                status=500
            )
            
        exported_file = matching_files[0]
        
        # Read and encode the image
        with open(exported_file, 'rb') as img_file:
            img_data = img_file.read()
            
        import base64
        encoded_data = base64.b64encode(img_data).decode('utf-8')

        # Clean up the file
        os.remove(exported_file)

        return routes.make_response(data={
            "image_data": encoded_data,
            "content_type": "image/png"
        })

    except Exception as e:
        return routes.make_response(
            data={"error": str(e)},
            status=500
        )


@api.route('/place_family/', methods=["POST"])
def place_family(doc, request):
    """
    Place a family instance at a specified location in the model.
    
    Expected request data:
    {
        "family_type": "Furniture",
        "type_name": "Chair
        "location": {"x": 0.0, "y": 0.0, "z": 0.0},
        "rotation": 0.0,
        "properties": {
            "Mark": "A1",
            "Comments": "Placed through API",
            "Description": "Sample object"
        }
    }
    """
    try:
        # Parse request data
        if not request or not request.data:
            return routes.make_response(
                data={"error": "No data provided or invalid request format"},
                status=400
            )
            
        # Parse JSON if needed
        data = None
        if isinstance(request.data, str):
            try:
                data = json.loads(request.data)
            except Exception as json_err:
                return routes.make_response(
                    data={"error": "Invalid JSON format: " + str(json_err)},
                    status=400
                )
        else:
            data = request.data
            
        # Validate data structure
        if not data or not isinstance(data, dict):
            return routes.make_response(
                data={"error": "Invalid data format - expected JSON object"},
                status=400
            )
        
        # Extract required fields
        family_type = data.get("family_type")
        type_name = data.get("type_name")
        location = data.get("location", {})
        rotation = data.get("rotation", 0.0)
        properties = data.get("properties", {})
        
        # Basic validation
        if not family_type:
            return routes.make_response(
                data={"error": "No family_type provided"},
                status=400
            )
            
        # Validate location
        if not location or not all(k in location for k in ["x", "y", "z"]):
            return routes.make_response(
                data={"error": "Invalid location - must include x, y, z coordinates"},
                status=400
            )
            
        # Parse family and type names
        family_name = family_type
        type_name = type_name
        
        
        # Find the appropriate family symbol (type)
        symbols = FilteredElementCollector(doc)\
            .OfClass(FamilySymbol)\
            .ToElements()
            
        target_symbol = None
        for symbol in symbols:
            # Added a check to ensure symbol.Family is not None before accessing .Name
            if symbol.Family: 
                if type_name:
                    # Match both family name and type name
                    if symbol.Family.Name == family_name and symbol.Name == type_name:
                        target_symbol = symbol
                        break
                else:
                    # Match just family name
                    if symbol.Family.Name == family_name:
                        target_symbol = symbol
                        break
                    
        if not target_symbol:
            return routes.make_response(
                data={"error": "Family type not found: " + family_type},
                status=404
            )
        
        # Create the location point
        point = XYZ(
            float(location["x"]),
            float(location["y"]),
            float(location["z"])
        )
        
        # Start a transaction
        t = DB.Transaction(doc, "Place Family Instance")
        t.Start()
            
        try:
            # Ensure the symbol is activated
            if not target_symbol.IsActive:
                target_symbol.Activate()
                
            # Create the instance
            new_instance = doc.Create.NewFamilyInstance(
                point,
                target_symbol,
                Structure.StructuralType.NonStructural
            )
            
            # Apply rotation if specified
            if rotation != 0:
                rotation_radians = rotation * (3.14159265359 / 180.0)
                axis = Line.CreateBound(point, point.Add(XYZ(0, 0, 1)))
                
                try:
                    if hasattr(new_instance.Location, "Rotate"):
                        new_instance.Location.Rotate(axis, rotation_radians)
                except Exception as rotate_err:
                    # Log but continue
                    print("Warning: Could not rotate element: " + str(rotate_err))
            
            # Set custom properties
            for param_name, param_value in properties.items():
                param = new_instance.LookupParameter(param_name)
                if param and param.HasValue:
                    # Set parameter based on its storage type
                    if param.StorageType == StorageType.String:
                        param.Set(str(param_value))
                    elif param.StorageType == StorageType.Integer:
                        param.Set(int(param_value))
                    elif param.StorageType == StorageType.Double:
                        param.Set(float(param_value))
            
            t.Commit()

            
            # Return information about the placed instance
            return routes.make_response(data={
                "status": "success",
                "element_id": new_instance.Id.IntegerValue,
                "family": family_type,
                "type": type_name,
                "location": {
                    "x": point.X,
                    "y": point.Y,
                    "z": point.Z
                },
                "rotation": rotation,
                "properties_set": list(properties.keys())
            })
                
        except Exception as tx_error:
            # Roll back the transaction if something went wrong
            if t.HasStarted() and not t.HasEnded():
                t.RollBack()
            raise tx_error
        
    except Exception as e:
        error_trace = traceback.format_exc()
        return routes.make_response(
            data={"error": str(e), "traceback": error_trace},
            status=500
        )
    