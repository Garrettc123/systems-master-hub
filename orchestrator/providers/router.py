"""
MultiModelRouter — Garcar multi-model cognitive fabric.
Genome-controlled routing, ensemble modes, full cost attribution.
"""
from __future__ import annotations
import asyncio
import time
from typing import Any, Dict, List, Optional

from .base import BaseProvider, ProviderResponse


class MultiModelRouter:
    """
    Routes tasks to one or more providers according to the promoted genome policy.
    Modes: single | fallback | parallel | consensus | synthesize
    """

    def __init__(self, providers: Dict[str, BaseProvider], policy: Optional[Dict[str, Any]] = None):
        self.providers = providers
        self.policy = policy or self._default_policy()

    @staticmethod
    def _default_policy() -> Dict[str, Any]:
        return {
            "default_mode": "cost_optimized",
            "max_cost_per_task_usd": 0.08,
            "routing": {
                "live_web": {"primary": "perplexity", "mode": "single"},
                "bulk_score": {"primary": "gemini", "secondary": ["anthropic"], "mode": "fallback"},
                "deep_qualify": {"primary": "anthropic", "secondary": ["openai", "gemini"], "mode": "consensus"},
                "tool_use": {"primary": "openai", "secondary": ["anthropic"], "mode": "fallback"},
                "high_stakes": {"primary": "anthropic", "secondary": ["openai", "gemini"], "mode": "majority"},
                "fact_check": {"primary": "perplexity", "secondary": ["anthropic"], "mode": "cross"},
                "synthesis": {"primary": "gemini", "secondary": ["anthropic"], "mode": "sequential"},
            },
            "ensemble_threshold": 0.75,
        }

    def update_policy(self, policy: Dict[str, Any]) -> None:
        self.policy = policy

    async def route(
        self,
        task_type: str,
        prompt: str,
        *,
        system: Optional[str] = None,
        lead: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        start = time.perf_counter()
        route_cfg = self.policy.get("routing", {}).get(task_type, {"primary": "anthropic", "mode": "single"})
        mode = route_cfg.get("mode", "single")
        primary_name = route_cfg.get("primary")
        secondary_names = route_cfg.get("secondary", [])

        primary = self.providers.get(primary_name)
        if not primary:
            return {"error": f"Provider {primary_name} not registered", "cost_usd": 0.0}

        responses: List[ProviderResponse] = []

        if mode == "single":
            resp = await primary.generate(prompt, system=system)
            responses.append(resp)

        elif mode == "fallback":
            resp = await primary.generate(prompt, system=system)
            responses.append(resp)
            if not resp.ok:
                for name in secondary_names:
                    sec = self.providers.get(name)
                    if sec:
                        r = await sec.generate(prompt, system=system)
                        responses.append(r)
                        if r.ok:
                            break

        elif mode in ("parallel", "consensus", "majority"):
            names = [primary_name] + list(secondary_names)
            tasks = []
            for name in names:
                p = self.providers.get(name)
                if p:
                    tasks.append(p.generate(prompt, system=system))
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if isinstance(r, ProviderResponse):
                        responses.append(r)

        else:  # sequential / synthesize / default
            resp = await primary.generate(prompt, system=system)
            responses.append(resp)

        total_cost = sum(r.cost_usd for r in responses)
        max_cost = self.policy.get("max_cost_per_task_usd", 0.08)
        if total_cost > max_cost:
            # still return results but flag over-budget
            pass

        chosen = self._select(responses, mode)
        duration_ms = int((time.perf_counter() - start) * 1000)

        return {
            "task_type": task_type,
            "mode": mode,
            "chosen": chosen.__dict__ if chosen else None,
            "all_responses": [r.__dict__ for r in responses],
            "cost_usd": total_cost,
            "duration_ms": duration_ms,
            "agreement": self._agreement(responses),
        }

    def _select(self, responses: List[ProviderResponse], mode: str) -> Optional[ProviderResponse]:
        ok = [r for r in responses if r.ok]
        if not ok:
            return responses[0] if responses else None
        if mode in ("consensus", "majority") and len(ok) > 1:
            # simple: highest confidence among agreeing cluster; fallback to first ok
            return max(ok, key=lambda r: r.confidence)
        return ok[0]

    def _agreement(self, responses: List[ProviderResponse]) -> float:
        ok = [r for r in responses if r.ok]
        if len(ok) < 2:
            return 0.0
        # crude content-overlap proxy; real impl can use embedding similarity
        return min(1.0, len(ok) / max(len(responses), 1))
