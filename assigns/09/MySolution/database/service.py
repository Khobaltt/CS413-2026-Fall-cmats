from datetime import datetime, timezone
from uuid import uuid4

from .errors import ApiError
from .validation import check_revision, record_input

MAX_RECORDS = 100
MAX_CASES = 25


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def ensure_unique(records, name, except_id=None):
    if any(record["id"] != except_id and record["name"] == name for record in records):
        raise ApiError(409, "duplicate_name", "That name is already in use.")


def revise(record, changes):
    return {**record, **changes, "updated_at": timestamp(), "revision": record["revision"] + 1}


class Database:
    def __init__(self, store):
        self.store = store

    def _get(self, kind, record_id):
        record = self.store.get(kind, record_id)
        if record is None:
            raise ApiError(404, "record_not_found", "The record does not exist.")
        return record

    def _check_capacity(self):
        collections = self.store.records("collection")
        total = (len(self.store.records("program")) + len(collections)
                 + sum(len(record["cases"]) for record in collections))
        if total >= MAX_RECORDS:
            raise ApiError(409, "capacity_limit", "Total record capacity reached.")

    def list(self, kind, limit, cursor):
        with self.store.transaction:
            return self.store.page(kind, limit, cursor)

    def get(self, kind, record_id):
        with self.store.transaction:
            return self._get(kind, record_id)

    def create(self, kind, payload):
        values = record_input(kind, payload)
        with self.store.transaction:
            ensure_unique(self.store.records(kind), values["name"])
            self._check_capacity()
            now = timestamp()
            record = {"id": uuid4().hex, **values, "created_at": now,
                      "updated_at": now, "revision": 1}
            if kind == "collection":
                record["cases"] = []
            self.store.put(kind, record)
            return record

    def update(self, kind, record_id, match, read_body):
        with self.store.transaction:
            record = self._get(kind, record_id)
            check_revision(match, record["revision"])
            values = record_input(kind, read_body())
            ensure_unique(self.store.records(kind), values["name"], record_id)
            updated = revise(record, values)
            self.store.put(kind, updated)
            return updated

    def delete(self, kind, record_id, match):
        with self.store.transaction:
            record = self._get(kind, record_id)
            check_revision(match, record["revision"])
            self.store.delete(kind, record_id)

    def mutate_case(self, record_id, case_id, match, *, action, read_body=None):
        with self.store.transaction:
            collection = self._get("collection", record_id)
            cases = list(collection["cases"])
            position = None
            if case_id is not None:
                position = next((i for i, case in enumerate(cases) if case["id"] == case_id), None)
                if position is None:
                    raise ApiError(404, "record_not_found", "The case does not exist.")
            check_revision(match, collection["revision"])
            if action == "delete":
                del cases[position]
            else:
                values = record_input("case", read_body())
                ensure_unique(cases, values["name"], case_id)
                if action == "create":
                    if len(cases) >= MAX_CASES:
                        raise ApiError(409, "capacity_limit", "Collection case capacity reached.")
                    self._check_capacity()
                    cases.append({"id": uuid4().hex, **values})
                else:
                    cases[position] = {"id": case_id, **values}
            updated = revise(collection, {"cases": cases})
            self.store.put("collection", updated)
            return updated
