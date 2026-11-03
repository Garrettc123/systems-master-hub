"""Offline HMAC-authenticated checkpoint for a local SQLite audit chain.

Checkpoint files MUST be copied to independently controlled append-only storage.
A local signed file alone is not WORM retention or a tamper-proof ledger.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import time

from security.max_security import MaxSecurityEngine, SecurityDenied


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _check_key(key: bytes) -> None:
    if not isinstance(key, bytes) or len(key) < 32:
        raise SecurityDenied("independent checkpoint key is required")


def _snapshot(engine: MaxSecurityEngine) -> tuple[int, str, list[str]]:
    """Read and validate a consistent local audit snapshot under a write lock."""
    try:
        with engine._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            rows = db.execute(
                "SELECT sequence, created_at, event, payload, previous_hash, record_hash "
                "FROM security_audit ORDER BY sequence"
            ).fetchall()
            previous = "0" * 64
            record_hashes = []
            for expected, (seq, created, event, payload, prev, stored) in enumerate(rows, 1):
                if seq != expected or not hmac.compare_digest(prev, previous):
                    raise SecurityDenied("local audit chain broken")
                material = _canonical({
                    "created_at": created, "event": event,
                    "payload": json.loads(payload), "previous_hash": prev,
                })
                calculated = hashlib.sha256(material).hexdigest()
                if not hmac.compare_digest(calculated, stored):
                    raise SecurityDenied("local audit chain broken")
                previous = stored
                record_hashes.append(stored)
            db.commit()
            return len(rows), previous, record_hashes
    except (sqlite3.Error, ValueError, TypeError, UnicodeError) as exc:
        raise SecurityDenied("audit checkpoint snapshot unavailable") from exc


def create_checkpoint(engine: MaxSecurityEngine, checkpoint_key: bytes,
                      *, now: int | None = None) -> dict:
    """Create serializable signed evidence; no network calls or disk writes."""
    _check_key(checkpoint_key)
    count, head, _ = _snapshot(engine)
    created = int(time.time()) if now is None else now
    created = engine._epoch(created, "checkpoint time")
    payload = {
        "version": 1,
        "sequence": count,
        "head_hash": head,
        "created_at": created,
        "algorithm": "HMAC-SHA256",
    }
    signature = hmac.new(checkpoint_key, _canonical(payload), hashlib.sha256).hexdigest()
    return {"payload": payload, "signature": signature}


def verify_checkpoint(engine: MaxSecurityEngine, checkpoint_key: bytes,
                      checkpoint: object) -> bool:
    """Verify signature and historic prefix against the current audit ledger."""
    _check_key(checkpoint_key)
    if not isinstance(checkpoint, dict) or set(checkpoint) != {"payload", "signature"}:
        return False
    payload, signature = checkpoint["payload"], checkpoint["signature"]
    if not isinstance(payload, dict) or set(payload) != {
        "version", "sequence", "head_hash", "created_at", "algorithm",
    } or not isinstance(signature, str) or len(signature) != 64:
        return False
    if (payload["version"] != 1 or type(payload["sequence"]) is not int
            or payload["sequence"] < 0 or payload["algorithm"] != "HMAC-SHA256"
            or type(payload["created_at"]) is not int):
        return False
    try:
        expected = hmac.new(checkpoint_key, _canonical(payload), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False
        count, _, hashes = _snapshot(engine)
        if payload["sequence"] > count:
            return False
        actual = hashes[payload["sequence"] - 1] if payload["sequence"] else "0" * 64
        return (isinstance(payload["head_hash"], str)
                and hmac.compare_digest(payload["head_hash"], actual))
    except (SecurityDenied, ValueError, TypeError, UnicodeError):
        return False
