import json
import re

from .errors import ApiError, invalid

MAX_SOURCE_BYTES = 16_384
MAX_DESCRIPTION = 2_000
MAX_NAME = 120
MAX_BODY_BYTES = 524_288
MAX_PAGE = 100
DEFAULT_PAGE = 50
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,64}")
CURSOR_PATTERN = re.compile(r"[0-9a-f]{32}")
TAG_PATTERN = re.compile(r'"[1-9][0-9]*"')
FIELDS = {
    "program": {"name", "source"},
    "collection": {"name"},
    "case": {"name", "source", "expected"},
}


def reject_constant(value):
    raise ValueError(f"invalid JSON constant {value}")


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate object key")
        result[key] = value
    return result


def parse_json(raw):
    try:
        return json.loads(raw.decode("utf-8"), parse_constant=reject_constant,
                          object_pairs_hook=unique_keys)
    except (ValueError, RecursionError):
        raise invalid("The request body must be valid UTF-8 JSON.") from None


def field_text(value, field, maximum, *, allow_blank, byte_limit=False):
    if not isinstance(value, str):
        raise invalid(f"{field} must be a string.")
    if not allow_blank and not value.strip():
        raise invalid(f"{field} must be nonempty.")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError:
        raise invalid(f"{field} contains invalid Unicode.") from None
    size = len(encoded) if byte_limit else len(value)
    if size > maximum:
        unit = "UTF-8 bytes" if byte_limit else "characters"
        raise invalid(f"{field} must be at most {maximum:,} {unit}.")
    return value


def expectation(value):
    if isinstance(value, dict):
        if value.keys() == {"kind", "value"} and value["kind"] == "value":
            return {"kind": "value", "value": field_text(
                value["value"], "expected.value", MAX_SOURCE_BYTES, allow_blank=True, byte_limit=True
            )}
        if (value.keys() == {"kind", "category"} and value["kind"] == "error"
                and value["category"] in ("syntax", "type")):
            return {"kind": "error", "category": value["category"]}
    raise invalid("expected must contain kind 'value' with a string value or kind 'error' with category 'syntax' or 'type'.")


def record_input(kind, payload):
    required = FIELDS[kind]
    if not isinstance(payload, dict):
        raise invalid("The request body must be a JSON object.")
    if payload.keys() - (required | {"description"}):
        raise invalid("The request body contains unknown fields.")
    missing = required - payload.keys()
    if missing:
        raise invalid("Missing fields: " + ", ".join(sorted(missing)) + ".")
    name = payload["name"]
    record = {
        "name": field_text(name.strip() if isinstance(name, str) else name,
                           "name", MAX_NAME, allow_blank=False),
        "description": field_text(payload.get("description", ""), "description",
                                  MAX_DESCRIPTION, allow_blank=True),
    }
    if "source" in required:
        record["source"] = field_text(payload["source"], "source", MAX_SOURCE_BYTES,
                                      allow_blank=False, byte_limit=True)
    if "expected" in required:
        record["expected"] = expectation(payload["expected"])
    return record


def revision_tag(revision):
    return f'"{revision}"'


def check_revision(header, revision):
    if header is None:
        raise ApiError(428, "precondition_required", "Send the current ETag in If-Match.")
    if TAG_PATTERN.fullmatch(header) is None:
        raise invalid('If-Match must be a quoted positive revision such as "1".')
    if header != revision_tag(revision):
        raise ApiError(409, "revision_conflict", "The record has changed.",
                       current_revision=revision)


def validate_id(value):
    if ID_PATTERN.fullmatch(value) is None:
        raise invalid("Invalid record ID.")


def page_input(args):
    if args.keys() - {"limit", "cursor"} or any(len(values) != 1 for _, values in args.lists()):
        raise invalid("Use only one limit and one cursor parameter.")
    raw_limit = args.get("limit", str(DEFAULT_PAGE))
    if re.fullmatch(r"[0-9]{1,3}", raw_limit) is None or not 1 <= int(raw_limit) <= MAX_PAGE:
        raise invalid(f"limit must be an integer from 1 to {MAX_PAGE}.")
    cursor = args.get("cursor")
    if cursor is not None and CURSOR_PATTERN.fullmatch(cursor) is None:
        raise invalid("Invalid cursor.")
    return int(raw_limit), cursor
