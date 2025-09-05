# -*- coding: utf-8 -*-
"""Status and model information tools"""

from math import nextafter
from mcp.server.fastmcp import Context
from .utils import format_response


def register_status_tools(mcp, revit_get):
    """Register status-related tools"""

    @mcp.tool()
    async def get_revit_status(ctx: Context) -> str:
        """Check if the Revit MCP API is active and responding"""
        response = await revit_get("/status/", ctx, timeout=10.0)
        return format_response(response)

    @mcp.tool()
    async def get_revit_model_info(ctx: Context) -> str:
        """Get comprehensive information about the current Revit model"""
        response = await revit_get("/model_info/", ctx)
        return format_response(response)

    @mcp.tool()
    async def get_http_base_url(ctx: Context) -> str:
        """Get the HTTP base URL for the Revit MCP server"""
        try:  
            base_url = "http://localhost:48884"
            host = "localhost"
            port = 48884
            
            return {
                "status": "success",
                "message": "HTTP base URL retrieved successfully",
                "data": {
                    "base_url": base_url,
                    "host": host,
                    "port": port,
                    "protocol": "http",
                    "usage_note": "Use this base URL to construct HTTP requests to the Tekla API endpoints",
                }
            }
        
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Failed to get HTTP base URL: {str(e)}",
                "data": None
            }
