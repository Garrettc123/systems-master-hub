"""
DriftMonitor — reality contact for Garcar.
Detects when promoted policy loses contact with outcomes.
Never auto-demotes; only records and raises pressure for new candidates.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid


@dataclass
class DriftSignal:
    drift_type: str
    metric_name: str
    baseline_value: float
    current_value: float
    delta: float
    severity: str  # low | medium | high | critical
    genome_id: Optional[str] = None
    provider: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _severity(relative_drop: float) -> str:
    if relative_drop >= 0.40:
        return "critical"
    if relative_drop >= 0.25:
        return "high"
    if relative_drop >= 0.10:
        return "medium"
    return "low"


class DriftMonitor:
    def __init__(self, tolerances: Optional[Dict[str, float]] = None):
        self.tolerances = tolerances or {
            "performance": 0.10,
            "cost": 0.15,
            "agreement": 0.20,
        }
        self._signals: List[DriftSignal] = []

    def check_performance(
        self,
        baseline_score: float,
        current_score: float,
        genome_id: Optional[str] = None,
    ) -> Optional[DriftSignal]:
        if baseline_score <= 0:
            return None
        drop = (baseline_score - current_score) / baseline_score
        if drop < self.tolerances["performance"]:
            return None
        sig = DriftSignal(
            drift_type="performance",
            metric_name="fitness_score",
            baseline_value=baseline_score,
            current_value=current_score,
            delta=round(drop, 4),
            severity=_severity(drop),
            genome_id=genome_id,
            details={"relative_drop": drop},
        )
        self._signals.append(sig)
        return sig

    def check_cost(
        self,
        baseline_cpw: float,
        current_cpw: float,
        genome_id: Optional[str] = None,
    ) -> Optional[DriftSignal]:
        if baseline_cpw <= 0:
            return None
        rise = (current_cpw - baseline_cpw) / baseline_cpw
        if rise < self.tolerances["cost"]:
            return None
        sig = DriftSignal(
            drift_type="cost",
            metric_name="cost_per_won",
            baseline_value=baseline_cpw,
            current_value=current_cpw,
            delta=round(rise, 4),
            severity=_severity(rise),
            genome_id=genome_id,
            details={"relative_rise": rise},
        )
        self._signals.append(sig)
        return sig

    def check_agreement(
        self,
        baseline_rate: float,
        current_rate: float,
    ) -> Optional[DriftSignal]:
        if baseline_rate <= 0:
            return None
        drop = (baseline_rate - current_rate) / baseline_rate
        if drop < self.tolerances["agreement"]:
            return None
        sig = DriftSignal(
            drift_type="model",
            metric_name="cross_model_agreement_rate",
            baseline_value=baseline_rate,
            current_value=current_rate,
            delta=round(drop, 4),
            severity=_severity(drop),
            details={"relative_drop": drop},
        )
        self._signals.append(sig)
        return sig

    def drain(self) -> List[DriftSignal]:
        out = list(self._signals)
        self._signals.clear()
        return out
