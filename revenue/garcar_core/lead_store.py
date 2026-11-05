"""Atomic local lead idempotency with optional persistent SQLite WAL storage."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import RLock


class IdempotencyConflict(ValueError):
    pass


class LeadStore:
    def __init__(self, path=":memory:"):
        self.path = path
        self._lock = RLock()
        self._memory = None
        if path == ":memory:":
            self._memory = sqlite3.connect(path, timeout=15, check_same_thread=False)
        else:
            target = Path(path).expanduser().resolve()
            if not target.parent.exists():
                target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            # Create a new file privately without changing an existing file's permissions.
            try:
                descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                descriptor = None
            if descriptor is not None:
                os.close(descriptor)
            self.path = str(target)
        with self.connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS lead_events (
                tenant_id TEXT NOT NULL, idempotency_key TEXT NOT NULL,
                request_digest TEXT NOT NULL, lead_json TEXT NOT NULL,
                PRIMARY KEY(tenant_id,idempotency_key))""")

    @property
    def mode(self):
        return "memory" if self._memory is not None else "sqlite_wal"

    @contextmanager
    def connection(self):
        with self._lock:
            db = self._memory or sqlite3.connect(self.path, timeout=15)
            try:
                if self._memory is None:
                    db.execute("PRAGMA journal_mode=WAL")
                with db:
                    yield db
            finally:
                if self._memory is None:
                    db.close()

    def ingest(self, tenant_id, key, digest, build):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT request_digest,lead_json FROM lead_events WHERE tenant_id=? AND idempotency_key=?",
                             (tenant_id, key)).fetchone()
            if row:
                if row[0] != digest:
                    raise IdempotencyConflict("Idempotency key belongs to a different lead request")
                return json.loads(row[1])
            record = build()
            db.execute("INSERT INTO lead_events(tenant_id,idempotency_key,request_digest,lead_json) VALUES(?,?,?,?)",
                       (tenant_id, key, digest, json.dumps(record, sort_keys=True)))
            return record

    def close(self):
        if self._memory is not None:
            self._memory.close()
