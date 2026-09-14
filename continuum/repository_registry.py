#!/usr/bin/env python3
"""
Repository Registry normalizer for Continuum Grid.

Loads and canonicalizes SYSTEM_REGISTRY.json / capability-registry.json /
system-registry.yaml into a single auditable graph. Handles missing keys,
duplicates, and schema drift without mutating source files.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yaml  # optional
except ImportError:
    yaml = None  # type: ignore


@dataclass
class RepositoryRegistry:
    version: str = "unknown"
    source_path: str = ""
    systems: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    capability_weights: Dict[str, float] = field(default_factory=dict)
    warnings: list = field(default_factory=list)


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> Dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML not installed; cannot load YAML registry")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def normalize_registry(path: Path) -> RepositoryRegistry:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)

    if path.suffix in (".yaml", ".yml"):
        raw = _load_yaml(path)
    else:
        raw = _load_json(path)

    reg = RepositoryRegistry(
        version=str(raw.get("version", "unknown")),
        source_path=str(path),
        capability_weights=dict(raw.get("capability_weights") or {}),
    )

    systems_block = raw.get("systems") or raw.get("repos") or {}
    if isinstance(systems_block, list):
        # list-of-objects shape
        for item in systems_block:
            if not isinstance(item, dict):
                continue
            sid = item.get("system_id") or item.get("name") or item.get("id")
            if not sid:
                reg.warnings.append("list entry missing system_id")
                continue
            systems_block = {**({} if not isinstance(systems_block, dict) else systems_block), sid: item}

    if not isinstance(systems_block, dict):
        reg.warnings.append("systems block is not a dict; empty registry")
        return reg

    seen: Dict[str, str] = {}
    for key, entry in systems_block.items():
        if not isinstance(entry, dict):
            reg.warnings.append(f"{key}: entry is not object")
            continue
        system_id = str(entry.get("system_id") or key).strip().lower()
        if not system_id:
            reg.warnings.append(f"{key}: empty system_id")
            continue
        if system_id in seen:
            reg.warnings.append(f"duplicate system_id '{system_id}' (keys {seen[system_id]} and {key})")
        seen[system_id] = key

        # Canonical shape
        normalized = {
            "system_id": system_id,
            "name": entry.get("name") or system_id,
            "domain": entry.get("domain"),
            "role": entry.get("role"),
            "repo_url": entry.get("repo_url") or entry.get("url") or entry.get("repository"),
            "maturity_score": float(entry.get("maturity_score") or entry.get("score") or 0),
            "capabilities_complete": list(entry.get("capabilities_complete") or []),
            "capabilities_missing": list(entry.get("capabilities_missing") or []),
            "revenue_model": (entry.get("revenue") or {}).get("model")
            if isinstance(entry.get("revenue"), dict)
            else entry.get("revenue_model"),
            "monthly_target_usd": (entry.get("revenue") or {}).get("monthly_target_usd")
            if isinstance(entry.get("revenue"), dict)
            else entry.get("monthly_target_usd"),
            "attribution_code": entry.get("attribution_code")
            or (entry.get("revenue") or {}).get("attribution_code"),
            "raw": entry,
        }
        reg.systems[system_id] = normalized

    return reg


def dump_canonical(reg: RepositoryRegistry, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": reg.version,
        "source_path": reg.source_path,
        "capability_weights": reg.capability_weights,
        "warnings": reg.warnings,
        "systems": {
            sid: {k: v for k, v in data.items() if k != "raw"}
            for sid, data in sorted(reg.systems.items())
        },
    }
    out.write_text(json.dumps(payload, indent=2))
