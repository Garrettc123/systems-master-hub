"""
SynchronicityDetector — observational only.
Records emergent alignment. Never mutates production policy.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class SynchronicityEvent:
    event_type: str
    strength: float
    participants: Dict[str, Any]
    shared_signal: Optional[Dict[str, Any]] = None
    economic_value: Optional[float] = None
    explained: str = ""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    observed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SynchronicityDetector:
    def __init__(self, agreement_threshold: float = 0.75):
        self.agreement_threshold = agreement_threshold
        self._buffer: List[SynchronicityEvent] = []

    def observe_model_outputs(
        self,
        task_id: str,
        responses: List[Dict[str, Any]],
    ) -> Optional[SynchronicityEvent]:
        ok = [r for r in responses if r.get("content") and not r.get("error")]
        if len(ok) < 2:
            return None
        # Simple agreement proxy: multiple ok responses on same task
        strength = min(1.0, len(ok) / max(len(responses), 1))
        if strength < self.agreement_threshold:
            return None
        event = SynchronicityEvent(
            event_type="cross_model",
            strength=round(strength, 4),
            participants={
                "task_id": task_id,
                "providers": [r.get("provider") for r in ok],
                "models": [r.get("model") for r in ok],
            },
            shared_signal={"n_agreeing": len(ok)},
            explained=f"{len(ok)} providers aligned on task {task_id}",
        )
        self._buffer.append(event)
        return event

    def observe_genome_convergence(
        self,
        genomes: List[Dict[str, Any]],
        shared_rule_id: str,
    ) -> Optional[SynchronicityEvent]:
        if len(genomes) < 2:
            return None
        event = SynchronicityEvent(
            event_type="cross_genome",
            strength=min(1.0, len(genomes) / 3.0),
            participants={
                "genome_ids": [g.get("genome_id") or g.get("id") for g in genomes],
                "rule_id": shared_rule_id,
            },
            shared_signal={"rule_id": shared_rule_id},
            explained=f"Independent genomes converged on rule {shared_rule_id}",
        )
        self._buffer.append(event)
        return event

    def drain(self) -> List[SynchronicityEvent]:
        events = list(self._buffer)
        self._buffer.clear()
        return events
