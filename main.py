import httpx
from mcp.server.fastmcp import FastMCP, Image, Context
import json
import base64
from typing import Optional, Dict, Any, List, Union


# Create a generic MCP server for interacting with Revit
mcp = FastMCP("Revit MCP Server")

# Configuration
REVIT_HOST = "localhost"
REVIT_PORT = 48884  # Default pyRevit Routes port
BASE_URL = f"http://{REVIT_HOST}:{REVIT_PORT}/revit_mcp"


@mcp.tool()
async def get_revit_status(ctx: Context) -> str:
    """
    Check if the Revit MCP API is active and responding
    
    Returns:
        Status information about the Revit MCP API connection
    """
    try:
        url = f"{BASE_URL}/status/"
        ctx.info(f"Checking Revit API status at: {url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                return f"Error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Error connecting to Revit: {str(e)}"


@mcp.tool()
async def get_revit_model_info(ctx: Context) -> str:
    """
    Get comprehensive information about the current Revit model
    
    This tool provides model information including:
    - Project details (name, number, client)
    - Element counts by major architectural categories
    - Model health indicators (warnings, unplaced rooms)
    - Spatial organization (levels, rooms with areas)
    - Documentation status (views, sheets)
    - Linked model information
    
    Returns:
        Detailed JSON information about the Revit model structure and contents
    """
    try:
        url = f"{BASE_URL}/model_info/"
        ctx.info("Retrieving comprehensive Revit model information")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"Error: {response.status_code} - {response.text}"
                ctx.error(error_msg)
                return error_msg
                
    except Exception as e:
        error_msg = f"Error connecting to Revit: {str(e)}"
        ctx.error(error_msg)
        return error_msg
    

@mcp.tool()
async def get_revit_view(
    view_name: str,
    ctx: Context = None
) -> str:
    """
    Export a specific Revit view as an image
    
    Args:
        view_name: The exact name of the view to export (case-sensitive)
        ctx: MCP context for logging
        
    Returns:
        Base64 encoded PNG image data of the specified view, or error message
    """
    try:
        url = f"{BASE_URL}/get_view/{view_name}"
        ctx.info(f"Exporting Revit view: {view_name}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for image export
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                ctx.info("Successfully retrieved view")
                
                # Convert base64 string to bytes
                image_bytes = base64.b64decode(data["image_data"])
                
                # Return MCP Image object
                return Image(data=image_bytes, format="png")
            else:
                error_msg = f"Error retrieving view: {response.status_code} - {response.text}"
                ctx.error(error_msg)
                return error_msg
                
    except Exception as e:
        error_msg = f"Error connecting to Revit: {str(e)}"
        ctx.error(error_msg)
        return error_msg


@mcp.tool()
async def list_revit_views(ctx: Context = None) -> str:
    """
    Get a list of all exportable views in the current Revit model
    
    Returns:
        Dictionary containing all available views organized by type
        (floor plans, elevations, sections, 3D views, etc.)
    """
    try:
        url = f"{BASE_URL}/list_views/"
        ctx.info("Retrieving list of available Revit views")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                result = response.json()
                total_views = result.get("total_exportable_views", 0)
                ctx.info(f"Found {total_views} exportable views")
                return result
            else:
                error_msg = f"Error: {response.status_code} - {response.text}"
                ctx.error(error_msg)
                return error_msg
                
    except Exception as e:
        error_msg = f"Error connecting to Revit: {str(e)}"
        ctx.error(error_msg)
        return error_msg

@mcp.tool()
async def place_family(
    family_name: str,
    type_name: str = None,
    x: float = 0.0,
    y: float = 0.0, 
    z: float = 0.0,
    rotation: float = 0.0,
    level_name: str = None,
    properties: Dict[str, Any] = None,
    ctx: Context = None
    ) -> str:
    """
    Place a family instance at a specified location in the Revit model
    
    Args:
        family_name: Name of the family to place
        type_name: Specific type/size of the family (optional)
        x: X coordinate for placement
        y: Y coordinate for placement
        z: Z coordinate for placement (elevation)
        rotation: Rotation in degrees (optional)
        level_name: Name of the level to place on (optional)
        properties: Dictionary of parameter values to set (optional)
        ctx: MCP context for logging
        
    Returns:
        Success message with placement details or error information
    """
    try:
        data = {
            "family_name": family_name,
            "type_name": type_name,
            "location": {"x": x, "y": y, "z": z},
            "rotation": rotation,
            "level_name": level_name,
            "properties": properties or {}
        }
        
        url = f"{BASE_URL}/place_family/"
        ctx.info(f"Placing family: {family_name} - {type_name or 'Default Type'}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                ctx.info("Family placed successfully")
                return result
            else:
                error_msg = f"Error: {response.status_code} - {response.text}"
                ctx.error(error_msg)
                return error_msg
                
    except Exception as e:
        error_msg = f"Error connecting to Revit: {str(e)}"
        ctx.error(error_msg)
        return error_msg


@mcp.tool()
async def list_families(
    contains: str = None,
    limit: int = 50,
    ctx: Context = None
) -> str:
    """
    Get a flat list of up to 50 available family types in the current Revit model.
    Args:
        contains: Only include families containing this text (case-insensitive)
        limit: Maximum number of family types to return (default: 50)
        ctx: MCP context for logging
    Returns:
        List of families with their type, category, and activation status
    """
    try:
        params = {}
        if contains:
            params["contains"] = contains
        if limit != 50:
            params["limit"] = str(limit)
        url = f"{BASE_URL}/list_families/"
        filter_text = f"containing '{contains}'" if contains else "no filters"
        ctx.info(f"Retrieving up to {limit} families {filter_text}")
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, params=params)
            if response.status_code == 200:
                result = response.json()
                families = result.get("families", [])
                ctx.info(f"Found {len(families)} families")
                return families
            else:
                error_msg = f"Error: {response.status_code} - {response.text}"
                ctx.error(error_msg)
                return error_msg
    except Exception as e:
        error_msg = f"Error connecting to Revit: {str(e)}"
        ctx.error(error_msg)
        return error_msg
    

@mcp.tool()
async def list_family_categories(ctx: Context = None) -> str:
    """
    Get a list of all family categories in the current Revit model
    This helps users know what categories are available for filtering
    
    Returns:
        Dictionary containing all family categories with counts
    """
    try:
        url = f"{BASE_URL}/list_family_categories/"
        ctx.info("Retrieving list of family categories")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                result = response.json()
                total_categories = result.get("total_categories", 0)
                ctx.info(f"Found {total_categories} family categories")
                return result
            else:
                error_msg = f"Error: {response.status_code} - {response.text}"
                ctx.error(error_msg)
                return error_msg
                
    except Exception as e:
        error_msg = f"Error connecting to Revit: {str(e)}"
        ctx.error(error_msg)
        return error_msg


@mcp.tool()
async def list_levels(ctx: Context = None) -> str:
    """
    Get a list of all levels in the current Revit model
    
    Returns:
        Dictionary containing all available levels with their elevations
    """
    try:
        url = f"{BASE_URL}/list_levels/"
        ctx.info("Retrieving list of available levels")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                result = response.json()
                total_levels = result.get("total_levels", 0)
                ctx.info(f"Found {total_levels} levels")
                return result
            else:
                error_msg = f"Error: {response.status_code} - {response.text}"
                ctx.error(error_msg)
                return error_msg
                
    except Exception as e:
        error_msg = f"Error connecting to Revit: {str(e)}"
        ctx.error(error_msg)
        return error_msg
    


if __name__ == "__main__":
    mcp.run(transport="stdio")