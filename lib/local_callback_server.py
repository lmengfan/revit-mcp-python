#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Local HTTP server for capturing OAuth authorization codes

Python 2.7/3.x compatible version without asyncio
"""

import socket
import threading
import time

# Python 2/3 compatibility for HTTP server
try:
    # Python 2
    from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
    from urlparse import urlparse, parse_qs
except ImportError:
    # Python 3
    from http.server import HTTPServer, BaseHTTPRequestHandler
    try:
        from urllib.parse import urlparse, parse_qs
    except ImportError:
        from urlparse import urlparse, parse_qs


class CallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callbacks"""
    
    def do_GET(self):
        """Handle GET requests for OAuth callbacks"""
        try:
            # Parse the request URL
            parsed_url = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            
            # Check for authorization code
            if 'code' in query_params:
                code = query_params['code'][0]
                self.server.callback_server._result_code = code
                self.server.callback_server._result_received.set()
                self._send_success_response()
                return
            
            # Check for error
            if 'error' in query_params:
                error = query_params['error'][0]
                error_description = query_params.get('error_description', [''])[0]
                error_message = "{}: {}".format(error, error_description) if error_description else error
                self.server.callback_server._result_error = error_message
                self.server.callback_server._result_received.set()
                self._send_error_response(error_message)
                return
            
            # No code or error found
            self._send_error_response("No authorization code found in callback")
            
        except Exception as ex:
            self._send_error_response("Failed to process callback: {}".format(str(ex)))
    
    def _send_success_response(self):
        """Send success response to browser"""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Authorization Successful</title>
    <style>
        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
        .success {{ color: #4CAF50; font-size: 24px; margin: 20px 0; }}
        .info {{ color: #666; font-size: 16px; }}
    </style>
</head>
<body>
    <div class='success'>[OK] Authorization Successful</div>
    <div class='info'>
        <p>You have successfully authenticated with Autodesk Platform Services.</p>
        <p>You can now close this browser window and return to your application.</p>
    </div>
</body>
</html>"""
        
        self._send_html_response(html)
    
    def _send_error_response(self, error_message):
        """Send error response to browser"""
        html = """<!DOCTYPE html>
<html>
<head>
    <title>Authorization Error</title>
    <style>
        body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
        .error {{ color: #f44336; font-size: 24px; margin: 20px 0; }}
        .info {{ color: #666; font-size: 16px; }}
    </style>
</head>
<body>
    <div class='error'>[ERROR] Authorization Error</div>
    <div class='info'>
        <p>{}</p>
        <p>Please return to your application and try again.</p>
    </div>
</body>
</html>""".format(error_message)
        
        self._send_html_response(html)
    
    def _send_html_response(self, html):
        """Send HTML response"""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.send_header('Content-Length', str(len(html)))
        self.end_headers()
        self.wfile.write(html)
    
    def log_message(self, format, *args):
        """Override to suppress default logging"""
        pass


class LocalCallbackServer(object):
    """Local HTTP server for capturing OAuth authorization codes"""
    
    def __init__(self, callback_url):
        """
        Initialize local callback server
        
        Args:
            callback_url: The callback URL (e.g., http://localhost:8082/callback/)
        """
        self.callback_url = callback_url
        self.server = None
        self.server_thread = None
        self.port = self._extract_port(callback_url)
        self._result_code = None
        self._result_error = None
        self._result_received = threading.Event()
    
    def start(self):
        """Start the local callback server"""
        try:
            # Create HTTP server
            self.server = HTTPServer(('localhost', self.port), CallbackHandler)
            self.server.callback_server = self  # Reference back to this instance
            
            # Start server in background thread
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
        except Exception as ex:
            print("[ERROR] Failed to start local callback server: {}".format(str(ex)))
            raise
    
    def stop(self):
        """Stop the local callback server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        if self.server_thread:
            self.server_thread.join(timeout=1.0)
    
    def wait_for_callback(self, timeout_seconds=300):
        """
        Wait for OAuth callback with timeout
        
        Args:
            timeout_seconds: Maximum time to wait for callback
            
        Returns:
            Authorization code if successful, None if failed or timed out
        """
        try:
            print("Waiting for OAuth callback (timeout: {} seconds)...".format(timeout_seconds))
            
            # Wait for callback with timeout
            if self._result_received.wait(timeout_seconds):
                if self._result_error:
                    print("[ERROR] {}".format(self._result_error))
                    return None
                else:
                    print("[OK] Authorization code received successfully!")
                    return self._result_code
            else:
                print("[TIMER] Callback timeout reached. Please try again.")
                return None
                
        except Exception as ex:
            if "Access is denied" in str(ex):
                print("[ERROR] Failed to start local server: Access denied.")
                print("Please ensure port {} is available or run as administrator.".format(self.port))
            else:
                print("[ERROR] Failed to start local server: {}".format(str(ex)))
            return None
        finally:
            self.stop()
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()
    
    @staticmethod
    def _extract_port(callback_url):
        """
        Extract port number from callback URL
        
        Args:
            callback_url: The callback URL
            
        Returns:
            Port number
        """
        try:
            parsed = urlparse(callback_url)
            return parsed.port or 80
        except Exception:
            return 8082  # Default port


def is_local_callback_available(callback_url):
    """
    Check if local callback server can be started on the specified URL
    
    Args:
        callback_url: The callback URL to test
        
    Returns:
        True if port is available, False otherwise
    """
    try:
        port = LocalCallbackServer._extract_port(callback_url)
        
        # Try to bind to the port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        # If connection failed, port is available
        return result != 0
        
    except Exception:
        return False


def extract_port(callback_url):
    """
    Extract port from callback URL
    
    Args:
        callback_url: Callback URL string
        
    Returns:
        Port number as integer
    """
    return LocalCallbackServer._extract_port(callback_url) 