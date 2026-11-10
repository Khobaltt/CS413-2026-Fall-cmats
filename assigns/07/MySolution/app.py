"""Run locally with python MySolution/app.py, from assigns/07."""
import json
from flask import Flask, jsonify, request
from dispatcher import dispatch
from errors import RpcError
from service import LambdaService

def reject_constant(value):
    raise ValueError("Non-JSON numeric constant")

def create_app(service=None):
    app = Flask(__name__)
    adapter = service if service is not None else LambdaService()
    app.config["MAX_CONTENT_LENGTH"] = 1_048_576

    @app.post("/rpc")
    def rpc():
        if request.mimetype != "application/json":
            return jsonify({"error": "Content-Type must be application/json"}), 415
        raw = request.get_data()
        try:
            # Strict UTF-8 and constants; Python's default accepts NaN/Infinity.
            payload = json.loads(raw.decode("utf-8"), parse_constant=reject_constant)
        except (ValueError, UnicodeError, RecursionError):
            return jsonify(RpcError(-32700, "Parse error").response(None)), 200
        response = dispatch(payload, adapter)
        if response is None:
            return "", 204
        return jsonify(response), 200

    return app

if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=8000, debug=False)
