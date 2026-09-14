#!/usr/bin/env python3
"""
Upgrade Ledger — append-only, fingerprint-deduplicated decision log.

Every planned or applied Continuum action is recorded with a SHA-256
fingerprint so the engine never re-proposes identical work.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set


class UpgradeLedger:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._seen: Set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    fp = rec.get("fingerprint")
                    if fp:
                        self._seen.add(fp)
                except json.JSONDecodeError:
                    continue

    def seen(self, fingerprint: str) -> bool:
        return fingerprint in self._seen

    def record(
        self,
        fingerprint: str,
        system_id: str,
        action_type: str,
        status: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a ledger entry. status: planned | proposed | applied | rejected | skipped."""
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "fingerprint": fingerprint,
            "system_id": system_id,
            "action_type": action_type,
            "status": status,
            "meta": meta or {},
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        self._seen.add(fingerprint)

    def count(self) -> int:
        return len(self._seen)
