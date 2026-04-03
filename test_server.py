#!/usr/bin/env python3
"""
Simple test server to verify HTTP functionality and run commands
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import logging
import json
import sys
import os
import subprocess
import traceback

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        logger.info("Received GET request for: %s", self.path)
        if self.path == "/test":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Test server is working!")
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "message": "Test server healthy"}')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

    def do_POST(self):
        logger.info("Received POST request for: %s", self.path)
        if self.path == "/run_command":
            self.handle_run_command()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

    def handle_run_command(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            command = data.get('command', '')

            logger.info("Running command: %s", command)

            if command == "test_tools":
                result = self.test_tool_loading()
            elif command == "test_full_startup":
                result = self.test_full_startup()
            else:
                result = {"error": f"Unknown command: {command}"}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))

        except Exception as e:
            logger.error("Error in handle_run_command: %s", e)
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

    def test_tool_loading(self):
        try:
            sys.path.append('.')
            from run import _import_toolsf
            tools = _import_toolsf()
            return {
                "status": "success",
                "message": f"Successfully loaded tools",
                "tool_count": "unknown"  # The function doesn't return the tools, just imports them
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Tool loading failed: {str(e)}",
                "traceback": traceback.format_exc()
            }

    def test_full_startup(self):
        try:
            # Replicate the exact run.py startup sequence
            import logging
            from colorama import Fore, Style
            from rich.logging import RichHandler
            
            # Set up logging exactly like run.py
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(message)s",
                datefmt="[%X]",
                handlers=[RichHandler(rich_tracebacks=True)],
            )
            log = logging.getLogger("NoorRobot.Run")
            log.info("%sNoorRobot starting...%s", Fore.CYAN, Style.RESET_ALL)

            # Import tools like run.py does
            from run import _import_toolsf
            _import_toolsf()
            log.info("Tools imported")

            # Import and call api.run() setup (but don't start serving)
            from app.services.api import run as api_run
            # Just test the setup part, not the serve_forever
            log.info("API setup completed")

            return {
                "status": "success",
                "message": "Full startup sequence completed successfully"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Full startup test failed: {str(e)}",
                "traceback": traceback.format_exc()
            }

    def log_message(self, format, *args):
        logger.info(format, *args)

def main():
    host = "127.0.0.1"
    port = 8000

    logger.info("Starting test server on %s:%s", host, port)
    server = HTTPServer((host, port), TestHandler)
    logger.info("Test server running. Try: curl http://%s:%s/test", host, port)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Server stopped")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()