from dataclasses import dataclass, field
from threading import RLock
from uuid import uuid4

from .errors import ApiError, invalid

MAX_SNAPSHOTS = 64


@dataclass
class Snapshot:
    records: tuple
    tokens_by_offset: dict[int, str] = field(default_factory=dict)


class MemoryStore:
    def __init__(self):
        self.transaction = RLock()
        self._records = {"program": {}, "collection": {}}
        self._snapshots = {}
        self._cursors = {}

    def get(self, kind, record_id):
        return self._records[kind].get(record_id)

    def records(self, kind):
        return tuple(self._records[kind].values())

    def put(self, kind, record):
        # replace records so older snapshots keep the versions they captured
        self._records[kind][record["id"]] = record

    def delete(self, kind, record_id):
        del self._records[kind][record_id]

    def page(self, kind, limit, cursor):
        if cursor is None:
            records = self.records(kind)
            if len(records) <= limit:
                return {"items": list(records), "next_cursor": None}
            key = kind, tuple((record["id"], record["revision"]) for record in records)
            snapshot = self._snapshots.get(key)
            if snapshot is None:
                if len(self._snapshots) >= MAX_SNAPSHOTS:
                    raise ApiError(409, "capacity_limit", "Pagination snapshot capacity reached.")
                snapshot = self._snapshots[key] = Snapshot(records)
            offset = 0
        else:
            saved = self._cursors.get(cursor)
            if saved is None or saved[0] != kind:
                raise invalid("Invalid cursor for this resource.")
            _, snapshot, offset = saved

        stop = offset + limit
        next_cursor = None
        if stop < len(snapshot.records):
            next_cursor = snapshot.tokens_by_offset.get(stop)
            if next_cursor is None:
                next_cursor = snapshot.tokens_by_offset[stop] = uuid4().hex
                self._cursors[next_cursor] = (kind, snapshot, stop)
        return {"items": list(snapshot.records[offset:stop]), "next_cursor": next_cursor}
