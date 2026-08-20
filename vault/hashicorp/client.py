#!/usr/bin/env python3
"""
Garcar Enterprise — HashiCorp Vault Client (KV v2)
Single source of truth for all secrets. GitHub Secrets is the distribution plane only.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

import hvac
import requests


class GarcarVault:
    """Minimal production client for HashiCorp Vault KV v2."""

    def __init__(
        self,
        addr: Optional[str] = None,
        token: Optional[str] = None,
        role_id: Optional[str] = None,
        secret_id: Optional[str] = None,
        mount: str = "secret",
        namespace: str = "garcar",
    ):
        self.addr = (addr or os.environ.get("VAULT_ADDR") or "").rstrip("/")
        self.mount = mount
        self.namespace = namespace.rstrip("/")
        self._token = token or os.environ.get("VAULT_TOKEN")
        self.role_id = role_id or os.environ.get("VAULT_ROLE_ID")
        self.secret_id = secret_id or os.environ.get("VAULT_SECRET_ID")

        if not self.addr:
            raise RuntimeError("VAULT_ADDR is required")

        self.client = hvac.Client(url=self.addr)
        self._authenticate()

    def _authenticate(self) -> None:
        if self._token:
            self.client.token = self._token
        elif self.role_id and self.secret_id:
            resp = self.client.auth.approle.login(
                role_id=self.role_id,
                secret_id=self.secret_id,
            )
            self._token = resp["auth"]["client_token"]
            self.client.token = self._token
        else:
            raise RuntimeError(
                "Provide VAULT_TOKEN or (VAULT_ROLE_ID + VAULT_SECRET_ID)"
            )

        if not self.client.is_authenticated():
            raise RuntimeError("Vault authentication failed")

    def _path(self, key: str) -> str:
        return f"{self.namespace}/{key}".strip("/")

    def write(self, key: str, data: Dict[str, Any]) -> None:
        """Write a secret (KV v2). Creates or updates."""
        self.client.secrets.kv.v2.create_or_update_secret(
            path=self._path(key),
            secret=data,
            mount_point=self.mount,
        )

    def read(self, key: str) -> Dict[str, Any]:
        """Read latest version of a secret."""
        resp = self.client.secrets.kv.v2.read_secret_version(
            path=self._path(key),
            mount_point=self.mount,
        )
        return resp["data"]["data"]

    def read_value(self, key: str, field: str = "value") -> Optional[str]:
        """Convenience: read a single field (default 'value')."""
        try:
            data = self.read(key)
            return data.get(field) or data.get(key)
        except Exception:
            return None

    def list_keys(self, prefix: str = "") -> List[str]:
        """List secret keys under namespace/prefix."""
        path = self._path(prefix) if prefix else self.namespace
        try:
            resp = self.client.secrets.kv.v2.list_secrets(
                path=path,
                mount_point=self.mount,
            )
            return resp.get("data", {}).get("keys", [])
        except Exception:
            return []

    def delete(self, key: str) -> None:
        """Soft-delete latest version (metadata retained)."""
        self.client.secrets.kv.v2.delete_latest_version_of_secret(
            path=self._path(key),
            mount_point=self.mount,
        )

    def health(self) -> Dict[str, Any]:
        """Vault health check."""
        try:
            r = requests.get(f"{self.addr}/v1/sys/health", timeout=5)
            return r.json()
        except Exception as e:
            return {"error": str(e)}


def build_from_env() -> GarcarVault:
    """Factory used by all Garcar agents and workflows."""
    return GarcarVault()


if __name__ == "__main__":
    # Quick connectivity test
    v = build_from_env()
    print("Vault authenticated:", v.client.is_authenticated())
    print("Health:", v.health())
    print("Keys under garcar/:", v.list_keys())
