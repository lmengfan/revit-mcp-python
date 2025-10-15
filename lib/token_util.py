#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Token utility functions for handling APS authentication commands

Python 2.7 compatible version without asyncio
"""

from datetime import datetime, timedelta

import requests

from oauth_util import OAuthUtil
from oauth_models import TokenResponse
from config_manager import ConfigManager


def handle_get_token_command():
    """
    Handle the GetToken command - authenticate and get access token
    """
    try:
        # Validate environment configuration first
        if not OAuthUtil.validate_environment_configuration():
            print("[ERROR] Configuration validation failed. Please check your setup.")
            print("Refer to config/SETUP_GUIDE.md for detailed setup instructions.")
            return
        
        print("[OK] Configuration validated successfully.")
        print("Starting OAuth 3-legged authentication flow...")
        print("[NOTE] A browser will open for you to log in to Autodesk Platform Services.")
        
        # Get access token using 3-legged OAuth flow
        access_token = OAuthUtil.get_3_legged_token_from_environment()
        
        if access_token:
            print("[SUCCESS] Authentication successful!")
            print("[OK] Access token obtained: {}...".format(access_token[:min(20, len(access_token))]))
            
            # Show token details
            current_token = OAuthUtil.get_current_token()
            if current_token:
                print("[DATE] Token expires at: {} UTC".format(current_token.expires_at))
                print("[SECURE] Token type: {}".format(current_token.token_type))
                print("[TARGET] Scopes: {}".format(current_token.scope))
                
                # Show time until expiry
                if current_token.expires_at:
                    time_until_expiry = current_token.expires_at - datetime.utcnow()
                    if time_until_expiry.total_seconds() > 3600:
                        print("[TIME]  Token valid for: {:.1f} hours".format(time_until_expiry.total_seconds() / 3600))
                    else:
                        print("[TIME]  Token valid for: {:.1f} minutes".format(time_until_expiry.total_seconds() / 60))
                
                print("[TIP] Token is now stored and ready for use in other commands.")
                print("[TIP] You can use this token to make authenticated API calls to Autodesk Platform Services.")
        else:
            print("[ERROR] Failed to obtain access token.")
            
    except KeyboardInterrupt:
        print("[WARNING]  Authentication cancelled by user.")
    except ValueError as ex:
        print("[ERROR] Configuration error: {}".format(ex))
        print("[TIP] Please check your .env file or environment variables.")
        print("[TIP] Refer to config/SETUP_GUIDE.md for setup instructions.")
    except requests.HTTPError as ex:
        print("[ERROR] Network error during authentication: {}".format(ex))
        print("[TIP] Please check your internet connection and APS credentials.")
    except Exception as ex:
        print("[ERROR] Unexpected error during authentication: {}".format(ex))
        print("[DEBUG] Error type: {}".format(type(ex).__name__))
        
        # Show inner exception if available
        if hasattr(ex, '__cause__') and ex.__cause__:
            print("[DEBUG] Inner error: {}".format(ex.__cause__))


def handle_clear_token_command():
    """
    Handle the ClearToken command - clear stored access token
    """
    try:
        current_token = OAuthUtil.get_current_token()
        if current_token:
            print("[INFO] Current token expires at: {} UTC".format(current_token.expires_at))
            print("[DELETE]  Clearing stored token...")
        
        OAuthUtil.clear_stored_token()
        print("[OK] Token cleared successfully.")
        print("[TIP] You will need to authenticate again for the next API call.")
    except Exception as ex:
        if not current_token:
            print("[INFO] No token currently stored.")
        else:
            print("[ERROR] Error clearing token: {}".format(ex))


def handle_check_token_command():
    """
    Handle the CheckToken command - check current token status
    """
    try:
        current_token = OAuthUtil.get_current_token()
        
        if current_token:
            print("[OK] Token is stored")
            print("[SECURE] Token type: {}".format(current_token.token_type))
            print("[TARGET] Scopes: {}".format(current_token.scope))
            
            # Check expiration
            if current_token.expires_at:
                print("[DATE] Expires at: {} UTC".format(current_token.expires_at))
                
                time_until_expiry = current_token.expires_at - datetime.utcnow()
                if time_until_expiry.total_seconds() <= 0:
                    print("[WARNING]  Token is EXPIRED")
                    print("[TIP] Run get_token command to get a new token.")
                elif time_until_expiry.total_seconds() > 3600:
                    print("[OK] Token valid for: {:.1f} hours".format(time_until_expiry.total_seconds() / 3600))
                elif time_until_expiry.total_seconds() > 300:  # 5 minutes
                    print("[CLOCK] Token expires soon: {:.1f} minutes".format(time_until_expiry.total_seconds() / 60))
            else:
                print("[WARNING]  Token expiration time not available")
            
            print("[TOKEN] Access token: {}...".format(current_token.access_token[:min(20, len(current_token.access_token))]))
        else:
            print("[INFO] No token currently stored.")
            print("[TIP] Run get_token command to authenticate and get a token.")
    except Exception as ex:
        print("[ERROR] Error checking token: {}".format(ex))


# Convenience functions that match the C# CommandMethod names
def get_token():
    """Convenience function that matches C# GetToken command"""
    handle_get_token_command()

def clear_token():
    """Convenience function that matches C# ClearToken command"""
    handle_clear_token_command()

def check_token():
    """Convenience function that matches C# CheckToken command"""
    handle_check_token_command()


# Main function for CLI usage
def main():
    """Main function for command-line usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python token_util.py <command>")
        print("Commands: get_token, clear_token, check_token")
        return
    
    command = sys.argv[1].lower()
    
    if command == "get_token":
        get_token()
    elif command == "clear_token":
        clear_token()
    elif command == "check_token":
        check_token()
    else:
        print("Unknown command: {}".format(command))
        print("Available commands: get_token, clear_token, check_token")


if __name__ == "__main__":
    main() 