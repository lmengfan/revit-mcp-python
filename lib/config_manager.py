#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Configuration manager for Civil3D Connector

Handles loading configuration from .env files and environment variables.
Python 2.7 compatible version.
"""

import os
import json
import threading


class ConfigManager(object):
    """Manages application configuration from environment variables and .env files"""
    
    _config = {}
    _loaded = False
    _lock = threading.Lock()
    
    @classmethod
    def load_configuration(cls, env_file_path=None):
        """
        Load configuration from .env file and environment variables
        
        Args:
            env_file_path: Optional path to .env file
        """
        import os

        current_directory = os.getcwd()
        print("Current Working Directory:", current_directory)
        with cls._lock:
            if cls._loaded:
                return
            
            # Load from .env file first
            # Get the directory where the current file is located
            current_dir = os.path.dirname(__file__)
            env_file_path = os.path.join(current_dir, '.env')
            print("Looking for .env at: {env_file_path}")
            
            if os.path.exists(env_file_path):
                cls._load_from_file(env_file_path)
            else:
                # Try parent directory
                parent_dir = os.path.dirname(current_dir)
                env_file_path = os.path.join(parent_dir, '.env')
                print("Looking for .env at parent dir: {env_file_path}")
                
                if os.path.exists(env_file_path):
                    cls._load_from_file(env_file_path)
            
            # Load from system environment (overrides file values)
            cls._load_from_system_environment()
            cls._loaded = True
    
    @classmethod
    def get_string(cls, key, default_value=""):
        """Get string configuration value"""
        cls._ensure_loaded()
        return cls._config.get(key, default_value)
    
    @classmethod
    def get_int(cls, key, default_value=0):
        """Get integer configuration value"""
        cls._ensure_loaded()
        value = cls._config.get(key, str(default_value))
        try:
            return int(value)
        except (ValueError, TypeError):
            return default_value
    
    @classmethod
    def get_bool(cls, key, default_value=False):
        """Get boolean configuration value"""
        cls._ensure_loaded()
        value = cls._config.get(key, "").lower()
        if value in ('true', '1', 'yes', 'on'):
            return True
        elif value in ('false', '0', 'no', 'off'):
            return False
        return default_value
    
    @classmethod
    def get_double(cls, key, default_value=0.0):
        """Get float configuration value"""
        cls._ensure_loaded()
        value = cls._config.get(key, str(default_value))
        try:
            return float(value)
        except (ValueError, TypeError):
            return default_value
    
    @classmethod
    def has_key(cls, key):
        """Check if configuration key exists"""
        cls._ensure_loaded()
        return key in cls._config
    
    @classmethod
    def get_all_keys(cls):
        """Get all configuration keys"""
        cls._ensure_loaded()
        return list(cls._config.keys())
    
    @classmethod
    def set_value(cls, key, value):
        """Set configuration value"""
        cls._ensure_loaded()
        cls._config[key] = str(value)
    
    @classmethod
    def reload(cls, env_file_path=None):
        """Reload configuration"""
        with cls._lock:
            cls._loaded = False
            cls._config.clear()
            cls.load_configuration(env_file_path)
    
    @classmethod
    def get_oauth_config(cls):
        """Get OAuth configuration"""
        from oauth_models import OAuthConfig
        
        environment = cls.get_oauth_environment()
        
        if environment == "prod":
            client_id_key = "APS_CLIENT_ID"
            client_secret_key = "APS_CLIENT_SECRET"
            callback_url_key = "APS_CALLBACK_URL_LOCAL"
            callback_url_key_back = "APS_CALLBACK_URL"
            auth_url = "APS_AUTH_URL"
            token_url = "APS_TOKEN_URL"
            scopes = "APS_SCOPES"
        else:  # staging
            client_id_key = "APS_STG_CLIENT_ID"
            client_secret_key = "APS_STG_CLIENT_SECRET"
            callback_url_key = "APS_STG_CALLBACK_URL_LOCAL"
            callback_url_key_back = "APS_STG_CALLBACK_URL"
            auth_url = "APS_STG_AUTH_URL"
            token_url = "APS_STG_TOKEN_URL"
            scopes = "APS_STG_SCOPES"
        return OAuthConfig(
            client_id=cls.get_string(client_id_key),
            client_secret=cls.get_string(client_secret_key),
            callback_url=cls.get_string(callback_url_key_back),
            local_callback_url=cls.get_string(callback_url_key),
            auth_url=cls.get_string(auth_url),
            token_url=cls.get_string(token_url),
            scope=cls.get_string(scopes)
        )
    
    @classmethod
    def validate_required_configuration(cls):
        """
        Validate that all required configuration keys are present
        
        Returns:
            List of missing required keys
        """
        cls._ensure_loaded()
        
        environment = cls.get_oauth_environment()
        
        if environment == "prod":
            required_keys = [
                "APS_CLIENT_ID",
                "APS_CLIENT_SECRET",
                'APS_CALLBACK_URL',
                'APS_CALLBACK_URL_LOCAL'
            ]
        else:  # staging
            required_keys = [
                "APS_STG_CLIENT_ID", 
                "APS_STG_CLIENT_SECRET",
                'APS_STG_CALLBACK_URL',
                'APS_STG_CALLBACK_URL_LOCAL'
            ]
        
        missing_keys = []
        for key in required_keys:
            if not cls.has_key(key) or not cls.get_string(key).strip():
                missing_keys.append(key)
        
        return missing_keys
    
    @classmethod
    def get_oauth_environment(cls):
        """Get OAuth environment (prod or stg)"""
        return cls.get_string("DX_ENVIRONMENT", "stg").lower()
    
    @classmethod
    def get_application_config(cls):
        """Get application configuration"""
        return ApplicationConfig(
            environment=cls.get_oauth_environment(),
            log_level=cls.get_string("LOG_LEVEL", "INFO"),
            dx_acc_config_path=cls.get_string("DX_ACC_CONFIG_PATH", "")
        )
    
    @classmethod
    def get_atf_config(cls):
        """Get ATF configuration"""
        return AtfConfig(
            atf_path=cls.get_string("ATF_PATH", ""),
            atf_timeout_seconds=cls.get_int("ATF_TIMEOUT_SECONDS", 300),
            atf_log_level=cls.get_string("ATF_LOG_LEVEL", "INFO")
        )
    
    @classmethod
    def get_network_config(cls):
        """Get network configuration"""
        return NetworkConfig(
            http_timeout_seconds=cls.get_int("HTTP_TIMEOUT_SECONDS", 30),
            max_retry_attempts=cls.get_int("MAX_RETRY_ATTEMPTS", 3),
            retry_delay_ms=cls.get_int("RETRY_DELAY_MS", 1000)
        )
    
    @classmethod
    def get_env_variable(cls, key, default_value=None):
        """
        Get a specific environment variable from .env file
        
        Args:
            key (str): The environment variable name
            default_value: Default value if key not found
            
        Returns:
            str: The environment variable value or default_value
        """
        cls._ensure_loaded()
        return cls._config.get(key, default_value)
    
    @classmethod
    def get_atf_variables(cls):
        """
        Get all ATF-related environment variables from .env file
        
        Returns:
            dict: Dictionary containing all ATF configuration variables
        """
        cls._ensure_loaded()
        
        atf_vars = {
            # ATF Configuration
            'ATF_LIBRARY_PATH': cls.get_string("ATF_LIBRARY_PATH", ""),
            'DEFAULT_ATF_FORMAT': cls.get_string("DEFAULT_ATF_FORMAT", "dx"),
            'DX_ENVIRONMENT': cls.get_string("DX_ENVIRONMENT", "stg"),
            'LOG_DUMP_PATH': cls.get_string("LOG_DUMP_PATH", "Log\\fdxConsumer_log.json"),
            'ATF_XLAYER_DX_ACC_CONFIG_JSON_STG': cls.get_string("ATF_XLAYER_DX_ACC_CONFIG_JSON_STG", "Resources\\AccConfig_stg.json"),
            'ATF_XLAYER_DX_ACC_CONFIG_JSON_PROD': cls.get_string("ATF_XLAYER_DX_ACC_CONFIG_JSON_PROD", "Resources\\AccConfig_prod.json"),
            
            # Network Configuration (useful for ATF operations)
            'HTTP_TIMEOUT_SECONDS': cls.get_int("HTTP_TIMEOUT_SECONDS", 30),
            'MAX_RETRY_ATTEMPTS': cls.get_int("MAX_RETRY_ATTEMPTS", 3),
            'RETRY_DELAY_MS': cls.get_int("RETRY_DELAY_MS", 1000),
            
            # APS URLs (useful for ATF data exchange operations)
            'APS_BASE_URL': cls.get_string("APS_BASE_URL", "https://developer.api.autodesk.com"),
            'APS_STG_BASE_URL': cls.get_string("APS_STG_BASE_URL", "https://developer-stg.api.autodesk.com")
        }
        
        return atf_vars
    
    @classmethod
    def _ensure_loaded(cls):
        """Ensure configuration is loaded"""
        if not cls._loaded:
            cls.load_configuration()
    
    @classmethod
    def _load_from_file(cls, file_path):
        """Load configuration from .env file"""
        if not os.path.exists(file_path):
            return
        
        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        cls._config[key] = value
        except IOError:
            pass  # File doesn't exist or can't be read
    
    @classmethod
    def _load_from_system_environment(cls):
        """Load configuration from system environment variables"""
        for key, value in os.environ.items():
            cls._config[key] = value
    
    @classmethod
    def _get_absolute_path(cls, relative_path):
        """Convert relative path to absolute path"""
        if os.path.isabs(relative_path):
            return relative_path
        
        # Try relative to current working directory
        current_dir_path = os.path.abspath(relative_path)
        if os.path.exists(current_dir_path):
            return current_dir_path
        
        # Try relative to script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_relative_path = os.path.join(script_dir, relative_path)
        if os.path.exists(script_relative_path):
            return script_relative_path
        
        # Return the original path if nothing found
        return relative_path


class ApplicationConfig(object):
    """Application configuration"""
    
    def __init__(self, environment="stg", log_level="INFO", dx_acc_config_path=""):
        self.environment = environment
        self.log_level = log_level
        self.dx_acc_config_path = dx_acc_config_path
    
    def get_dx_acc_config_path(self):
        """Get the full path to DX ACC config file"""
        if not self.dx_acc_config_path:
            # Use default based on environment
            if self.environment == "prod":
                return os.path.join("Resources", "AccConfig_prod.json")
            else:
                return os.path.join("Resources", "AccConfig_stg.json")
        
        return ConfigManager._get_absolute_path(self.dx_acc_config_path)


class AtfConfig(object):
    """ATF configuration"""
    
    def __init__(self, atf_path="", atf_timeout_seconds=300, atf_log_level="INFO"):
        self.atf_path = atf_path
        self.atf_timeout_seconds = atf_timeout_seconds
        self.atf_log_level = atf_log_level


class NetworkConfig(object):
    """Network configuration"""
    
    def __init__(self, http_timeout_seconds=30, max_retry_attempts=3, retry_delay_ms=1000):
        self.http_timeout_seconds = http_timeout_seconds
        self.max_retry_attempts = max_retry_attempts
        self.retry_delay_ms = retry_delay_ms 