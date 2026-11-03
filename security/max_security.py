"""Fail-closed security primitives for Garcar Enterprise.

Standard-library only. This module is a security building block, not a complete
network perimeter or substitute for TLS, OS isolation, independent review,
or host-level authorization.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


class SecurityDenied(Exception):
    """Raised whenever a security check cannot be positively satisfied."""


@dataclass(frozen=True)
class SecurityConfig:
    database: str
    bearer_token: bytes
    signing_key: bytes
    max_body_bytes: int = 65_536
    clock_skew_seconds: int = 60
    nonce_ttl_seconds: int = 300
    rate_limit: int = 60
    rate_window_seconds: int = 60

    def validate(self) -> None:
        if len(self.bearer_token) < 32:
            raise ValueError("bearer_token must contain at least 32 random bytes")
        if len(self.signing_key) < 32:
            raise ValueError("signing_key must contain at least 32 random bytes")
        if self.max_body_bytes < 1 or self.clock_skew_seconds < 1:
            raise ValueError("security limits must be positive")
        if self.nonce_ttl_seconds < self.clock_skew_seconds:
            raise ValueError("nonce TTL must be at least the clock-skew window")
        if self.rate_limit < 1 or self.rate_window_seconds < 1:
            raise ValueError("rate limits must be positive")


class MaxSecurityEngine:
    """Persistent replay defense, authorization, rate limiting and audit chain."""

    def __init__(self, config: SecurityConfig):
        config.validate()
        self.config = config
        Path(config.database).parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.config.database, timeout=10, isolation_level=None)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("PRAGMA foreign_keys=ON")
            yield db
        finally:
            db.close()

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS security_nonces (
                    nonce TEXT PRIMARY KEY,
                    expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS security_buckets (
                    subject_hash TEXT NOT NULL,
                    window_start INTEGER NOT NULL,
                    count INTEGER NOT NULL,
                    PRIMARY KEY(subject_hash, window_start)
                );
                CREATE TABLE IF NOT EXISTS security_audit (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at INTEGER NOT NULL,
                    event TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    record_hash TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS security_permissions (
                    principal TEXT NOT NULL,
                    action TEXT NOT NULL,
                    PRIMARY KEY(principal, action)
                );
            """)

    @staticmethod
    def _canonical(value: object) -> bytes:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False).encode("utf-8")

    def authenticate(self, supplied_token: str) -> bool:
        if not isinstance(supplied_token, str):
            return False
        try:
            candidate = supplied_token.encode("utf-8")
        except UnicodeError:
            return False
        return secrets.compare_digest(candidate, self.config.bearer_token)

    def sign_request(self, method: str, path: str, timestamp: int,
                     nonce: str, body: bytes) -> str:
        body_hash = hashlib.sha256(body).hexdigest()
        message = "\n".join((method.upper(), path, str(timestamp), nonce, body_hash))
        return hmac.new(self.config.signing_key, message.encode(),
                        hashlib.sha256).hexdigest()

    def verify_request(self, *, token: str, signature: str, method: str,
                       path: str, timestamp: int, nonce: str, body: bytes,
                       now: int | None = None) -> None:
        """Verify identity, body bound, signature, time window and one-time nonce."""
        now = int(time.time()) if now is None else int(now)
        if not self.authenticate(token):
            raise SecurityDenied("authentication failed")
        if not isinstance(body, bytes) or len(body) > self.config.max_body_bytes:
            raise SecurityDenied("request body rejected")
        if not method or not path.startswith("/") or "\n" in path:
            raise SecurityDenied("invalid request target")
        if not isinstance(nonce, str) or len(nonce) < 24 or len(nonce) > 128:
            raise SecurityDenied("invalid nonce")
        if abs(now - int(timestamp)) > self.config.clock_skew_seconds:
            raise SecurityDenied("request timestamp outside allowed window")
        expected = self.sign_request(method, path, int(timestamp), nonce, body)
        if not isinstance(signature, str) or not hmac.compare_digest(expected, signature):
            raise SecurityDenied("request signature invalid")

        # A unique primary key and BEGIN IMMEDIATE make nonce consumption atomic.
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("DELETE FROM security_nonces WHERE expires_at < ?", (now,))
                db.execute(
                    "INSERT INTO security_nonces(nonce, expires_at) VALUES (?, ?)",
                    (nonce, now + self.config.nonce_ttl_seconds),
                )
                db.commit()
        except sqlite3.IntegrityError as exc:
            raise SecurityDenied("replayed request") from exc
        except sqlite3.Error as exc:
            raise SecurityDenied("replay protection unavailable") from exc
        self.append_audit("request_verified", {
            "method": method.upper(), "path": path,
            "body_sha256": hashlib.sha256(body).hexdigest(),
        })

    def grant_permission(self, principal: str, action: str) -> None:
        """Administrative provisioning only; do not expose as an untrusted API."""
        if not principal or not action:
            raise ValueError("principal and action are required")
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO security_permissions VALUES (?, ?)",
                       (principal, action))

    def require_permission(self, principal: str, action: str) -> None:
        if not principal or not action:
            raise SecurityDenied("missing principal or action")
        try:
            with self._connect() as db:
                row = db.execute(
                    "SELECT 1 FROM security_permissions WHERE principal=? AND action=?",
                    (principal, action),
                ).fetchone()
            if row is None:
                self.append_audit("authorization_denied", {
                    "principal": principal, "action": action,
                })
                raise SecurityDenied("permission denied")
            self.append_audit("authorization_granted", {
                "principal": principal, "action": action,
            })
        except sqlite3.Error as exc:
            raise SecurityDenied("authorization store unavailable") from exc

    def consume_rate_limit(self, subject: str, *, now: int | None = None) -> None:
        """Persistent fixed-window limit; subject is stored only as a digest."""
        if not subject:
            raise SecurityDenied("missing rate-limit subject")
        now = int(time.time()) if now is None else int(now)
        window = now - (now % self.config.rate_window_seconds)
        digest = hashlib.sha256(subject.encode()).hexdigest()
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("""
                    INSERT INTO security_buckets(subject_hash, window_start, count)
                    VALUES (?, ?, 1)
                    ON CONFLICT(subject_hash, window_start)
                    DO UPDATE SET count=count+1
                """, (digest, window))
                count = db.execute(
                    "SELECT count FROM security_buckets WHERE subject_hash=? AND window_start=?",
                    (digest, window),
                ).fetchone()[0]
                db.execute("DELETE FROM security_buckets WHERE window_start < ?",
                           (window - self.config.rate_window_seconds,))
                db.commit()
            if count > self.config.rate_limit:
                self.append_audit("rate_limit_denied", {"subject_hash": digest})
                raise SecurityDenied("rate limit exceeded")
        except sqlite3.Error as exc:
            raise SecurityDenied("rate limiter unavailable") from exc

    def append_audit(self, event: str, payload: dict) -> str:
        """Append a tamper-evident record; any storage failure is fatal to caller."""
        if not event or not isinstance(payload, dict):
            raise SecurityDenied("invalid audit event")
        encoded = self._canonical(payload).decode("utf-8")
        created = int(time.time())
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT record_hash FROM security_audit ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                previous = row[0] if row else "0" * 64
                material = self._canonical({
                    "created_at": created, "event": event,
                    "payload": json.loads(encoded), "previous_hash": previous,
                })
                digest = hashlib.sha256(material).hexdigest()
                db.execute("""
                    INSERT INTO security_audit
                    (created_at, event, payload, previous_hash, record_hash)
                    VALUES (?, ?, ?, ?, ?)
                """, (created, event, encoded, previous, digest))
                db.commit()
            return digest
        except (sqlite3.Error, ValueError, TypeError) as exc:
            raise SecurityDenied("audit ledger unavailable; operation blocked") from exc

    def verify_audit_chain(self) -> bool:
        try:
            with self._connect() as db:
                rows = db.execute("""
                    SELECT created_at, event, payload, previous_hash, record_hash
                    FROM security_audit ORDER BY sequence
                """).fetchall()
            previous = "0" * 64
            for created, event, payload, prev, stored in rows:
                if not hmac.compare_digest(prev, previous):
                    return False
                material = self._canonical({
                    "created_at": created, "event": event,
                    "payload": json.loads(payload), "previous_hash": prev,
                })
                calculated = hashlib.sha256(material).hexdigest()
                if not hmac.compare_digest(calculated, stored):
                    return False
                previous = stored
            return True
        except (sqlite3.Error, ValueError, TypeError):
            return False


def load_config_from_environment(database: str = "data/security.sqlite3") -> SecurityConfig:
    """Load secrets from environment; never generate or overwrite production secrets."""
    token = os.environ.get("GARCAR_BEARER_TOKEN")
    signing = os.environ.get("GARCAR_SIGNING_KEY")
    if not token or not signing:
        raise SecurityDenied("required security secrets are not configured")
    return SecurityConfig(database=database, bearer_token=token.encode(),
                          signing_key=signing.encode())
