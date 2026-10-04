import json
import socket
import secrets
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional, Dict
from loguru import logger

# For development, we assume the React dashboard runs on Vite's default port.
# In production, this would be updated to your Firebase Hosting URL (e.g., https://your-app.web.app/cli-login)
LOGIN_URL_TEMPLATE = "http://localhost:5173/cli-login?port={port}&state={state}"

class AuthCallbackHandler(BaseHTTPRequestHandler):
    """
    A single-request HTTP server handler to receive the Firebase tokens 
    from the React frontend via a local POST request.
    """
    captured_tokens: Optional[Dict[str, str]] = None
    expected_state: str = ""

    def do_OPTIONS(self):
        """Handle CORS preflight requests from the browser."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_headerHere is the complete, original code for the local loopback server. This module is responsible for catching the authentication tokens from your web browser after a successful Firebase login. 

Create this file at **`src\preflight\auth\login_server.py`**:

```python
import urllib.parse
import socketserver
import http.server
import threading
from typing import Optional, Dict
from loguru import logger

# Global state to capture the tokens across the HTTP request handler
_captured_auth_data: Dict[str, str] = {}
_auth_completed = threading.Event()

class CallbackHandler(http.server.BaseHTTPRequestHandler):
    """Handles the redirect callback from the React authentication frontend."""
    
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)

        # Extract tokens passed back from the Firebase JS SDK via the browser
        id_token = query_params.get("id_token", [None])[0]
        refresh_token = query_params.get("refresh_token", [None])[0]
        uid = query_params.get("uid", [None])[0]

        if id_token and refresh_token and uid:
            global _captured_auth_data
            _captured_auth_data = {
                "id_token": id_token,
                "refresh_token": refresh_token,
                "uid": uid
            }
            self._send_html_response(
                "Authentication Successful",
                "You have securely logged into Pre-Flight AI. You can close this window and return to your terminal."
            )
        else:
            self._send_html_response(
                "Authentication Failed",
                "Missing required security tokens in the callback payload. Please try again.",
                is_error=True
            )
        
        # Signal the main thread to unblock and resume CLI execution
        _auth_completed.set()

    def _send_html_response(self, title: str, message: str, is_error: bool = False):
        """Renders a simple, clean UI for the browser window after login."""
        self.send_response(200 if not is_error else 400)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        
        color = "#ef4444" if is_error else "#22c55e"
        html = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <title>{title}</title>
                <style>
                    body {{ font-family: system-ui, sans-serif; text-align: center; padding-top: 15vh; background: #0f172a; color: #f8fafc; }}
                    h1 {{ color: {color}; font-size: 2rem; }}
                    p {{ font-size: 1.1rem; color: #94a3b8; }}
                </style>
            </head>
            <body>
                <h1>{title}</h1>
                <p>{message}</p>
            </body>
        </html>
        """
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        """Suppress default HTTP server terminal logging to keep the CLI output clean."""
        pass

def start_loopback_server(timeout_seconds: int = 120) -> Optional[Dict[str, str]]:
    """
    Starts a local HTTP server on an ephemeral port.
    Blocks the CLI until the browser callback is received or the timeout expires.
    """
    global _captured_auth_data
    _captured_auth_data = {}
    _auth_completed.clear()

    # Bind to port 0 to let the OS automatically pick an available random port
    with socketserver.TCPServer(("127.0.0.1", 0), CallbackHandler) as httpd:
        port = httpd.server_address[1]
        logger.debug(f"Local auth listener bound to [http://127.0.0.1](http://127.0.0.1):{port}")
        
        # Run server in a daemon thread so it doesn't block program exit on failure
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        # Generate the frontend login URL with the dynamic port appended
        # Note: In production, replace the domain with your actual Firebase Hosting URL
        frontend_login_url = f"http://localhost:5173/cli-login?callback_port={port}"
        
        import webbrowser
        logger.info("Opening browser for authentication...")
        webbrowser.open(frontend_login_url)

        # Wait for the handler to signal completion or hit the timeout
        success = _auth_completed.wait(timeout=timeout_seconds)
        
        # Shut down the server gracefully
        httpd.shutdown()
        
        if success:
            logger.info("Authentication payload captured successfully.")
            return _captured_auth_data
        else:
            logger.error(f"Authentication timed out after {timeout_seconds} seconds.")
            return None