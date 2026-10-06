"""Flask HTTP boundary: decode requests, call controller, serve the view."""
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.serving import make_server as wsgi_server
from controller import Controller

ROOT = Path(__file__).parent

def create_app(controller=None):
    controller = controller or Controller()
    app = Flask(__name__, static_folder=None)
    app.config['MAX_CONTENT_LENGTH'] = 1048576
    @app.after_request
    def headers(response):
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'"
        return response
    @app.get('/')
    def index():
        return send_from_directory(ROOT / 'static', 'index.html')
    @app.get('/<name>')
    def static_file(name):
        if name not in ('view.js', 'style.css'):
            return jsonify(error='Not found'), 404
        return send_from_directory(ROOT / 'static', name)
    @app.get('/api/state')
    def state():
        return jsonify(controller.state())
    @app.post('/api/command')
    def command():
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not isinstance(data.get('command'), str) or not isinstance(data.get('data', {}), dict):
            return jsonify(error='Invalid JSON command'), 400
        return jsonify(controller.request(data['command'], data.get('data', {})))
    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error='Request exceeds 1 MiB.'), 413
    return app

def make_server(port=8000, controller=None):
    return wsgi_server('127.0.0.1', port, create_app(controller), threaded=True)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    server = make_server(args.port)
    print(f'Open http://127.0.0.1:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
