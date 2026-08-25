#!/usr/bin/env python3
"""
Garcar Enterprise — HashiCorp Vault Client (KV v2)
Single source of truth for all secrets. GitHub Secrets is the distribution plane only.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import hvac
import requests


class GarcarVault:
    """Production client for HashiCorp Vault KV v2 under secret/garcar/*."""

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
        self.mount = mount or os.environ.get("VAULT_MOUNT", "secret")
        self.namespace = (namespace or os.environ.get("VAULT_NAMESPACE", "garcar")).rstrip("/")
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
        self.client.secrets.kv.v2.create_or_update_secret(
            path=self._path(key),
            secret=data,
            mount_point=self.mount,
        )

    def write_value(self, key: str, value: str, **extra: Any) -> None:
        payload = {"value": value, **extra}
        self.write(key, payload)

    def read(self, key: str) -> Dict[str, Any]:
        resp = self.client.secrets.kv.v2.read_secret_version(
            path=self._path(key),
            mount_point=self.mount,
        )
        return resp["data"]["data"]

    def read_value(self, key: str, field: str = "value") -> Optional[str]:
        try:
            data = self.read(key)
            if field in data:
                return data.get(field)
            # tolerate flat maps where the only key is the secret name
            if len(data) == 1:
                return next(iter(data.values()))
            return data.get(field)
        except Exception:
            return None

    def list_keys(self) -> List[str]:
        try:
            resp = self.client.secrets.kv.v2.list_secrets(
                path=self.namespace,
                mount_point=self.mount,
            )
            return list(resp.get("data", {}).get("keys", []) or [])
        except Exception:
            return []

    def delete(self, key: str) -> None:
        self.client.secrets.kv.v2.delete_latest_version_of_secret(
            path=self._path(key),
            mount_point=self.mount,
        )

    def health(self) -> Dict[str, Any]:
        try:
            r = requests.get(f"{self.addr}/v1/sys/health", timeout=5)
            return r.json()
        except Exception as e:
            return {"error": str(e)}

    def read_all(self) -> Dict[str, str]:
        """Return {SECRET_NAME: value} for every key under namespace."""
        out: Dict[str, str] = {}
        for key in self.list_keys():
            key = key.rstrip("/")
            val = self.read_value(key)
            if val is not None and str(val).strip() != "":
                out[key] = str(val)
        return out


def build_from_env() -> GarcarVault:
    return GarcarVault()


if __name__ == "__main__":
    v = build_from_env()
    print("Vault authenticated:", v.client.is_authenticated())
    print("Health:", v.health())
    print("Keys under garcar/:", v.list_keys())
