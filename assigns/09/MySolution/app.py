import os

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from database.errors import ApiError
from database.routes import routes
from database.service import Database
from database.storage import MemoryStore
from database.validation import MAX_BODY_BYTES
from studio_server import studio_routes

HTTP_CODES = {
    400: ("invalid_request", "The request is invalid."),
    404: ("record_not_found", "The route does not exist."),
    405: ("method_not_allowed", "The route does not support this method."),
    413: ("request_too_large", "The request body is too large."),
    415: ("unsupported_media_type", "The media type is unsupported."),
    500: ("internal_error", "An unexpected error occurred."),
}


def create_app(store=None, *, rpc_url=None):
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = MAX_BODY_BYTES
    database = Database(store if store is not None else MemoryStore())
    app.register_blueprint(routes(database))
    if rpc_url is None:
        rpc_url = os.environ.get("LAMBDA_RPC_URL", "http://127.0.0.1:8000/rpc")
    app.register_blueprint(studio_routes(rpc_url))

    @app.errorhandler(ApiError)
    def api_error(error):
        return jsonify(error.body), error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        status = error.code
        code, message = HTTP_CODES.get(status, ("invalid_request", "The request could not be handled."))
        response = jsonify({"error": {"code": code, "message": message}})
        response.status_code = status
        if status == 405 and error.valid_methods:
            response.headers["Allow"] = ", ".join(sorted(error.valid_methods))
        return response

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=9000)
