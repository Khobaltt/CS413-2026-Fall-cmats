"""Local HTTP server. Run from assigns/08: python3 MySolution/app.py."""

"""JSON transport and same-origin static client."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from dispatcher import dispatch, error
from service import QueensService

STATIC = Path(__file__).resolve().parent / 'static'

def reject_constant(value):
    raise ValueError('Non-JSON numeric constant')

def decode(body):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate object key')
            result[key] = value
        return result
    return json.loads(body.decode('utf-8'), parse_constant=reject_constant,
                      object_pairs_hook=unique_pairs)

class Server(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, service=None):
        self.service = service if service is not None else QueensService()
        super().__init__(address, Handler)

    def service_actions(self):
        self.service.cleanup()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, status, body=b'', content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_POST(self):
        if urlsplit(self.path).path != '/rpc':
            self.respond(404)
            return
        if self.headers.get_content_type() != 'application/json':
            self.respond(415)
            return
        try:
            length = int(self.headers.get('Content-Length', '-1'))
            if not 0 <= length <= 65536:
                self.respond(413)
                return
            request = decode(self.rfile.read(length))
        except (ValueError, UnicodeError, RecursionError):
            response = error(-32700, 'Parse error')
        else:
            response = dispatch(request, self.server.service)
        if response is None:
            self.respond(204)
        else:
            self.respond(200, json.dumps(response, allow_nan=False).encode())

    def do_GET(self):
        # Fixed allowlist: no directory traversal or source-code serving.
        name = urlsplit(self.path).path
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/style.css': ('style.css', 'text/css; charset=utf-8'),
                 '/client.mjs': ('client.mjs', 'text/javascript; charset=utf-8')}
        if name not in files:
            self.respond(404)
            return
        filename, mime = files[name]
        self.respond(200, (STATIC / filename).read_bytes(), mime)