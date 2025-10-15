# -*- coding: UTF-8 -*-
"""
ATF Management Module for Revit MCP
Handles ATF InteropModel creation, exchange URL management, and component hierarchy traversal
"""
import sys, clr, os, requests
from pyrevit import routes, revit, DB
from .utils import normalize_string, get_element_name
from .atf_component_models import (
    traverse_component_hierarchy, 
    get_component_ids_by_type,
    get_all_component_ids,
    _count_total_components,
    ComponentDefinition,
    ComponentInstance
)
from config_manager import ConfigManager
import json
import traceback
import logging

logger = logging.getLogger(__name__)

def import_atf_xlayer():
    """Import ATF.XLayer.dll with robust error handling"""
    dll_path = os.path.join(ConfigManager.get_env_variable("ATF_LIBRARY_PATH", r"D:\git\atf-poc\atf\x64\Bin\Release"), "ATF.XLayer.dll")
    dll_directory = os.path.dirname(dll_path)
    
    try:
        # Check if DLL exists
        if not os.path.exists(dll_path):
            raise Exception("ATF.XLayer.dll not found at: {}".format(dll_path))
        
        # Add directory to path for dependency resolution
        if dll_directory not in sys.path:
            sys.path.append(dll_directory)
        
        # Add reference to the DLL
        clr.AddReferenceToFileAndPath(dll_path)
        
        return True
        
    except Exception as ex:
        print("[ERROR] Failed to import ATF.XLayer.dll: {}".format(ex))
        print("[DEBUG] Error type: {}".format(type(ex).__name__))
        return False

# Initialize ATF.XLayer.dll import
atf_xlayer_loaded = import_atf_xlayer()

# Import namespaces after DLL is loaded
Models = None
Enums = None

if atf_xlayer_loaded:
    try:
        # Import the namespaces - adjust these based on actual DLL contents
        # Common patterns: ATF.XLayer, ATF.XLayer.Core, ATF.XLayer.Commands
        from ATF.XLayer import Models, Enums
        logger.info("Successfully imported ATF.XLayer namespaces: Models and Enums")
    except ImportError as import_ex:
        logger.warning("Could not import ATF.XLayer namespace: {}".format(import_ex))
        logger.info("You may need to adjust the namespace import based on the actual DLL structure")
        logger.info("ATF.XLayer DLL loaded but namespace import failed")
        atf_xlayer_loaded = False  # Mark as failed if namespace import fails
else:
    logger.error("ATF.XLayer import failed - some functionality may not be available")

def construct_exchange_url(exchange_id, base_url="https://developer-stg.api.autodesk.com/exchange/v1/exchanges?filters=attribute.exchangeFileUrn=="):
    """
    Construct the exchange URL from exchange ID
    
    Args:
        exchange_id (str): The exchange ID/URN to construct URL for
        base_url (str): Base URL for the exchange API
        
    Returns:
        str: Complete exchange URL
        
    Raises:
        ValueError: If exchange_id is not provided
    """
    if not exchange_id:
        raise ValueError("exchange_id is required")
    
    # Construct the URL
    url = "{}{}".format(base_url, exchange_id)
    return url


def create_interop_model():
    """
    Create and return an ATF InteropModel instance using ATF.XLayer
    
    Returns:
        InteropModel: ATF InteropModel instance or None if creation fails
    """
    try:
        if not atf_xlayer_loaded or Models is None:
            logger.error("ATF.XLayer not loaded or Models namespace not available - cannot create InteropModel")
            return None
            
        # Create InteropModel using ATF.XLayer
        model = Models.InteropModel.Create()
        logger.info("Successfully created ATF InteropModel")
        return model
            
    except Exception as ex:
        logger.error("Failed to create InteropModel: {}".format(ex))
        logger.error("Error type: {}".format(type(ex).__name__))
        return None


def get_exchange_parameters():
    """
    Get exchange parameters from configuration or environment variables
    
    This function retrieves the exchange ID/URN from various sources:
    - Environment variable ATF_EXCHANGE_URN
    - ConfigManager settings
    - Default fallback values
    
    Returns:
        str: Exchange ID/URN or None if not available
    """
    try:
        # Try to get from environment variable first
        exchange_urn = ConfigManager.get_env_variable("ATF_EXCHANGE_URN", None)
        if exchange_urn:
            logger.info("Found exchange URN from environment variable: {}".format(exchange_urn))
            return exchange_urn
        
        # Try to get from ConfigManager settings
        try:
            exchange_urn = ConfigManager.get_setting("atf_exchange_urn", None)
            if exchange_urn:
                logger.info("Found exchange URN from config settings: {}".format(exchange_urn))
                return exchange_urn
        except Exception as config_ex:
            logger.debug("Could not get exchange URN from config settings: {}".format(config_ex))
        
        # No exchange URN found
        logger.warning("No exchange URN found in environment variables or config settings")
        logger.info("Set ATF_EXCHANGE_URN environment variable or configure atf_exchange_urn setting")
        return None
        
    except Exception as e:
        logger.error("Failed to get exchange parameters: {}".format(str(e)))
        return None


def import_from_exchange_url(model, exchange_url):
    """
    Import data from exchange URL into the InteropModel using ATF.XLayer
    
    Args:
        model: InteropModel instance
        exchange_url (str): Complete exchange URL
        
    Returns:
        bool: True if import successful, False otherwise
    """
    try:
        if not model:
            logger.error("No InteropModel provided")
            return False
            
        if not exchange_url:
            logger.error("No exchange URL provided")
            return False
        
        if not atf_xlayer_loaded or Enums is None:
            logger.error("ATF.XLayer not loaded or Enums namespace not available - cannot import from exchange URL")
            return False
        
        # Import from exchange URL using ATF.XLayer
        logger.info("Importing from exchange URL: {}".format(exchange_url))
        model.ImportFromExchangeUrl(exchange_url, Enums.FileFormat.Dx)
        logger.info("Successfully imported from exchange URL")
        return True
        
    except Exception as e:
        logger.error("Failed to import from exchange URL: {}".format(str(e)))
        logger.error("Error type: {}".format(type(e).__name__))
        return False


def test_atf_integration():
    """
    Test function to verify ATF.XLayer integration is working
    
    Returns:
        dict: Test results with status and details
    """
    try:
        results = {
            "dll_loaded": atf_xlayer_loaded,
            "models_available": Models is not None,
            "enums_available": Enums is not None,
            "can_create_model": False,
            "error": None
        }
        
        if atf_xlayer_loaded and Models is not None:
            try:
                # Try to create a test model
                test_model = Models.InteropModel.Create()
                if test_model:
                    results["can_create_model"] = True
                    logger.info("ATF integration test passed - can create InteropModel")
                else:
                    results["error"] = "InteropModel.Create() returned None"
            except Exception as ex:
                results["error"] = "Failed to create test model: {}".format(str(ex))
        else:
            results["error"] = "ATF.XLayer not properly loaded or namespaces not available"
        
        return results
        
    except Exception as e:
        return {
            "dll_loaded": False,
            "models_available": False,
            "enums_available": False,
            "can_create_model": False,
            "error": "Test failed: {}".format(str(e))
        }


def get_all_component_instances_from_urn(urn):
    """
    Get all component instances from a particular URN
    
    This is the main function that implements the workflow you described.
    
    Args:
        urn (str): The URN to get instances from (e.g., "urn:adsk.wipstg:dm.lineage:FQVbQQouTiKcK27xRsECPg")
        
    Returns:
        dict: Results containing instances and metadata, or error information
    """
    try:
        logger.info("Getting component instances from URN: {}".format(urn))
        
        # Step 1: Create InteropModel
        try:
            model = create_interop_model()
        except Exception as ex:
            error_msg = "Failed to create InteropModel: {}".format(str(ex))
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "instances": [],
                "total_count": 0
            }
        
        if not model:
            error_msg = "Failed to create InteropModel"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "instances": [],
                "total_count": 0
            }
        
        # Step 2: Construct exchange URL
        try:
            exchange_url = construct_exchange_url(urn)
        except Exception as ex:
            error_msg = "Failed to construct exchange URL: {}".format(str(ex))
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "instances": [],
                "total_count": 0
            }
        
        if not exchange_url:
            error_msg = "Failed to construct exchange URL"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "instances": [],
                "total_count": 0
            }
        
        # Step 3: Import from exchange URL
        try:
            import_success = import_from_exchange_url(model, exchange_url)
            if not import_success:
                error_msg = "Failed to import from exchange URL"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "instances": [],
                    "total_count": 0
                }
        except Exception as ex:
            error_msg = "Failed to import from exchange URL: {}".format(str(ex))
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "instances": [],
                "total_count": 0
            }
        
        # Step 4: Get top component and traverse hierarchy
        try:
            # Get top component definition using ATF.XLayer
            logger.info("Getting top component definition from model")
            topComponentObject = model.GetTopComponentDefinition()
            
            if not topComponentObject:
                error_msg = "Failed to get top component definition - no top component found"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "instances": [],
                    "total_count": 0
                }
            
            logger.info("Successfully got top component definition, starting hierarchy traversal")
            traversal_results = traverse_component_hierarchy(model, topComponentObject)
        except Exception as ex:
            error_msg = "Failed to traverse component hierarchy: {}".format(str(ex))
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "instances": [],
                "total_count": 0
            }
        
        if not traversal_results:
            error_msg = "Failed to traverse component hierarchy"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "instances": [],
                "total_count": 0
            }
        
        if traversal_results.get("error"):
            error_msg = "Component traversal failed: {}".format(traversal_results.get("error"))
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "instances": [],
                "total_count": 0
            }
        
        # Step 5: Extract component instances
        try:
            all_component_instances = get_component_ids_by_type(traversal_results)
            all_instances = all_component_instances.get("instances", [])
            
            # Convert ComponentInstance objects to dictionaries for JSON serialization
            serializable_instances = []
            for instance in all_instances:
                if hasattr(instance, 'to_dict'):
                    serializable_instances.append(instance.to_dict())
                else:
                    # Fallback for objects without to_dict method
                    logger.warning("Instance {} does not have to_dict method, using basic serialization".format(instance))
                    serializable_instances.append({
                        "id": getattr(instance, 'id', None),
                        "label": getattr(instance, 'label', None),
                        "type": getattr(instance, 'type', None),
                        "componentDefinitionId": getattr(instance, 'component_definition_id', None)
                    })
            
            # Get component counts for statistics
            component_counts = _count_total_components(traversal_results)
            
            logger.info("Successfully retrieved {} component instances from URN".format(len(serializable_instances)))
            
            # Create response with only JSON-serializable data
            response = {
                "success": True,
                "message": "Successfully retrieved component instances from URN: {}".format(urn),
                "urn": urn,
                "instances": serializable_instances,
                "total_count": len(serializable_instances),
                "statistics": {
                    "total_components": component_counts.get("total", 0),
                    "component_definitions": component_counts.get("definitions", 0),
                    "component_instances": component_counts.get("instances", 0)
                },
                "traversal_depth": traversal_results.get("depth", 0) if traversal_results.get("depth") is not None else 0
            }
            
            # Log response structure for debugging
            logger.debug("Response structure: {}".format(type(response)))
            logger.debug("Response keys: {}".format(response.keys()))
            
            return response
            
        except Exception as ex:
            error_msg = "Failed to extract component instances: {}".format(str(ex))
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "instances": [],
                "total_count": 0
            }
        
    except Exception as e:
        error_msg = "Unexpected error getting component instances from URN: {}".format(str(e))
        logger.error(error_msg)
        logger.error("Traceback: {}".format(traceback.format_exc()))
        return {
            "success": False,
            "error": error_msg,
            "instances": [],
            "total_count": 0
        }


def register_atf_management_routes(api):
    """Register all ATF management routes with the API"""

    @api.route("/get_component_instances_from_urn/", methods=["POST"])
    @api.route("/get_component_instances_from_urn", methods=["POST"])
    def get_component_instances_from_urn_route(doc, request):
        """
        Get all component instances from a particular URN
        
        Expected request data:
        {
            "urn": "urn:adsk.wipstg:dm.lineage:FQVbQQouTiKcK27xRsECPg"
        }
        
        Returns:
        {
            "success": true/false,
            "message": "Success/error message",
            "urn": "provided URN",
            "instances": [array of ComponentInstance objects],
            "total_count": number,
            "statistics": {
                "total_components": number,
                "component_definitions": number,
                "component_instances": number
            },
            "traversal_depth": number
        }
        """
        try:
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

            # Extract URN
            urn = data.get("urn")
            if not urn:
                return routes.make_response(
                    data={"error": "URN is required"}, status=400
                )

            # Get component instances
            result = get_all_component_instances_from_urn(urn)
            
            if result.get("success"):
                return routes.make_response(data=result, status=200)
            else:
                return routes.make_response(
                    data=result, status=500
                )

        except Exception as e:
            logger.error("Failed to get component instances from URN: {}".format(str(e)))
            logger.error("Traceback: {}".format(traceback.format_exc()))
            return routes.make_response(
                data={
                    "success": False,
                    "error": "Failed to get component instances from URN: {}".format(str(e)),
                    "instances": [],
                    "total_count": 0
                },
                status=500,
            )

    @api.route("/construct_exchange_url/", methods=["POST"])
    @api.route("/construct_exchange_url", methods=["POST"])
    def construct_exchange_url_route(doc, request):
        """
        Construct exchange URL from URN/exchange ID
        
        Expected request data:
        {
            "exchange_id": "urn:adsk.wipstg:dm.lineage:FQVbQQouTiKcK27xRsECPg",
            "base_url": "https://developer-stg.api.autodesk.com/exchange/v1/exchanges?filters=attribute.exchangeFileUrn=="  // Optional
        }
        
        Returns:
        {
            "success": true/false,
            "message": "Success/error message", 
            "exchange_id": "provided exchange ID",
            "exchange_url": "constructed URL",
            "base_url": "base URL used"
        }
        """
        try:
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
            exchange_id = data.get("exchange_id")
            base_url = data.get("base_url")
            
            if not exchange_id:
                return routes.make_response(
                    data={"error": "exchange_id is required"}, status=400
                )

            # Construct URL
            try:
                if base_url:
                    exchange_url = construct_exchange_url(exchange_id, base_url)
                else:
                    exchange_url = construct_exchange_url(exchange_id)
                    base_url = "https://developer-stg.api.autodesk.com/exchange/v1/exchanges?filters=attribute.exchangeFileUrn=="
                
                return routes.make_response(
                    data={
                        "success": True,
                        "message": "Successfully constructed exchange URL",
                        "exchange_id": exchange_id,
                        "exchange_url": exchange_url,
                        "base_url": base_url
                    },
                    status=200
                )
                
            except ValueError as ve:
                return routes.make_response(
                    data={
                        "success": False,
                        "error": str(ve)
                    },
                    status=400
                )

        except Exception as e:
            logger.error("Failed to construct exchange URL: {}".format(str(e)))
            return routes.make_response(
                data={
                    "success": False,
                    "error": "Failed to construct exchange URL: {}".format(str(e))
                },
                status=500,
            )

    @api.route("/test_atf_integration/", methods=["GET"])
    @api.route("/test_atf_integration", methods=["GET"])
    def test_atf_integration_route(doc, request):
        """
        Test ATF.XLayer integration and return status
        
        Returns:
        {
            "dll_loaded": true/false,
            "models_available": true/false,
            "enums_available": true/false,
            "can_create_model": true/false,
            "error": "error message or null"
        }
        """
        try:
            test_results = test_atf_integration()
            return routes.make_response(data=test_results, status=200)
            
        except Exception as e:
            logger.error("Failed to test ATF integration: {}".format(str(e)))
            return routes.make_response(
                data={
                    "dll_loaded": False,
                    "models_available": False,
                    "enums_available": False,
                    "can_create_model": False,
                    "error": "Test failed: {}".format(str(e))
                },
                status=500
            )

    logger.info("ATF management routes registered successfully")
