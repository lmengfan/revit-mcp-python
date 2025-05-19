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
async def list_model_elements(ctx: Context) -> str:
    """
    Get a summary of elements in the active Revit model
    
    Returns:
        A summary of elements in the active Revit model, including project information,
        rooms, and key element categories
    """
    try:
        url = f"{BASE_URL}/model_info/"
        ctx.info(f"Connecting to: {url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            ctx.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                ctx.info("Received data from Revit")
                return data
            else:
                error_msg = f"Error from Revit API: {response.status_code} - {response.text}"
                ctx.error(error_msg)
                return error_msg
            
    except Exception as e:
        error_msg = f"Error connecting to Revit: {str(e)}"
        ctx.error(error_msg)
        return error_msg


@mcp.tool()
async def get_view(view_name: str, ctx: Context) -> Image:
    """
    Get a Revit View as an image
    
    Args:
        view_name: The name of the view to retrieve from Revit.
        ctx: The MCP context for logging and other operations
    
    Returns:
        An Image containing the Revit view, or an error message if the view cannot be retrieved.
    """
    try:
        url = f"{BASE_URL}/get_view/{view_name}"
        ctx.info(f"Requesting view: {view_name} from {url}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
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
async def place_family(
    family_type: str,
    location: Dict[str, float],
    rotation: float = 0.0,
    properties: Dict[str, Any] = None,
    ctx: Context = None
) -> str:
    """
    Place a family instance at a specified location in the Revit model
    
    Args:
        family_type: The family and type name to place (e.g., "Furniture:Chair")
        location: Dictionary with x, y, z coordinates in Revit's internal units
        rotation: The rotation angle in degrees (default: 0.0)
        properties: Dictionary of properties to set on the created element
        ctx: The MCP context for logging and other operations
    
    Returns:
        Information about the placed family or an error message
    """
    try:
        # Prepare the data for the Revit server
        data = {
            "family_type": family_type,
            "location": location,
            "rotation": rotation,
            "properties": properties or {}
        }
        
        url = f"{BASE_URL}/place_family/"
        ctx.info(f"Requesting to place family: {url}")
        ctx.debug(f"With data: {data}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url, 
                json=data,
                headers={"Content-Type": "application/json"}
            )
            ctx.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                ctx.info("Family placed successfully")
                return result
            else:
                error_msg = f"Error from Revit API: {response.status_code} - {response.text}"
                ctx.error(error_msg)
                return error_msg
            
    except Exception as e:
        error_msg = f"Error connecting to Revit: {str(e)}"
        ctx.error(error_msg)
        return error_msg


if __name__ == "__main__":
    mcp.run(transport="stdio")