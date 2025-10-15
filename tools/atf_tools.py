# -*- coding: utf-8 -*-
"""ATF management tools for the MCP server."""

from mcp.server.fastmcp import Context
from typing import Dict, Any
from .utils import format_response


def register_atf_tools(mcp, revit_get, revit_post):
    """Register ATF management tools with the MCP server."""

    @mcp.tool()
    async def get_component_instances_from_urn(
        urn: str,
        ctx: Context = None,
    ) -> str:
        """
        Get all component instances from a particular URN using ATF InteropModel.
        
        This tool implements a complete workflow to:
        1. Create an ATF InteropModel
        2. Construct exchange URL from the provided URN  
        3. Import data from the exchange URL
        4. Traverse the component hierarchy to find all instances
        5. Return structured information about all ComponentInstance objects found
        
        The workflow handles ATF component models including ComponentDefinition and 
        ComponentInstance objects, with full hierarchy traversal and cycle detection.
        
        Args:
            urn: The URN to get instances from (required)
                 Example: "urn:adsk.wipstg:dm.lineage:FQVbQQouTiKcK27xRsECPg"
            ctx: MCP context for logging
            
        Returns:
            JSON response with component instances and metadata
            
        Response Format:
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
            
        Examples:
            # Get all instances from a specific URN
            result = get_component_instances_from_urn(
                "urn:adsk.wipstg:dm.lineage:FQVbQQouTiKcK27xRsECPg"
            )
            
            # Process the results
            if result["success"]:
                instances = result["instances"]
                print(f"Found {result['total_count']} component instances")
                for instance in instances:
                    print(f"Instance ID: {instance.id}, Label: {instance.label}")
            
        Usage Tips:
            - The URN should be a valid Autodesk exchange URN
            - The tool handles the complete ATF workflow automatically
            - Results include both raw instances and statistical information
            - Component hierarchy is traversed with cycle detection for safety
            - All ComponentInstance objects are extracted from the hierarchy
        """
        if ctx:
            await ctx.info(f"Getting component instances from URN: {urn}")
            
        # Prepare request data
        request_data = {
            "urn": urn
        }
        
        # Make API call to get component instances
        response = await revit_post("/get_component_instances_from_urn/", request_data, ctx)
        return format_response(response)

    @mcp.tool()
    async def construct_exchange_url(
        exchange_id: str,
        base_url: str = None,
        ctx: Context = None,
    ) -> str:
        """
        Construct exchange URL from URN/exchange ID.
        
        This utility tool constructs the complete exchange URL needed for ATF
        InteropModel.ImportFromExchangeUrl() operations. It combines the base
        exchange API URL with the specific exchange ID/URN.
        
        Args:
            exchange_id: The exchange ID/URN to construct URL for (required)
                        Example: "urn:adsk.wipstg:dm.lineage:FQVbQQouTiKcK27xRsECPg"
            base_url: Custom base URL for the exchange API (optional)
                     Default: "https://developer-stg.api.autodesk.com/exchange/v1/exchanges?filters=attribute.exchangeFileUrn=="
            ctx: MCP context for logging
            
        Returns:
            JSON response with constructed URL information
            
        Response Format:
            {
                "success": true/false,
                "message": "Success/error message",
                "exchange_id": "provided exchange ID",
                "exchange_url": "constructed URL", 
                "base_url": "base URL used"
            }
            
        Examples:
            # Construct URL with default base URL
            result = construct_exchange_url(
                "urn:adsk.wipstg:dm.lineage:FQVbQQouTiKcK27xRsECPg"
            )
            
            # Construct URL with custom base URL
            result = construct_exchange_url(
                exchange_id="urn:adsk.wipstg:dm.lineage:FQVbQQouTiKcK27xRsECPg",
                base_url="https://custom-api.autodesk.com/exchange/v1/exchanges?filters=attribute.exchangeFileUrn=="
            )
            
            # Use the constructed URL
            if result["success"]:
                exchange_url = result["exchange_url"]
                print(f"Exchange URL: {exchange_url}")
            
        Usage Tips:
            - The exchange_id should be a valid Autodesk URN or exchange identifier
            - The default base_url points to the staging environment
            - Use this tool to prepare URLs before calling ATF import operations
            - The constructed URL can be used directly with InteropModel.ImportFromExchangeUrl()
        """
        if ctx:
            await ctx.info(f"Constructing exchange URL for: {exchange_id}")
            
        # Prepare request data
        request_data = {
            "exchange_id": exchange_id
        }
        
        # Add base_url if provided
        if base_url:
            request_data["base_url"] = base_url
        
        # Make API call to construct exchange URL
        response = await revit_post("/construct_exchange_url/", request_data, ctx)
        return format_response(response)

    @mcp.tool()
    async def test_atf_integration(
        ctx: Context = None,
    ) -> str:
        """
        Test ATF.XLayer integration and return status information.
        
        This diagnostic tool checks if the ATF.XLayer DLL is properly loaded
        and if the necessary namespaces (Models, Enums) are available for
        creating InteropModel instances.
        
        Args:
            ctx: MCP context for logging
            
        Returns:
            JSON response with integration test results
            
        Response Format:
            {
                "dll_loaded": true/false,
                "models_available": true/false, 
                "enums_available": true/false,
                "can_create_model": true/false,
                "error": "error message or null"
            }
            
        Examples:
            # Test ATF integration
            result = test_atf_integration()
            
            # Check if ATF is ready to use
            if result["dll_loaded"] and result["can_create_model"]:
                print("ATF integration is working properly")
            else:
                print(f"ATF integration issue: {result['error']}")
            
        Usage Tips:
            - Run this test before attempting to use ATF functionality
            - Use this to diagnose ATF.XLayer DLL loading issues
            - Check the error message for specific integration problems
            - Ensure ATF_LIBRARY_PATH environment variable is set correctly
        """
        if ctx:
            await ctx.info("Testing ATF.XLayer integration...")
            
        # Make API call to test ATF integration
        response = await revit_get("/test_atf_integration/", ctx)
        return format_response(response)
