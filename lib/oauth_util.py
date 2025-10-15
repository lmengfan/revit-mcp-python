#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utility class for handling APS 3-legged OAuth authentication

Python 2.7/3.x compatible version without asyncio
"""

import base64
import json
import threading
import time
import webbrowser
import uuid

# Python 2/3 compatibility for urllib
try:
    # Python 2
    from urllib import urlencode, quote
except ImportError:
    # Python 3
    from urllib.parse import urlencode, quote

import requests

from oauth_models import OAuthConfig, TokenResponse, OAuthError
from local_callback_server import LocalCallbackServer


class OAuthUtil(object):
    """Utility class for handling APS 3-legged OAuth authentication"""
    
    _current_token = None
    _token_lock = threading.Lock()
    
    @classmethod
    def create_http_session(cls):
        """Create HTTP session with network configuration applied"""
        from config_manager import ConfigManager
        network_config = ConfigManager.get_network_config()
        session = requests.Session()
        session.timeout = network_config.http_timeout_seconds
        return session
    
    @classmethod
    def generate_authorization_url(cls, config, state=None):
        """
        Generate authorization URL for 3-legged OAuth flow
        
        Args:
            config: OAuth configuration
            state: Optional state parameter for security
            
        Returns:
            Authorization URL
        """
        if not config.is_valid:
            raise ValueError("OAuth configuration is invalid. ClientId and ClientSecret are required.")
        
        parameters = {
            "response_type": "code",
            "client_id": config.client_id,
            "redirect_uri": config.local_callback_url,
            "scope": config.scope
        }
        
        if state:
            parameters["state"] = state
        
        query_string = urlencode(parameters)
        return "{}?{}".format(config.auth_url, query_string)
    
    @classmethod
    def get_authorization_code_via_browser(cls, config):
        """
        Get authorization code by opening browser and capturing callback
        
        Args:
            config: OAuth configuration
            
        Returns:
            Authorization code
        """
        # Generate state for security
        state = str(uuid.uuid4())
        
        # Generate authorization URL
        auth_url = cls.generate_authorization_url(config, state)
        
        # Try to use local callback server if configured
        if config.use_local_callback:
            try:
                server = LocalCallbackServer(config.local_callback_url)
                server.start()
                
                print("Opening browser for APS authentication...")
                webbrowser.open(auth_url)
                
                # Wait for callback with timeout
                result = server.wait_for_callback(timeout_seconds=300)  # 5 minutes

                if result:
                    return result
                else:
                    # Fallback to manual entry if timeout
                    server.stop()
                    
            except Exception as ex:
                print("[WARNING] Local callback server failed. Falling back to manual entry...")
                print("Server error: {}".format(str(ex)))
        
        # Manual entry fallback
        print("Opening browser for APS authentication...")
        print("After logging in, you will be redirected to a page.")
        print("Copy the 'code' parameter from the URL and paste it below.")
        webbrowser.open(auth_url)
        
        # Get authorization code from user input
        try:
            # Python 2
            code = raw_input("Please enter the authorization code: ").strip()
        except NameError:
            # Python 3
            code = input("Please enter the authorization code: ").strip()
        
        if not code:
            raise ValueError("Authorization code is required")
        
        return code
    
    @classmethod
    def exchange_code_for_token(cls, config, authorization_code):
        """
        Exchange authorization code for access token
        
        Args:
            config: OAuth configuration
            authorization_code: Authorization code from OAuth flow
            
        Returns:
            Token response
        """
        request_body = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": config.local_callback_url
        }
        
        return cls._request_token(config, request_body)
    
    @classmethod
    def refresh_token(cls, config, refresh_token):
        """
        Refresh access token using refresh token
        
        Args:
            config: OAuth configuration
            refresh_token: Refresh token
            
        Returns:
            New token response
        """
        request_body = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        return cls._request_token(config, request_body)
    
    @classmethod
    def get_valid_access_token(cls, config):
        """
        Get a valid access token, refreshing if necessary
        
        Args:
            config: OAuth configuration
            
        Returns:
            Valid access token
        """
        with cls._token_lock:
            current_token = cls._current_token
            
            # Check if we have a valid token
            if current_token and not current_token.is_expired:
                return current_token.access_token
            
            # Try to refresh if we have a refresh token
            if current_token and current_token.refresh_token:
                try:
                    print("Refreshing expired access token...")
                    new_token = cls.refresh_token(config, current_token.refresh_token)
                    cls._current_token = new_token
                    return new_token.access_token
                except Exception:
                    # Refresh failed, will need new authorization
                    print("Token refresh failed. Will request new authorization...")
                    pass
            
            # Need new authorization
            print("Will request new authorization...")
            raise ValueError("No valid token available. Please run authentication flow first.")
    
    @classmethod
    def get_3_legged_token(cls, config):
        """
        Get 3-legged OAuth token through complete flow
        
        Args:
            config: OAuth configuration
            
        Returns:
            Access token
        """
        print("Starting 3-legged OAuth authorization flow...")
        
        # Get authorization code
        auth_code = cls.get_authorization_code_via_browser(config)
        # Exchange code for token
        token_response = cls.exchange_code_for_token(config, auth_code)
        
        # Store token
        with cls._token_lock:
            cls._current_token = token_response
        
        return token_response.access_token
    
    @classmethod
    def get_3_legged_token_from_environment(cls):
        """
        Get 3-legged OAuth token using configuration from environment
        
        Returns:
            Access token
        """
        config = cls.create_config_from_environment()
        return cls.get_3_legged_token(config)
    
    @classmethod
    def clear_stored_token(cls):
        """Clear the stored token"""
        with cls._token_lock:
            cls._current_token = None
    
    @classmethod
    def get_current_token(cls):
        """Get the current stored token"""
        with cls._token_lock:
            return cls._current_token
    
    @classmethod
    def _execute_with_retry(cls, operation):
        """Execute HTTP request with retry logic based on network configuration"""
        from config_manager import ConfigManager
        network_config = ConfigManager.get_network_config()
        max_retries = network_config.max_retry_attempts
        retry_delay = network_config.retry_delay_ms / 1000.0  # Convert to seconds
        
        for attempt in range(max_retries + 1):
            try:
                return operation()
            except (requests.RequestException, requests.Timeout) as ex:
                if attempt < max_retries:
                    # Wait before retrying with exponential backoff
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    raise ex
    
    @classmethod
    def _request_token(cls, config, request_body):
        """
        Common method for making token requests
        
        Args:
            config: OAuth configuration
            request_body: Request body parameters
            
        Returns:
            Token response
        """
        from config_manager import ConfigManager
        
        # Create Basic Auth header
        credentials = base64.b64encode(
            "{}:{}".format(config.client_id, config.client_secret).encode('utf-8')
        ).decode('utf-8')
        
        headers = {
            "Authorization": "Basic {}".format(credentials),
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        def make_request():
            network_config = ConfigManager.get_network_config()
            response = requests.post(
                config.token_url,
                data=request_body,
                headers=headers,
                timeout=network_config.http_timeout_seconds
            )
            return response
        
        try:
            response = cls._execute_with_retry(make_request)
            response_data = response.json()
            
            if not response.ok:
                error = OAuthError.from_json(response_data)
                raise requests.HTTPError("Token request failed: {}".format(error))
            
            token_response = TokenResponse.from_json(response_data)
            token_response.set_expiration_time()
            
            return token_response
            
        except requests.RequestException as ex:
            raise ValueError("HTTP request failed: {}".format(str(ex)))
        except (KeyError, ValueError) as ex:
            raise ValueError("Failed to parse token response: {}".format(str(ex)))
    
    @classmethod
    def create_config_with_defaults(cls, client_id, client_secret, 
                                   callback_url="http://localhost:8082/callback/",
                                   scope="viewables:read data:read data:write data:create data:search bucket:create bucket:read bucket:update bucket:delete"):
        """
        Create OAuth configuration with default values
        
        Args:
            client_id: APS Client ID
            client_secret: APS Client Secret  
            callback_url: Callback URL for OAuth flow
            scope: OAuth scopes
            
        Returns:
            OAuth configuration
        """
        return OAuthConfig(
            client_id=client_id,
            client_secret=client_secret,
            callback_url=callback_url,
            scope=scope
        )
    
    @classmethod
    def create_config_from_environment(cls):
        """Create OAuth configuration from environment variables"""
        from config_manager import ConfigManager
        return ConfigManager.get_oauth_config()
    
    @classmethod
    def validate_environment_configuration(cls):
        """
        Validate that required OAuth environment configuration is present
        
        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            from config_manager import ConfigManager
            
            missing_keys = ConfigManager.validate_required_configuration()
            if missing_keys:
                print("[ERROR] Configuration Error")
                for key in missing_keys:
                    print("  Missing: {}".format(key))
                print("Please check your .env file or environment variables.")
                print("Refer to config/SETUP_GUIDE.md for setup instructions.")
                return False
            
            # Test OAuth config creation
            config = ConfigManager.get_oauth_config()
            environment = ConfigManager.get_oauth_environment()
            
            print("[OK] Configuration Valid ({})".format(environment.upper()))
            print("Client ID: {}...".format(config.client_id[:8]))
            print("Scopes: {}".format(config.scope))
            print("Callback URL: {}".format(config.callback_url))
            
            # Check local callback availability
            if config.local_callback_url:
                from local_callback_server import is_local_callback_available
                if is_local_callback_available(config.local_callback_url):
                    print("[OK] Local Callback: {} (Available)".format(config.local_callback_url))
                    print("   -> Automatic code capture enabled")
                else:
                    print("[WARNING] Local Callback: {} (Not Available)".format(config.local_callback_url))
                    print("   -> Will use manual code entry")
            else:
                print("[NOTE] Local Callback: Not configured")
                print("   -> Will use manual code entry")
            
            return True
            
        except Exception as ex:
            print("[ERROR] Configuration validation failed: {}".format(str(ex)))
            return False 