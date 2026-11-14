from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def canonical(value: dict[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class EventLedger:
    """Single-node SQLite event and job store with a verifiable event hash chain.

    The chain detects edits to retained history, but it is not WORM storage.
    Export and retain the chain head separately to detect truncation of the tail.
    This store is intentionally single-host; use PostgreSQL for multi-host work.
    """

    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 15000")
        if self.path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = FULL")
        return conn

    def initialize(self) -> None:
        conn = self.connect()
        try:
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL UNIQUE,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    task_name TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed')),
                    attempt_count INTEGER NOT NULL DEFAULT 0,
                    worker_id TEXT,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    result_json TEXT,
                    error_code TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_status_seq ON jobs(status, seq)")
        finally:
            conn.close()

    @staticmethod
    def _hash(record: dict[str, Any]) -> str:
        return hashlib.sha256(canonical(record).encode("utf-8")).hexdigest()

    def append_in_transaction(
        self, conn: sqlite3.Connection, event_type: str, actor: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        previous = conn.execute(
            "SELECT event_hash FROM events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous["event_hash"] if previous else "GENESIS"
        event = {
            "event_id": str(uuid.uuid4()), "occurred_at": utc_now(),
            "event_type": event_type, "actor": actor, "payload": payload,
            "previous_hash": previous_hash,
        }
        event_hash = self._hash(event)
        cursor = conn.execute(
            """INSERT INTO events
               (event_id, occurred_at, event_type, actor, payload_json, previous_hash, event_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (event["event_id"], event["occurred_at"], event_type, actor,
             canonical(payload), previous_hash, event_hash),
        )
        return {**event, "seq": cursor.lastrowid, "event_hash": event_hash}

    def append(self, event_type: str, actor: str, payload: dict[str, Any]) -> dict[str, Any]:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            event = self.append_in_transaction(conn, event_type, actor, payload)
            conn.commit()
            return event
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def verify(self) -> dict[str, Any]:
        conn = self.connect()
        try:
            rows = conn.execute("SELECT * FROM events ORDER BY seq ASC").fetchall()
            expected_previous = "GENESIS"
            checked = 0
            for row in rows:
                event = {
                    "event_id": row["event_id"], "occurred_at": row["occurred_at"],
                    "event_type": row["event_type"], "actor": row["actor"],
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
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM events ORDER BY seq DESC LIMIT ?", (max(1, min(limit, 200)),)
            ).fetchall()
            return [
                {"seq": row["seq"], "event_id": row["event_id"],
                 "occurred_at": row["occurred_at"], "event_type": row["event_type"],
                 "actor": row["actor"], "payload": json.loads(row["payload_json"]),
                 "previous_hash": row["previous_hash"], "event_hash": row["event_hash"]}
                for row in rows
            ]
        finally:
            conn.close()

    def enqueue(self, task_name: str, idempotency_key: str,
                payload: dict[str, Any]) -> tuple[dict[str, Any], bool, bool]:
        """Return job, created flag, and same-request flag for idempotent submissions."""
        payload_json = canonical(payload)
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM jobs WHERE idempotency_key = ?", (idempotency_key,)
            ).fetchone()
            if row:
                conn.commit()
                return self._job_dict(row), False, (
                    row["task_name"] == task_name and row["payload_json"] == payload_json
                )
            job_id = str(uuid.uuid4())
            now = utc_now()
            conn.execute(
                """INSERT INTO jobs
                   (job_id,idempotency_key,task_name,payload_json,status,created_at)
                   VALUES (?,?,?,?, 'queued', ?)""",
                (job_id, idempotency_key, task_name, payload_json, now),
            )
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            self.append_in_transaction(conn, "job.queued", "operator", {
                "job_id": job_id, "task_name": task_name, "idempotency_key": idempotency_key
            })
            conn.commit()
            return self._job_dict(row), True, True
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _job_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "job_id": row["job_id"], "task_name": row["task_name"],
            "payload": json.loads(row["payload_json"]), "status": row["status"],
            "attempt_count": row["attempt_count"], "worker_id": row["worker_id"],
            "created_at": row["created_at"], "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "result": json.loads(row["result_json"]) if row["result_json"] else None,
            "error_code": row["error_code"],
        }

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        conn = self.connect()
        try:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            return self._job_dict(row) if row else None
        finally:
            conn.close()

    def claim_job(self, worker_id: str, lease_seconds: int = 300,
                  max_attempts: int = 3) -> dict[str, Any] | None:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            now = datetime.now(UTC)
            cutoff = (now - timedelta(seconds=max(1, lease_seconds))).isoformat()
            expired = conn.execute(
                """SELECT job_id FROM jobs
                   WHERE status='running' AND started_at < ? AND attempt_count >= ?""",
                (cutoff, max_attempts),
            ).fetchall()
            for item in expired:
                conn.execute(
                    """UPDATE jobs SET status='failed', error_code='job_lease_expired_max_attempts',
                       finished_at=? WHERE job_id=? AND status='running'""",
                    (now.isoformat(), item["job_id"]),
                )
                self.append_in_transaction(conn, "job.failed", worker_id, {
                    "job_id": item["job_id"], "error_code": "job_lease_expired_max_attempts"
                })
            row = conn.execute(
                """SELECT * FROM jobs
                   WHERE status='queued'
                      OR (status='running' AND started_at < ? AND attempt_count < ?)
                   ORDER BY seq ASC LIMIT 1""",
                (cutoff, max_attempts),
            ).fetchone()
            if row is None:
                conn.commit()
                return None
            attempt = row["attempt_count"] + 1
            conn.execute(
                """UPDATE jobs SET status='running', worker_id=?, started_at=?,
                   attempt_count=? WHERE job_id=?""",
                (worker_id, now.isoformat(), attempt, row["job_id"]),
            )
            claimed = conn.execute(
                "SELECT * FROM jobs WHERE job_id=?", (row["job_id"],)
            ).fetchone()
            self.append_in_transaction(conn, "job.claimed", worker_id, {
                "job_id": row["job_id"], "attempt_count": attempt
            })
            conn.commit()
            return self._job_dict(claimed)
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def finish_job(self, job_id: str, worker_id: str, result: dict[str, Any]) -> bool:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """UPDATE jobs SET status='succeeded', result_json=?, finished_at=?
                   WHERE job_id=? AND worker_id=? AND status='running'""",
                (canonical(result), utc_now(), job_id, worker_id),
            )
            if cursor.rowcount == 1:
                self.append_in_transaction(conn, "job.succeeded", worker_id,
                                           {"job_id": job_id, "result": result})
            conn.commit()
            return cursor.rowcount == 1
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def fail_job(self, job_id: str, worker_id: str, error_code: str) -> bool:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            cursor = conn.execute(
                """UPDATE jobs SET status='failed', error_code=?, finished_at=?
                   WHERE job_id=? AND worker_id=? AND status='running'""",
                (error_code, utc_now(), job_id, worker_id),
            )
            if cursor.rowcount == 1:
                self.append_in_transaction(conn, "job.failed", worker_id,
                                           {"job_id": job_id, "error_code": error_code})
            conn.commit()
            return cursor.rowcount == 1
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
