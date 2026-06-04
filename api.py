import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from monitor import load_log

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/status":
            try:
                log = load_log()
                data = json.dumps(log)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data.encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

def start_api():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print("[API] Server running on port " + str(port), flush=True)
    server.serve_forever()
