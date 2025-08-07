# -*- coding: utf-8 -*-
"""API Mapping tools for Revit MCP Server"""

from mcp.server.fastmcp import Context
from .utils import format_response


def register_mapping_tools(mcp, revit_get):
    """Register API mapping tools"""

    @mcp.tool()
    async def get_mcp_to_http_mapping(ctx: Context = None) -> str:
        """
        Provides a comprehensive mapping between MCP tools and their corresponding HTTP API routes.

        This tool helps LLMs understand how to replicate MCP workflows using HTTP calls by providing:
        - Direct mapping between MCP tool names and HTTP endpoints
        - HTTP method and URL for each operation
        - Request body examples for HTTP calls
        - Response format information
        - Code examples for both MCP and HTTP usage

        Returns:
            dict: Complete mapping with examples and usage patterns
            
        Response Format:
            {
                "status": "success",
                "message": "MCP to HTTP API mapping",
                "data": {
                    "base_url": "http://localhost:48884",
                    "mappings": {
                        "mcp_tool_name": {
                            "http_method": "POST|GET|PUT|DELETE",
                            "http_endpoint": "/revit_mcp/endpoint",
                            "http_url": "http://localhost:48884/revit_mcp/endpoint",
                            "request_body": {...},
                            "mcp_example": "...",
                            "http_example": "..."
                        }
                    },
                    "workflow_examples": [...],
                    "common_patterns": {...}
                }
            }

        Usage:
            This tool is essential for LLMs to understand how to convert MCP-based workflows
            into HTTP API calls, enabling code generation and automation scripts.
        """
        if ctx:
            ctx.info("Retrieving MCP to HTTP API mapping information...")

        response = await revit_get("/mcp_to_http_mapping/", ctx)
        return format_response(response) 