# -*- coding: UTF-8 -*-
"""
Geometry Management Module for Revit MCP
Handles geometry analysis functionality including bounding box operations
"""

from .utils import get_element_name, RoomWarningSwallower
from pyrevit import routes, revit, DB
import json
import traceback
import logging
import math

logger = logging.getLogger(__name__)


def register_geometry_management_routes(api):
    """Register all geometry management routes with the API"""

    @api.route("/check_points_in_bounding_box/", methods=["POST"])
    @api.route("/check_points_in_bounding_box", methods=["POST"])
    def check_points_in_bounding_box(doc, request):
        """
        Check if multiple start and end points are inside the bounding box of a selected Revit element.
        
        This endpoint checks whether given start and end points are inside the bounding box 
        of the currently selected Revit element. For each point pair, it returns true if 
        either the start point OR the end point is inside the bounding box.

        Expected request data:
        {
            "point_pairs": [
                {
                    "start_point": {"x": 1000.0, "y": 2000.0, "z": 3000.0},
                    "end_point": {"x": 1500.0, "y": 2500.0, "z": 3500.0}
                },
                {
                    "start_point": {"x": 4000.0, "y": 5000.0, "z": 6000.0},
                    "end_point": {"x": 4500.0, "y": 5500.0, "z": 6500.0}
                }
            ]
        }
        
        Returns:
        {
            "results": [true, false, ...],  // Boolean for each point pair
            "point_pairs": [...],           // Echo of input point pairs
            "selected_count": 1,
            "bounding_box_info": {...},
            "element": {...}
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

            # Extract point pairs
            point_pairs_data = data.get("point_pairs")
            if not point_pairs_data or not isinstance(point_pairs_data, list):
                return routes.make_response(
                    data={"error": "point_pairs is required and must be a list"},
                    status=400,
                )

            if len(point_pairs_data) == 0:
                return routes.make_response(
                    data={"error": "At least one point pair is required"},
                    status=400,
                )

            # Validate and parse point pairs
            FEET_TO_MM = 304.8
            parsed_point_pairs = []
            
            for i, pair in enumerate(point_pairs_data):
                if not isinstance(pair, dict):
                    return routes.make_response(
                        data={"error": "Point pair {} must be an object".format(i)},
                        status=400,
                    )
                
                start_point_data = pair.get("start_point")
                end_point_data = pair.get("end_point")
                
                if not start_point_data or not isinstance(start_point_data, dict):
                    return routes.make_response(
                        data={"error": "start_point is required for point pair {}".format(i)},
                        status=400,
                    )
                
                if not end_point_data or not isinstance(end_point_data, dict):
                    return routes.make_response(
                        data={"error": "end_point is required for point pair {}".format(i)},
                        status=400,
                    )

                try:
                    # Parse start point coordinates
                    start_x = float(start_point_data.get("x", 0))
                    start_y = float(start_point_data.get("y", 0))
                    start_z = float(start_point_data.get("z", 0))
                    
                    # Parse end point coordinates
                    end_x = float(end_point_data.get("x", 0))
                    end_y = float(end_point_data.get("y", 0))
                    end_z = float(end_point_data.get("z", 0))
                    
                    # Convert from mm to feet (Revit internal units)
                    start_point = DB.XYZ(start_x / FEET_TO_MM, start_y / FEET_TO_MM, start_z / FEET_TO_MM)
                    end_point = DB.XYZ(end_x / FEET_TO_MM, end_y / FEET_TO_MM, end_z / FEET_TO_MM)
                    
                    parsed_point_pairs.append({
                        "start_point": start_point,
                        "end_point": end_point,
                        "original_start": {"x": start_x, "y": start_y, "z": start_z},
                        "original_end": {"x": end_x, "y": end_y, "z": end_z}
                    })
                    
                except (ValueError, TypeError) as e:
                    return routes.make_response(
                        data={"error": "Invalid coordinates in point pair {}: {}".format(i, str(e))},
                        status=400,
                    )

            # Get current selection
            selection = revit.get_selection()
            if not selection.element_ids:
                return routes.make_response(
                    data={
                        "error": "No element selected. Please select exactly one element to analyze its bounding box."
                    },
                    status=400,
                )
            
            # Ensure exactly one element is selected
            if len(selection.element_ids) != 1:
                return routes.make_response(
                    data={
                        "error": "Multiple elements selected. Please select exactly one element to analyze its bounding box."
                    },
                    status=400,
                )

            # Get the single selected element
            element_id = selection.element_ids[0]
            try:
                element = doc.GetElement(element_id)
                if not element:
                    return routes.make_response(
                        data={"error": "Selected element not found in document"},
                        status=400,
                    )
            except Exception as e:
                return routes.make_response(
                    data={"error": "Failed to get selected element: {}".format(str(e))},
                    status=400,
                )

            # Prepare element info
            element_info = {
                "id": str(element.Id.Value),
                "name": get_element_name(element),
                "category": element.Category.Name if element.Category else "Unknown",
                "type": element.GetType().Name
            }

            # Get the element's bounding box
            try:
                element_bbox = element.get_BoundingBox(None)
                if element_bbox is None:
                    return routes.make_response(
                        data={"error": "No valid bounding box found for selected element"},
                        status=400,
                    )
            except Exception as e:
                return routes.make_response(
                    data={"error": "Failed to get bounding box for element: {}".format(str(e))},
                    status=400,
                )

            # Check each point pair against the bounding box
            results = []
            detailed_results = []
            
            for i, pair in enumerate(parsed_point_pairs):
                start_point = pair["start_point"]
                end_point = pair["end_point"]
                
                # Check if start point is inside bounding box
                start_inside = (
                    start_point.X >= element_bbox.Min.X and start_point.X <= element_bbox.Max.X and
                    start_point.Y >= element_bbox.Min.Y and start_point.Y <= element_bbox.Max.Y and
                    start_point.Z >= element_bbox.Min.Z and start_point.Z <= element_bbox.Max.Z
                )
                
                # Check if end point is inside bounding box
                end_inside = (
                    end_point.X >= element_bbox.Min.X and end_point.X <= element_bbox.Max.X and
                    end_point.Y >= element_bbox.Min.Y and end_point.Y <= element_bbox.Max.Y and
                    end_point.Z >= element_bbox.Min.Z and end_point.Z <= element_bbox.Max.Z
                )
                
                # Result is true if either start OR end point is inside
                pair_result = start_inside or end_inside
                results.append(pair_result)
                
                detailed_results.append({
                    "index": i,
                    "start_point": pair["original_start"],
                    "end_point": pair["original_end"],
                    "start_inside": start_inside,
                    "end_inside": end_inside,
                    "result": pair_result
                })

            # Prepare bounding box information (convert from feet to mm for response)
            bbox_info = {
                "min": {
                    "x": element_bbox.Min.X * FEET_TO_MM,
                    "y": element_bbox.Min.Y * FEET_TO_MM,
                    "z": element_bbox.Min.Z * FEET_TO_MM
                },
                "max": {
                    "x": element_bbox.Max.X * FEET_TO_MM,
                    "y": element_bbox.Max.Y * FEET_TO_MM,
                    "z": element_bbox.Max.Z * FEET_TO_MM
                },
                "center": {
                    "x": (element_bbox.Min.X + element_bbox.Max.X) / 2 * FEET_TO_MM,
                    "y": (element_bbox.Min.Y + element_bbox.Max.Y) / 2 * FEET_TO_MM,
                    "z": (element_bbox.Min.Z + element_bbox.Max.Z) / 2 * FEET_TO_MM
                },
                "dimensions": {
                    "width": (element_bbox.Max.X - element_bbox.Min.X) * FEET_TO_MM,
                    "depth": (element_bbox.Max.Y - element_bbox.Min.Y) * FEET_TO_MM,
                    "height": (element_bbox.Max.Z - element_bbox.Min.Z) * FEET_TO_MM
                },
                "transform_applied": not element_bbox.Transform.IsIdentity
            }

            # Prepare response
            result = {
                "message": "Batch point inside bounding box check completed successfully",
                "results": results,
                "detailed_results": detailed_results,
                "total_pairs": len(parsed_point_pairs),
                "pairs_inside": sum(results),
                "selected_count": 1,
                "bounding_box_info": bbox_info,
                "element": element_info
            }

            return routes.make_response(data=result, status=200)

        except Exception as e:
            error_msg = "Failed to check points inside bounding box: {}".format(str(e))
            logger.error(error_msg)
            logger.error("Traceback: %s", traceback.format_exc())
            
            return routes.make_response(
                data={
                    "error": error_msg,
                    "traceback": traceback.format_exc(),
                    "details": "Check the Revit logs for more information"
                },
                status=500,
            )

