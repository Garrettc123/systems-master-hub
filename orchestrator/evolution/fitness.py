"""
Economic fitness from lead_outcomes.
Primary signal for selection and promotion.
"""
from __future__ import annotations
from typing import Any, Dict, List


def compute_fitness(
    outcomes: List[Dict[str, Any]],
    *,
    synchronicity_bonus: float = 0.0,
    min_samples: int = 10,
) -> Dict[str, Any]:
    """
    fitness ≈ (won_revenue - costs - lost_penalty) / (n + ε)
    Returns structured fitness for agent_genomes.fitness JSONB.
    """
    n = len(outcomes)
    if n == 0:
        return {
            "score": 0.0,
            "sample_size": 0,
            "ready_for_promotion": False,
            "breakdown": {},
        }

    won_revenue = 0.0
    total_cost = 0.0
    won = 0
    lost = 0
    engaged = 0

    for o in outcomes:
        otype = (o.get("outcome_type") or "").lower()
        rev = float(o.get("revenue_usd") or 0)
        cost = float(o.get("acquisition_cost_usd") or 0)
        total_cost += cost
        if otype == "closed_won":
            won += 1
            won_revenue += rev
        elif otype == "closed_lost":
            lost += 1
        elif otype in ("engaged", "expanded"):
            engaged += 1

    # Economic value
    raw = won_revenue + (engaged * 50.0) - (lost * 30.0) - (total_cost * 1.2)
    score = raw / (n + 1e-6)

    # Normalize roughly to 0–100 for readability
    norm = max(0.0, min(100.0, 50.0 + score / 20.0))
    norm = min(100.0, norm + synchronicity_bonus * 5.0)

    return {
        "score": round(norm, 2),
        "raw_ev": round(score, 4),
        "sample_size": n,
        "won": won,
        "lost": lost,
        "engaged": engaged,
        "won_revenue_usd": round(won_revenue, 2),
        "total_cost_usd": round(total_cost, 4),
        "synchronicity_bonus": synchronicity_bonus,
        "ready_for_promotion": n >= min_samples and norm > 0,
        "breakdown": {
            "won_revenue": won_revenue,
            "engaged_value": engaged * 50.0,
            "lost_penalty": lost * 30.0,
            "cost_penalty": total_cost * 1.2,
        },
    }


def promotion_eligible(
    candidate_fitness: Dict[str, Any],
    promoted_fitness: Dict[str, Any],
    *,
    min_lift: float = 2.0,
    min_samples: int = 15,
) -> bool:
    """Promote only on demonstrated economic lift + sufficient samples."""
    if candidate_fitness.get("sample_size", 0) < min_samples:
        return False
    c = candidate_fitness.get("score", 0)
    p = promoted_fitness.get("score", 0) if promoted_fitness else 0
    return (c - p) >= min_lift
