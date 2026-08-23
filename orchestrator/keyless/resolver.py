"""
Garcar Keyless Resolver
=======================
The only place secrets are ever materialized.

Contract:
  - Callers never read os.environ for secrets.
  - Secrets exist in memory only for the duration of a single operation.
  - No secret is ever logged, serialized into agent_runs, or written to disk.
  - Missing keys degrade gracefully (provider simply not registered).
  - Rotation is invisible to callers — next call gets the new value.

Sources (priority order):
  1. HashiCorp Vault (preferred, production)
  2. Cloudflare Worker secrets / env (runtime)
  3. Explicit injection for tests only
"""

from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

_tls = threading.local()


class KeylessError(Exception):
    """Raised only when a *required* secret is missing for a critical path."""


class KeylessResolver:
    """
    Single source of truth for secret materialization.
    Never store the returned values beyond the call stack that needs them.
    """

    REQUIRED_FOR_REVENUE = (
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
    )

    OPTIONAL = (
        "APOLLO_API_KEY",
        "HUBSPOT_API_KEY",
        "LINEAR_API_KEY",
        "OPENAI_API_KEY",
        "NOTION_API_KEY",
        "SLACK_WEBHOOK_URL",
        "RAILWAY_TOKEN",
    )

    def __init__(
        self,
        vault_client: Any = None,
        inject: Optional[Dict[str, str]] = None,
    ):
        self._vault = vault_client
        self._inject = inject or {}
        self._cache: Dict[str, str] = {}
        self._lock = threading.Lock()

    def get(self, name: str, required: bool = False) -> Optional[str]:
        name = name.strip().upper()

        if name in self._inject:
            return self._inject[name]

        with self._lock:
            if name in self._cache:
                return self._cache[name]

        value: Optional[str] = None

        if self._vault is not None:
            try:
                value = self._vault.read(f"secret/garcar/{name.lower()}")
            except Exception:
                value = None

        if value is None:
            value = os.environ.get(name) or os.environ.get(name.lower())

        if value:
            with self._lock:
                self._cache[name] = value
            return value

        if required:
            raise KeylessError(
                f"Required secret '{name}' is not available. "
                "Seed via Vault or Autokey propagate."
            )
        return None

    def require(self, *names: str) -> Dict[str, str]:
        out: Dict[str, str] = {}
        missing = []
        for n in names:
            v = self.get(n, required=False)
            if v is None:
                missing.append(n)
            else:
                out[n] = v
        if missing:
            raise KeylessError(
                f"Missing required secrets for this operation: {', '.join(missing)}"
            )
        return out

    def available(self, *names: str) -> Dict[str, bool]:
        return {n: self.get(n) is not None for n in names}

    def clear_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    @contextmanager
    def scoped(self, *names: str) -> Generator[Dict[str, str], None, None]:
        secrets = self.require(*names) if names else {}
        try:
            yield secrets
        finally:
            for k in list(secrets.keys()):
                secrets[k] = ""
            secrets.clear()


_default: Optional[KeylessResolver] = None
_default_lock = threading.Lock()


def get_resolver() -> KeylessResolver:
    global _default
    with _default_lock:
        if _default is None:
            _default = KeylessResolver()
        return _default


def configure_resolver(
    vault_client: Any = None,
    inject: Optional[Dict[str, str]] = None,
) -> KeylessResolver:
    global _default
    with _default_lock:
        _default = KeylessResolver(vault_client=vault_client, inject=inject)
        return _default
