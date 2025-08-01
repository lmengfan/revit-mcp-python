# -*- coding: utf-8 -*-
import httpx
from mcp.server.fastmcp import FastMCP, Image, Context
import base64
from typing import Optional, Dict, Any, Union

# Create a generic MCP server for interacting with Revit
mcp = FastMCP("Revit MCP Server")

# Configuration
REVIT_HOST = "localhost"
REVIT_PORT = 48884  # Default pyRevit Routes port
BASE_URL = "http://{}:{}/revit_mcp".format(REVIT_HOST, REVIT_PORT)


async def revit_get(endpoint: str, ctx: Context = None, **kwargs) -> Union[Dict, str]:
    """Simple GET request to Revit API"""
    return await _revit_call("GET", endpoint, ctx=ctx, **kwargs)


async def revit_post(endpoint: str, data: Dict[str, Any], ctx: Context = None, **kwargs) -> Union[Dict, str]:
    """Simple POST request to Revit API"""
    return await _revit_call("POST", endpoint, data=data, ctx=ctx, **kwargs)


async def revit_image(endpoint: str, ctx: Context = None) -> Union[Image, str]:
    """GET request that returns an Image object"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get("{}{}".format(BASE_URL, endpoint))
            
            if response.status_code == 200:
                data = response.json()
                image_bytes = base64.b64decode(data["image_data"])
                return Image(data=image_bytes, format="png")
            else:
                return "Error: {} - {}".format(response.status_code, response.text)
    except Exception as e:
        return "Error: {}".format(e)


async def _revit_call(method: str, endpoint: str, data: Dict = None, ctx: Context = None, 
                     timeout: float = 30.0, params: Dict = None) -> Union[Dict, str]:
    """Internal function handling all HTTP calls"""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            url = "{}{}".format(BASE_URL, endpoint)
            
            if method == "GET":
                response = await client.get(url, params=params)
            else:  # POST
                response = await client.post(url, json=data, headers={"Content-Type": "application/json"})
            
            return response.json() if response.status_code == 200 else "Error: {} - {}".format(response.status_code, response.text)
    except Exception as e:
        return "Error: {}".format(e)


# Register all tools BEFORE the main block
from tools import register_tools
register_tools(mcp, revit_get, revit_post, revit_image)


if __name__ == "__main__":
    mcp.run(transport="stdio")