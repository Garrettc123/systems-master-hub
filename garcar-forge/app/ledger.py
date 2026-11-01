from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _canonical(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class EventLedger:
    """Single-node append-only API ledger with a verifiable hash chain.

    This detects modification or deletion when the expected chain head is
    retained independently. It is not WORM storage or a substitute for backups.
    """

    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        if self.path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = FULL")
        return conn

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    occurred_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE
                )
            """)

    @staticmethod
    def _hash(record: dict[str, Any]) -> str:
        return hashlib.sha256(_canonical(record).encode("utf-8")).hexdigest()

    def append(self, event_type: str, actor: str, payload: dict[str, Any]) -> dict[str, Any]:
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute(
                "SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            previous_hash = previous["event_hash"] if previous else "GENESIS"
            event = {
                "event_id": str(uuid.uuid4()),
                "occurred_at": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "actor": actor,
                "payload": payload,
                "previous_hash": previous_hash,
            }
            event_hash = self._hash(event)
            cursor = conn.execute(
                """INSERT INTO events
                   (event_id, occurred_at, event_type, actor, payload_json, previous_hash, event_hash)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    event["event_id"], event["occurred_at"], event_type, actor,
                    _canonical(payload), previous_hash, event_hash,
                ),
            )
            event["seq"] = cursor.lastrowid
            event["event_hash"] = event_hash
            conn.commit()
            return event
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def verify(self) -> dict[str, Any]:
        conn = self._connect()
        try:
            rows = conn.execute("SELECT * FROM events ORDER BY seq ASC").fetchall()
            expected_previous = "GENESIS"
            checked = 0
            for row in rows:
                event = {
                    "event_id": row["event_id"],
                    "occurred_at": row["occurred_at"],
                    "event_type": row["event_type"],
                    "actor": row["actor"],
                    "payload": json.loads(row["payload_json"]),
                    "previous_hash": row["previous_hash"],
                }
                if row["previous_hash"] != expected_previous:
                    return {"valid": False, "checked": checked, "failed_sequence": row["seq"]}
                computed = self._hash(event)
                if computed != row["event_hash"]:
                    return {"valid": False, "checked": checked, "failed_sequence": row["seq"]}
                expected_previous = computed
                checked += 1
            return {"valid": True, "checked": checked, "head": expected_previous}
        finally:
            conn.close()

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY seq DESC LIMIT ?", (max(1, min(limit, 200)),)
            ).fetchall()
            return [
                {
                    "seq": row["seq"],
                    "event_id": row["event_id"],
                    "occurred_at": row["occurred_at"],
                    "event_type": row["event_type"],
                    "actor": row["actor"],
                    "payload": json.loads(row["payload_json"]),
                    "previous_hash": row["previous_hash"],
                    "event_hash": row["event_hash"],
                }
                for row in rows
            ]
        finally:
            conn.close()
