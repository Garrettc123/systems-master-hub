"""
Hybrid crossover for LeadGenome.
Module-level uniform + rule-level + numeric blending + preferential multi_model.
"""
from __future__ import annotations
import copy
import random
from typing import Any, Dict, List, Optional


def hybrid_crossover(
    parent_a: Dict[str, Any],
    parent_b: Dict[str, Any],
    *,
    fitness_a: float = 0.0,
    fitness_b: float = 0.0,
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    rng = rng or random.Random()
    modules_a = parent_a.get("modules", parent_a)
    modules_b = parent_b.get("modules", parent_b)
    child: Dict[str, Any] = {}

    # 1. Module-level uniform for structural modules
    for mod in ("intake", "enrichment", "behavioral", "cost_control"):
        child[mod] = copy.deepcopy(
            modules_a.get(mod, {}) if rng.random() < 0.5 else modules_b.get(mod, {})
        )

    # 2. Scoring: rule-level + numeric blend
    child["scoring"] = _crossover_scoring(
        modules_a.get("scoring", {}), modules_b.get("scoring", {}), rng
    )

    # 3. Routing: blend thresholds
    child["routing"] = _crossover_routing(
        modules_a.get("routing", {}), modules_b.get("routing", {}), rng
    )

    # 4. Multi-model: preferential toward higher fitness
    mm_a = modules_a.get("multi_model", {})
    mm_b = modules_b.get("multi_model", {})
    if fitness_a >= fitness_b:
        child["multi_model"] = copy.deepcopy(mm_a or mm_b)
    else:
        child["multi_model"] = copy.deepcopy(mm_b or mm_a)
    if rng.random() < 0.15 and mm_a and mm_b:
        child["multi_model"] = copy.deepcopy(mm_b if fitness_a >= fitness_b else mm_a)

    return repair({"modules": child})


def _crossover_scoring(a: Dict, b: Dict, rng: random.Random) -> Dict:
    out = copy.deepcopy(a) if a else copy.deepcopy(b) or {}
    if not a or not b:
        return out

    # blend base_score
    ba, bb = a.get("base_score", 20), b.get("base_score", 20)
    out["base_score"] = int(0.5 * ba + 0.5 * bb)

    # rule-level uniform
    rules_a = a.get("rules", [])
    rules_b = b.get("rules", [])
    max_len = max(len(rules_a), len(rules_b))
    new_rules = []
    for i in range(max_len):
        if i < len(rules_a) and i < len(rules_b):
            new_rules.append(copy.deepcopy(rules_a[i] if rng.random() < 0.5 else rules_b[i]))
        elif i < len(rules_a):
            if rng.random() < 0.7:
                new_rules.append(copy.deepcopy(rules_a[i]))
        elif i < len(rules_b):
            if rng.random() < 0.7:
                new_rules.append(copy.deepcopy(rules_b[i]))
    out["rules"] = new_rules
    out["normalization"] = a.get("normalization") or b.get("normalization") or "clip_0_100"
    return out


def _crossover_routing(a: Dict, b: Dict, rng: random.Random) -> Dict:
    out = copy.deepcopy(a) if a else copy.deepcopy(b) or {}
    if not a or not b:
        return out
    for key in ("hubspot_threshold", "discard_below", "high_value_threshold"):
        if key in a and key in b:
            alpha = rng.uniform(0.3, 0.7)
            out[key] = int(alpha * a[key] + (1 - alpha) * b[key])
    # discrete fields
    out["hubspot_lifecycle_stage"] = (
        a.get("hubspot_lifecycle_stage") if rng.random() < 0.5
        else b.get("hubspot_lifecycle_stage")
    ) or "marketingqualifiedlead"
    return out


def repair(genome: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure semantic validity after crossover."""
    mods = genome.get("modules", genome)
    routing = mods.get("routing", {})
    ht = routing.get("hubspot_threshold", 60)
    db = routing.get("discard_below", 25)
    if ht <= db:
        routing["hubspot_threshold"] = db + 10
    scoring = mods.get("scoring", {})
    if scoring.get("normalization") == "clip_0_100":
        scoring["base_score"] = max(0, min(100, scoring.get("base_score", 20)))
    return genome
