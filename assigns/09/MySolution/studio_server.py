import json
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from flask import Blueprint, Response, send_from_directory

from database.errors import ApiError, invalid
from database.routes import read_body
from database.validation import MAX_SOURCE_BYTES, field_text

STUDIO = Path(__file__).resolve().parent / "studio"
MAX_RPC_RESPONSE = 262_144


def studio_routes(rpc_url):
    studio = Blueprint("studio", __name__)

    @studio.get("/")
    def index():
        return send_from_directory(STUDIO, "index.html")

    @studio.get("/studio/<path:filename>")
    def static_asset(filename):
        return send_from_directory(STUDIO, filename)

    @studio.post("/studio/interpret")
    def interpret():
        payload = read_body()
        if not isinstance(payload, dict) or payload.keys() != {"source"}:
            raise invalid("Send a JSON object containing only source.")
        source = field_text(payload["source"], "source", MAX_SOURCE_BYTES,
                            allow_blank=False, byte_limit=True)
        # forward only the fixed interpret operation to the configured service
        envelope = {"jsonrpc": "2.0", "id": 1, "method": "lambda.interpret",
                    "params": {"source": source}}
        outgoing = Request(rpc_url, json.dumps(envelope).encode("utf-8"),
                           {"Content-Type": "application/json"})
        try:
            with urlopen(outgoing, timeout=4) as upstream:
                result = upstream.read(MAX_RPC_RESPONSE + 1)
                if len(result) > MAX_RPC_RESPONSE or upstream.headers.get_content_type() != "application/json":
                    raise ValueError("invalid interpreter response")
        except (URLError, OSError, ValueError):
            raise ApiError(502, "lambda_unavailable", "LAMBDA3 is unavailable or returned an invalid response.") from None
        return Response(result, mimetype="application/json")

    return studio
