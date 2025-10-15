#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python equivalent of the C# Connector.cs token commands

This module provides the same token management commands as the C# version:
- GetToken: Get APS access token for authentication
- ClearToken: Clear stored authentication token
- CheckToken: Check current token status and validity

These commands can be used standalone or integrated into larger applications.
Python 2.7 compatible version without asyncio.
"""

import sys
from datetime import datetime

from config_manager import ConfigManager
from oauth_util import OAuthUtil
import token_util
import requests


class ConnectorCommands(object):
    """
    Python equivalent of the C# Connector class
    
    Provides token management commands that mirror the C# implementation
    """
    
    def __init__(self):
        """Initialize connector commands"""
        self._initialized = False
    
    def initialize(self):
        """Initialize the connector - equivalent to C# InitializeDocumentContext"""
        try:
            # Load configuration
            ConfigManager.load_configuration()
            
            # Validate required configuration
            missing_keys = ConfigManager.validate_required_configuration()
            if missing_keys:
                print("[ERROR] Failed to initialize - missing required configuration")
                print("Missing keys: {}".format(', '.join(missing_keys)))
                print("Please check your .env file or environment variables.")
                print("Refer to config/SETUP_GUIDE.md for setup instructions.")
                return False
            
            self._initialized = True
            return True
            
        except Exception as ex:
            print("[ERROR] Error initializing connector: {}".format(ex))
            return False
    
    def _ensure_initialized(self):
        """Ensure connector is initialized"""
        if not self._initialized:
            return self.initialize()
        return True
    
    def get_access_token_cmd(self):
        """
        Command to get APS access token for authentication
        
        Python equivalent of GetAccessTokenCmd() in C#
        """
        if not self._ensure_initialized():
            return  # Exit if initialization failed
        
        token_util.handle_get_token_command()
    
    def clear_token_cmd(self):
        """
        Command to clear stored authentication token
        
        Python equivalent of ClearTokenCmd() in C#
        """
        if not self._ensure_initialized():
            return  # Exit if initialization failed
        
        token_util.handle_clear_token_command()
    
    def check_token_cmd(self):
        """
        Command to check current token status and validity
        
        Python equivalent of CheckTokenCmd() in C#
        """
        if not self._ensure_initialized():
            return  # Exit if initialization failed
        
        token_util.handle_check_token_command()
    
    def get_valid_token_for_export(self):
        """
        Get a valid APS access token for data exchange export operations.
        This replicates the token validation logic from C# CreateDataExchangeBySelectionCmd.
        
        Returns:
            Valid access token string, or None if failed
        """
        try:
            print("[TOKEN] Checking APS access token for DX export...")
            
            # Check if we have a current valid token
            current_token = OAuthUtil.get_current_token()
            
            if current_token and not current_token.is_expired:
                print("[OK] Using existing valid token.")
                return current_token.access_token
            
            if current_token and current_token.is_expired:
                print("[WARNING]  Current token is expired. Getting new token...")
            else:
                print("[INFO] No token found. Getting new token...")
            
            # Validate OAuth configuration
            if not OAuthUtil.validate_environment_configuration():
                print("[ERROR] OAuth configuration validation failed.")
                print("[TIP] Please run get_token command first to authenticate.")
                return None
            
            print("[NETWORK] Starting authentication flow...")
            access_token = OAuthUtil.get_3_legged_token_from_environment()
            print("[OK] Token obtained successfully.")
            
            return access_token
            
        except KeyboardInterrupt:
            print("[WARNING]  Authentication cancelled by user.")
            return None
        except ValueError as ex:
            print("[ERROR] Configuration error: {}".format(ex))
            print("[TIP] Please check your .env file and run connector test first.")
            return None
        except requests.HTTPError as ex:
            print("[ERROR] Network error during token retrieval: {}".format(ex))
            return None
        except Exception as ex:
            print("[ERROR] Unexpected error during token retrieval: {}".format(ex))
            print("[DEBUG] Error type: {}".format(type(ex).__name__))
            
            # Show inner exception if available
            if hasattr(ex, '__cause__') and ex.__cause__:
                print("[DEBUG] Inner error: {}".format(ex.__cause__))
            return None


class AsyncCommandWrapper(object):
    """
    Wrapper to handle async commands in sync contexts
    
    This allows async commands to be called from synchronous code
    """
    
    def __init__(self):
        """Initialize wrapper"""
        self.connector = ConnectorCommands()
    
    def get_token(self):
        """Synchronous wrapper for get_token command"""
        self.connector.get_access_token_cmd()
    
    def clear_token(self):
        """Synchronous wrapper for clear_token command"""
        self.connector.clear_token_cmd()
    
    def check_token(self):
        """Synchronous wrapper for check_token command"""
        self.connector.check_token_cmd()
    
    def get_valid_token_for_export(self):
        """Synchronous wrapper for get_valid_token_for_export command"""
        return self.connector.get_valid_token_for_export()


# Global connector instance factory functions
def get_connector():
    """
    Get a ConnectorCommands instance
    
    Returns:
        ConnectorCommands instance
    """
    return ConnectorCommands()


def get_wrapper():
    """
    Get an AsyncCommandWrapper instance
    
    Returns:
        AsyncCommandWrapper instance
    """
    return AsyncCommandWrapper()


# Direct command functions that match C# CommandMethod names
# These provide the exact same interface as the C# version

def GetToken():
    """Python equivalent of [CommandMethod("GetToken")]"""
    connector = get_connector()
    connector.get_access_token_cmd()


def ClearToken():
    """Python equivalent of [CommandMethod("ClearToken")]"""
    connector = get_connector()
    connector.clear_token_cmd()


def CheckToken():
    """Python equivalent of [CommandMethod("CheckToken")]"""
    connector = get_connector()
    connector.check_token_cmd()


def GetTokenSync():
    """Synchronous version of GetToken command"""
    GetToken()


def ClearTokenSync():
    """Synchronous version of ClearToken command"""
    ClearToken()


def CheckTokenSync():
    """Synchronous version of CheckToken command"""
    CheckToken()


def GetValidTokenForExport():
    """
    Get valid token for export operations
    
    Python equivalent of the token validation logic in CreateDataExchangeBySelectionCmd
    
    Returns:
        Valid access token string, or None if failed
    """
    connector = get_connector()
    return connector.get_valid_token_for_export()


# Command registry for CLI usage
COMMANDS = {
    'GetToken': GetToken,
    'ClearToken': ClearToken, 
    'CheckToken': CheckToken,
    'GetTokenSync': GetTokenSync,
    'ClearTokenSync': ClearTokenSync,
    'CheckTokenSync': CheckTokenSync,
    'GetValidTokenForExport': GetValidTokenForExport,
    
    # Aliases
    'get_token': GetToken,
    'clear_token': ClearToken,
    'check_token': CheckToken,
    'get_valid_token_for_export': GetValidTokenForExport
}


def list_commands():
    """List all available commands"""
    print("Available Commands:")
    print("==================")
    for cmd_name in sorted(COMMANDS.keys()):
        if not cmd_name.startswith('_'):  # Skip private commands
            print("  {}".format(cmd_name))


def run_command(command_name):
    """
    Run a command by name
    
    Args:
        command_name: Name of the command to run
        
    Returns:
        True if command executed successfully, False otherwise
    """
    if command_name in COMMANDS:
        try:
            result = COMMANDS[command_name]()
            return True
        except KeyboardInterrupt:
            print("[WARNING] Command interrupted by user")
            return False
        except Exception as ex:
            print("[ERROR] Command failed: {}".format(ex))
            print("[DEBUG] Error type: {}".format(type(ex).__name__))
            return False
    else:
        print("[ERROR] Unknown command: {}".format(command_name))
        return False


# Main function for CLI usage
def main():
    """Main function for command-line usage"""
    if len(sys.argv) < 2:
        print("Usage: python connector_commands.py <command>")
        list_commands()
        return
    
    command = sys.argv[1]
    
    # Run the command
    try:
        success = run_command(command)
        
        if success:
            print("[OK] Command completed successfully")
        else:
            print("\n[WARNING]  Command interrupted by user")
    except KeyboardInterrupt:
        print("\n[WARNING]  Command interrupted by user")
    except Exception as ex:
        print("\n[ERROR] Command failed: {}".format(ex))
        print("[DEBUG] Error type: {}".format(type(ex).__name__))


if __name__ == "__main__":
    main() 