# -*- coding: UTF-8 -*-
"""
MCP Module for Revit Integration
Contains all MCP route handlers organized by functionality
"""

__version__ = "0.1.0"
__author__ = "Simple Revit MCP"

# Common imports that all modules might need
from pyrevit import routes, revit, DB
import logging

# Make logger available to all submodules
logger = logging.getLogger(__name__)