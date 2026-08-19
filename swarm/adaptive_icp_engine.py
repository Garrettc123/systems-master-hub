"""Adaptive ICP learning engine for the integrated autonomous swarm.

The engine turns observed commercial outcomes into a continuously updated ICP
score. It is intentionally deterministic at the scoring boundary so model
outputs can be audited and replaced without changing the decision contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from typing import Dict, Iterable, Mapping


SIGNAL_WEIGHTS: Dict[str, float] = {
    "pain_severity": 0.20,
    "ability_to_pay": 0.20,
    "lead_volume": 0.15,
    "operational_inefficiency": 0.15,
    "buying_urgency": 0.10,
    "decision_maker_access": 0.10,
    "retention_potential": 0.10,
}


@dataclass(frozen=True)
class ProspectObservation:
    """Normalized evidence collected by swarm agents."""

    segment: str
    signals: Mapping[str, float]
    outcome: str | None = None
    contract_value: float = 0.0
    acquisition_cost: float = 0.0
    retained: bool | None = None


@dataclass
class SegmentState:
    """Online state for one market segment."""

    observations: int = 0
    wins: int = 0
    losses: int = 0
    revenue: float = 0.0
    acquisition_cost: float = 0.0
    retention_events: int = 0
    retention_successes: int = 0
    signal_means: Dict[str, float] = field(default_factory=dict)


class AdaptiveICPEngine:
    """Continuously rank market segments from real observed outcomes."""

    def __init__(self, weights: Mapping[str, float] | None = None) -> None:
        self.weights = dict(weights or SIGNAL_WEIGHTS)
        if abs(sum(self.weights.values()) - 1.0) > 1e-9:
            raise ValueError("ICP weights must sum to 1.0")
        self.segments: Dict[str, SegmentState] = {}

    def ingest(self, observation: ProspectObservation) -> None:
        state = self.segments.setdefault(observation.segment, SegmentState())
        state.observations += 1
        state.revenue += max(0.0, observation.contract_value)
        state.acquisition_cost += max(0.0, observation.acquisition_cost)

        if observation.outcome == "won":
            state.wins += 1
        elif observation.outcome == "lost":
            state.losses += 1

        if observation.retained is not None:
            state.retention_events += 1
            state.retention_successes += int(observation.retained)

        for name, value in observation.signals.items():
            value = min(1.0, max(0.0, float(value)))
            old = state.signal_means.get(name, 0.0)
            n = state.observations
            state.signal_means[name] = old + (value - old) / n

    def score(self, segment: str) -> float:
        state = self.segments[segment]
        signal_score = sum(
            self.weights.get(name, 0.0) * state.signal_means.get(name, 0.0)
            for name in self.weights
        )
        total_outcomes = state.wins + state.losses
        win_rate = state.wins / total_outcomes if total_outcomes else 0.5
        retention = (
            state.retention_successes / state.retention_events
            if state.retention_events
            else 0.5
        )
        economics = self._economic_score(state)

        # Evidence-aware blending: early segments rely more on the explicit
        # ICP signals; mature segments increasingly reflect actual outcomes.
        maturity = 1.0 - exp(-state.observations / 25.0)
        outcome_score = 0.55 * win_rate + 0.25 * retention + 0.20 * economics
        return round(100.0 * ((1.0 - maturity) * signal_score + maturity * outcome_score), 2)

    def rank(self) -> list[tuple[str, float]]:
        return sorted(
            ((segment, self.score(segment)) for segment in self.segments),
            key=lambda item: item[1],
            reverse=True,
        )

    @staticmethod
    def _economic_score(state: SegmentState) -> float:
        if state.revenue <= 0:
            return 0.5
        if state.acquisition_cost <= 0:
            return 1.0
        ratio = state.revenue / state.acquisition_cost
        # Smoothly maps revenue/CAC to approximately [0, 1].
        return 1.0 - exp(-ratio / 5.0)

    def best_segments(self, limit: int = 5) -> Iterable[tuple[str, float]]:
        return self.rank()[:limit]
