#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OAuth data models for APS authentication

Python 2.7 compatible version without dataclasses
"""

import json
from datetime import datetime, timedelta


class OAuthConfig(object):
    """Configuration for OAuth authentication"""
    
    def __init__(self, client_id="", client_secret="", callback_url="", 
                 local_callback_url="", auth_url="", token_url="", scope=""):
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url
        self.local_callback_url = local_callback_url
        self.auth_url = auth_url or "https://developer.api.autodesk.com/authentication/v1/authorize"
        self.token_url = token_url or "https://developer.api.autodesk.com/authentication/v1/gettoken"
        self.scope = scope
    
    @property
    def is_valid(self):
        """Check if configuration has required fields"""
        return bool(self.client_id and self.client_secret)
    
    @property
    def use_local_callback(self):
        """Check if local callback server should be used"""
        return bool(self.local_callback_url and self.local_callback_url.strip())
    
    def __repr__(self):
        return "OAuthConfig(client_id='{}...', callback_url='{}')".format(
            self.client_id[:8] if self.client_id else "", 
            self.callback_url
        )
    
    @classmethod
    def create_with_defaults(cls):
        """Create OAuth configuration with default values"""
        return cls(
            callback_url="http://localhost:8082/callback/",
            scope="viewables:read data:read data:write data:create data:search bucket:create bucket:read bucket:update bucket:delete"
        )


class TokenResponse(object):
    """OAuth token response"""
    
    def __init__(self, access_token="", token_type="Bearer", expires_in=3600, 
                 refresh_token="", scope="", expires_at=None):
        self.access_token = access_token
        self.token_type = token_type
        self.expires_in = expires_in
        self.refresh_token = refresh_token
        self.scope = scope
        self.expires_at = expires_at
    
    @property
    def is_expired(self):
        """Check if token is expired"""
        if not self.expires_at:
            return False
        return datetime.utcnow() >= self.expires_at
    
    def set_expiration_time(self):
        """Set expiration time based on expires_in"""
        if self.expires_in:
            self.expires_at = datetime.utcnow() + timedelta(seconds=self.expires_in)
    
    @classmethod
    def from_json(cls, json_data):
        """Create TokenResponse from JSON data"""
        if not isinstance(json_data, dict):
            raise ValueError("Invalid JSON data for TokenResponse")
        
        return cls(
            access_token=json_data.get('access_token', ''),
            token_type=json_data.get('token_type', 'Bearer'),
            expires_in=int(json_data.get('expires_in', 3600)),
            refresh_token=json_data.get('refresh_token', ''),
            scope=json_data.get('scope', '')
        )
    
    def to_json(self):
        """Convert TokenResponse to JSON-serializable dict"""
        return {
            'access_token': self.access_token,
            'token_type': self.token_type,
            'expires_in': self.expires_in,
            'refresh_token': self.refresh_token,
            'scope': self.scope,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None
        }
    
    def __repr__(self):
        return "TokenResponse(token_type='{}', expires_in={}, scope='{}')".format(
            self.token_type, self.expires_in, self.scope
        )


class OAuthScopes(object):
    """Common OAuth scopes for APS"""
    
    # Data Management API
    DATA_READ = "data:read"
    DATA_WRITE = "data:write"
    DATA_CREATE = "data:create"
    DATA_SEARCH = "data:search"
    
    # Model Derivative API
    VIEWABLES_READ = "viewables:read"
    
    # Bucket Management
    BUCKET_CREATE = "bucket:create"
    BUCKET_READ = "bucket:read"
    BUCKET_UPDATE = "bucket:update"
    BUCKET_DELETE = "bucket:delete"
    
    # Common scope combinations
    DATA_MANAGEMENT = "data:read data:write data:create data:search"
    FULL_ACCESS = "viewables:read data:read data:write data:create data:search bucket:create bucket:read bucket:update bucket:delete"


class OAuthError(object):
    """OAuth error response"""
    
    def __init__(self, error="", error_description="", error_uri=""):
        self.error = error
        self.error_description = error_description
        self.error_uri = error_uri
    
    def __str__(self):
        if self.error_description:
            return "{}: {}".format(self.error, self.error_description)
        return self.error or "Unknown OAuth error"
    
    @classmethod
    def from_json(cls, json_data):
        """Create OAuthError from JSON data"""
        if not isinstance(json_data, dict):
            return cls(error="Invalid error response format")
        
        return cls(
            error=json_data.get('error', 'unknown_error'),
            error_description=json_data.get('error_description', ''),
            error_uri=json_data.get('error_uri', '')
        )
    
    def __repr__(self):
        return "OAuthError(error='{}', description='{}')".format(
            self.error, self.error_description
        ) 