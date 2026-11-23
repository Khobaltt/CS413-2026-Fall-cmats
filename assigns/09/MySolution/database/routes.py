from flask import Blueprint, jsonify, request

from .errors import ApiError, invalid
from .validation import MAX_BODY_BYTES, page_input, parse_json, revision_tag, validate_id


def read_body():
    if request.mimetype != "application/json":
        raise ApiError(415, "unsupported_media_type", "Send Content-Type: application/json.")
    return parse_json(request.get_data(cache=False))


def item_response(kind, record, status=200):
    response = jsonify({kind: record})
    response.status_code = status
    response.headers["ETag"] = revision_tag(record["revision"])
    return response


def routes(database):
    api = Blueprint("database", __name__, url_prefix="/api/v1")

    @api.before_request
    def validate_request():
        if request.content_length is not None and request.content_length > MAX_BODY_BYTES:
            raise ApiError(413, "request_too_large", "The request body is too large.")
        is_list = (request.endpoint in {"database.programs", "database.collections"}
                   and request.method in ("GET", "HEAD"))
        if request.args and not is_list:
            raise invalid("This route does not accept query parameters.")

    @api.get("/health", provide_automatic_options=False)
    def health():
        return {"status": "ok", "version": "1.0"}

    def register_kind(kind):
        def list_or_create():
            if request.method == "POST":
                return item_response(kind, database.create(kind, read_body()), 201)
            limit, cursor = page_input(request.args)
            return database.list(kind, limit, cursor)

        def item(record_id):
            validate_id(record_id)
            match = request.headers.get("If-Match")
            if request.method == "PUT":
                return item_response(kind, database.update(kind, record_id, match, read_body))
            if request.method == "DELETE":
                database.delete(kind, record_id, match)
                return "", 204
            return item_response(kind, database.get(kind, record_id))

        base = kind + "s"
        api.add_url_rule("/" + base, base, list_or_create, methods=["GET", "POST"],
                         provide_automatic_options=False)
        api.add_url_rule("/" + base + "/<record_id>", kind, item, methods=["GET", "PUT", "DELETE"],
                         provide_automatic_options=False)

    register_kind("program")
    register_kind("collection")

    @api.post("/collections/<record_id>/cases", provide_automatic_options=False)
    def append_case(record_id):
        validate_id(record_id)
        collection = database.mutate_case(record_id, None, request.headers.get("If-Match"),
                                          action="create", read_body=read_body)
        return item_response("collection", collection, 201)

    @api.route("/collections/<record_id>/cases/<case_id>", methods=["PUT", "DELETE"],
               provide_automatic_options=False)
    def case_item(record_id, case_id):
        validate_id(record_id)
        validate_id(case_id)
        action = "delete" if request.method == "DELETE" else "update"
        collection = database.mutate_case(record_id, case_id, request.headers.get("If-Match"),
                                          action=action, read_body=read_body)
        return item_response("collection", collection)

    return api
