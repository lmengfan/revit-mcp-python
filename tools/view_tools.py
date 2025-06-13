"""View-related tools for capturing and listing Revit views"""

from mcp.server.fastmcp import Context


def register_view_tools(mcp, revit_get, revit_image):
    """Register view-related tools"""
    
    @mcp.tool()
    async def get_revit_view(view_name: str, ctx: Context = None) -> str:
        """Export a specific Revit view as an image"""
        return await revit_image(f"/get_view/{view_name}", ctx)

    @mcp.tool()
    async def list_revit_views(ctx: Context = None) -> str:
        """Get a list of all exportable views in the current Revit model"""
        return await revit_get("/list_views/", ctx)