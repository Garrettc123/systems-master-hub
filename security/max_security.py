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
from typing import Callable


class SecurityDenied(Exception):
    """Raised whenever a security check cannot be positively satisfied."""


@dataclass(frozen=True)
class SecurityConfig:
    database: str
    bearer_token: bytes
    signing_key: bytes
    provisioning_key: bytes
    max_body_bytes: int = 65_536
    clock_skew_seconds: int = 60
    nonce_ttl_seconds: int = 300
    rate_limit: int = 60
    rate_window_seconds: int = 60

    def validate(self) -> None:
        if not isinstance(self.bearer_token, bytes) or len(self.bearer_token) < 32:
            raise ValueError("bearer_token must contain at least 32 random bytes")
        if not isinstance(self.signing_key, bytes) or len(self.signing_key) < 32:
            raise ValueError("signing_key must contain at least 32 random bytes")
        if not isinstance(self.provisioning_key, bytes) or len(self.provisioning_key) < 32:
            raise ValueError("provisioning_key must contain at least 32 random bytes")
        if len({self.bearer_token, self.signing_key, self.provisioning_key}) != 3:
            raise ValueError("bearer, signing, and provisioning keys must be different")
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

    @staticmethod
    def _epoch(value: object, field: str) -> int:
        """Accept only bounded Unix-second integers; reject bools and coercions."""
        if isinstance(value, bool) or not isinstance(value, int):
            raise SecurityDenied(f"invalid {field}")
        if value < 0 or value > 253402300799:
            raise SecurityDenied(f"invalid {field}")
        return value

    def verify_request(self, *, token: str, signature: str, method: str,
                       path: str, timestamp: int, nonce: str, body: bytes,
                       now: int | None = None) -> None:
        """Verify identity, body bound, signature, time window and one-time nonce."""
        now_value = int(time.time()) if now is None else now
        now_value = self._epoch(now_value, "current time")
        timestamp_value = self._epoch(timestamp, "request timestamp")
        if not self.authenticate(token):
            raise SecurityDenied("authentication failed")
        if not isinstance(body, bytes) or len(body) > self.config.max_body_bytes:
            raise SecurityDenied("request body rejected")
        if (not isinstance(method, str) or not method or
                not method.isascii() or not method.isalpha() or len(method) > 16):
            raise SecurityDenied("invalid HTTP method")
        if (not isinstance(path, str) or not path.startswith("/") or
                any(ord(ch) < 32 or ord(ch) == 127 for ch in path)):
            raise SecurityDenied("invalid request target")
        if (not isinstance(nonce, str) or not 24 <= len(nonce) <= 128 or
                not nonce.isascii() or not all(
                    ch.isalnum() or ch in "_-" for ch in nonce
                )):
            raise SecurityDenied("invalid nonce")
        if abs(now_value - timestamp_value) > self.config.clock_skew_seconds:
            raise SecurityDenied("request timestamp outside allowed window")
        expected = self.sign_request(method, path, timestamp_value, nonce, body)
        if (not isinstance(signature, str) or len(signature) != 64 or
                not all(ch in "0123456789abcdef" for ch in signature) or
                not hmac.compare_digest(expected, signature)):
            raise SecurityDenied("request signature invalid")

        # A unique primary key and BEGIN IMMEDIATE make nonce consumption atomic.
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("DELETE FROM security_nonces WHERE expires_at < ?", (now_value,))
                db.execute(
                    "INSERT INTO security_nonces(nonce, expires_at) VALUES (?, ?)",
                    (nonce, now_value + self.config.nonce_ttl_seconds),
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

    def _audit_in_transaction(self, db: sqlite3.Connection, event: str,
                              payload: dict) -> str:
        """Append a chained audit event inside the caller's open transaction."""
        if not isinstance(event, str) or not 0 < len(event) <= 128 or not isinstance(payload, dict):
            raise SecurityDenied("invalid audit event")
        try:
            encoded = self._canonical(payload).decode("utf-8")
            row = db.execute(
                "SELECT record_hash FROM security_audit ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous = row[0] if row else "0" * 64
            created = int(time.time())
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
            return digest
        except (sqlite3.Error, ValueError, TypeError, UnicodeError) as exc:
            raise SecurityDenied("audit ledger unavailable; operation blocked") from exc

    def _change_permission(self, principal: str, action: str, *,
                           admin_key: bytes, grant: bool) -> None:
        """Audit permission changes atomically with their database updates."""
        if (not isinstance(principal, str) or not 0 < len(principal) <= 200 or
                any(ord(ch) < 32 for ch in principal)):
            raise SecurityDenied("invalid principal")
        if (not isinstance(action, str) or not 0 < len(action) <= 200 or
                any(ord(ch) < 32 for ch in action)):
            raise SecurityDenied("invalid action")
        if (not isinstance(admin_key, bytes) or
                not hmac.compare_digest(admin_key, self.config.provisioning_key)):
            raise SecurityDenied("permission provisioning denied")
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                if grant:
                    changed = db.execute(
                        "INSERT OR IGNORE INTO security_permissions VALUES (?, ?)",
                        (principal, action),
                    ).rowcount
                else:
                    changed = db.execute(
                        "DELETE FROM security_permissions WHERE principal=? AND action=?",
                        (principal, action),
                    ).rowcount
                operation = "granted" if grant else "revoked"
                event = "permission_" + (operation if changed else "no_change")
                self._audit_in_transaction(db, event, {
                    "principal": principal, "action": action,
                    "requested_operation": operation,
                })
                db.commit()
        except sqlite3.Error as exc:
            raise SecurityDenied("permission store unavailable") from exc

    def grant_permission(self, principal: str, action: str, *,
                         admin_key: bytes) -> None:
        """Privileged local provisioning; never expose this method to agents or HTTP."""
        self._change_permission(principal, action, admin_key=admin_key, grant=True)

    def revoke_permission(self, principal: str, action: str, *,
                          admin_key: bytes) -> None:
        """Remove a grant, atomically recording the revocation in the audit chain."""
        self._change_permission(principal, action, admin_key=admin_key, grant=False)

    def authorize_operation(self, *, token: str, signature: str, method: str,
                            path: str, timestamp: int, nonce: str, body: bytes,
                            principal: str, action: str, rate_subject: str,
                            now: int | None = None,
                            approval_check: Callable[[], bool] | None = None) -> str:
        """Complete every security gate before the caller performs a side effect.

        This method authorizes but does not execute the operation. The caller must
        invoke it before any payment, email, deployment, write, or external action.
        """
        # Do not spend O(n) ledger-verification work on unauthenticated callers.
        if not self.authenticate(token):
            raise SecurityDenied("authentication failed")
        if not self.verify_audit_chain():
            raise SecurityDenied("audit chain integrity check failed")
        self.verify_request(
            token=token, signature=signature, method=method, path=path,
            timestamp=timestamp, nonce=nonce, body=body, now=now,
        )
        self.consume_rate_limit(rate_subject, now=now)
        self.require_permission(principal, action)
        if approval_check is not None:
            if not callable(approval_check):
                raise SecurityDenied("approval checker unavailable")
            try:
                approved = approval_check()
            except Exception as exc:
                raise SecurityDenied("approval verification unavailable") from exc
            if approved is not True:
                raise SecurityDenied("independent approval required")
        return self.append_audit("operation_authorized", {
            "principal": principal, "action": action,
            "method": method.upper(), "path": path,
            "body_sha256": hashlib.sha256(body).hexdigest(),
        })

    def require_permission(self, principal: str, action: str) -> None:
        if (not isinstance(principal, str) or not 0 < len(principal) <= 200 or
                not isinstance(action, str) or not 0 < len(action) <= 200):
            raise SecurityDenied("invalid principal or action")
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
        if (not isinstance(subject, str) or not 0 < len(subject) <= 256 or
                any(ord(ch) < 32 for ch in subject)):
            raise SecurityDenied("invalid rate-limit subject")
        now = self._epoch(int(time.time()) if now is None else now, "rate-limit time")
        window = now - (now % self.config.rate_window_seconds)
        digest = hmac.new(self.config.signing_key, subject.encode(), hashlib.sha256).hexdigest()
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
        """Append a tamper-evident record; any storage failure denies the caller."""
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                digest = self._audit_in_transaction(db, event, payload)
                db.commit()
                return digest
        except sqlite3.Error as exc:
            raise SecurityDenied("audit ledger unavailable; operation blocked") from exc

    def verify_audit_chain(self) -> bool:
        try:
            with self._connect() as db:
                rows = db.execute("""
                    SELECT sequence, created_at, event, payload, previous_hash, record_hash
                    FROM security_audit ORDER BY sequence
                """).fetchall()
            previous = "0" * 64
            for expected_sequence, (sequence, created, event, payload, prev, stored) in enumerate(rows, 1):
                if sequence != expected_sequence:
                    return False
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
    provisioning = os.environ.get("GARCAR_PERMISSION_ADMIN_KEY")
    if not token or not signing or not provisioning:
        raise SecurityDenied("required security secrets are not configured")
    return SecurityConfig(database=database, bearer_token=token.encode(),
                          signing_key=signing.encode(),
                          provisioning_key=provisioning.encode())
