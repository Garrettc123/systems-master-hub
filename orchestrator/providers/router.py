"""
MultiModelRouter — Garcar multi-model cognitive fabric.

Genome-controlled routing across Perplexity, Gemini, OpenAI, Anthropic.
Modes: single | fallback | parallel | consensus | majority | sequential
Every call returns full cost attribution for agent_runs.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

from .base import BaseProvider, ProviderResponse

logger = logging.getLogger("garcar.router")


class MultiModelRouter:
    """
    Central decision point for all LLM work in Garcar.

    Policy lives in the promoted genome under modules.multi_model.
    Production behavior changes only when a new genome is promoted.
    """

    def __init__(
        self,
        providers: Dict[str, BaseProvider],
        policy: Optional[Dict[str, Any]] = None,
    ):
        self.providers = {k.lower(): v for k, v in (providers or {}).items()}
        self.policy = policy or self.default_policy()
        self._total_cost_session = 0.0

    # ─── Policy ───────────────────────────────────────────────────────────

    @staticmethod
    def default_policy() -> Dict[str, Any]:
        return {
            "enabled": True,
            "default_mode": "cost_optimized",
            "max_cost_per_task_usd": 0.08,
            "daily_budget_usd": 220.0,
            "ensemble_threshold": 0.75,
            "routing": {
                "live_web": {
                    "primary": "perplexity",
                    "mode": "single",
                },
                "bulk_score": {
                    "primary": "gemini",
                    "secondary": ["anthropic"],
                    "mode": "fallback",
                },
                "deep_qualify": {
                    "primary": "anthropic",
                    "secondary": ["openai", "gemini"],
                    "mode": "consensus",
                },
                "tool_use": {
                    "primary": "openai",
                    "secondary": ["anthropic"],
                    "mode": "fallback",
                },
                "high_stakes": {
                    "primary": "anthropic",
                    "secondary": ["openai", "gemini"],
                    "mode": "majority",
                },
                "fact_check": {
                    "primary": "perplexity",
                    "secondary": ["anthropic"],
                    "mode": "cross",
                },
                "synthesis": {
                    "primary": "gemini",
                    "secondary": ["anthropic"],
                    "mode": "sequential",
                },
            },
        }

    def update_policy(self, policy: Dict[str, Any]) -> None:
        """Replace routing policy (call when a new genome is promoted)."""
        if policy:
            self.policy = {**self.default_policy(), **policy}

    def load_from_genome(self, genome_modules: Dict[str, Any]) -> None:
        """Extract multi_model module from a LeadGenome.modules dict."""
        mm = genome_modules.get("multi_model") if genome_modules else None
        if mm:
            self.update_policy(mm)

    # ─── Core route ───────────────────────────────────────────────────────

    async def route(
        self,
        task_type: str,
        prompt: str,
        *,
        system: Optional[str] = None,
        model_overrides: Optional[Dict[str, str]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Route a task to one or more providers according to genome policy.

        Returns:
            {
              task_type, mode, chosen, all_responses,
              cost_usd, duration_ms, agreement, over_budget
            }
        """
        start = time.perf_counter()
        routing = self.policy.get("routing", {})
        route_cfg = routing.get(
            task_type,
            {"primary": "anthropic", "mode": "single"},
        )
        mode = route_cfg.get("mode", "single")
        primary_name = (route_cfg.get("primary") or "anthropic").lower()
        secondary_names = [s.lower() for s in route_cfg.get("secondary", [])]

        primary = self.providers.get(primary_name)
        if not primary:
            primary = next(iter(self.providers.values()), None)
            primary_name = next(iter(self.providers.keys()), "none")
            if not primary:
                return self._empty_result(task_type, mode, "No providers registered")

        kwargs: Dict[str, Any] = dict(
            system=system,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=json_mode,
        )
        if model_overrides and primary_name in model_overrides:
            kwargs["model"] = model_overrides[primary_name]

        responses: List[ProviderResponse] = []

        try:
            if mode == "single":
                responses.append(await primary.generate(prompt, **kwargs))

            elif mode == "fallback":
                r = await primary.generate(prompt, **kwargs)
                responses.append(r)
                if not r.ok:
                    for name in secondary_names:
                        sec = self.providers.get(name)
                        if not sec:
                            continue
                        sk = dict(kwargs)
                        if model_overrides and name in model_overrides:
                            sk["model"] = model_overrides[name]
                        r2 = await sec.generate(prompt, **sk)
                        responses.append(r2)
                        if r2.ok:
                            break

            elif mode in ("parallel", "consensus", "majority", "cross"):
                names = [primary_name] + [
                    n for n in secondary_names if n in self.providers
                ]
                tasks = []
                for name in names:
                    p = self.providers[name]
                    sk = dict(kwargs)
                    if model_overrides and name in model_overrides:
                        sk["model"] = model_overrides[name]
                    tasks.append(p.generate(prompt, **sk))
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if isinstance(r, ProviderResponse):
                        responses.append(r)
                    elif isinstance(r, Exception):
                        logger.warning("Provider task failed: %s", r)

            elif mode == "sequential":
                r = await primary.generate(prompt, **kwargs)
                responses.append(r)
                if r.ok and secondary_names:
                    follow = (
                        f"Previous analysis:\n{r.content}\n\n"
                        f"Refine or synthesize:\n{prompt}"
                    )
                    for name in secondary_names:
                        sec = self.providers.get(name)
                        if not sec:
                            continue
                        sk = dict(kwargs)
                        if model_overrides and name in model_overrides:
                            sk["model"] = model_overrides[name]
                        r2 = await sec.generate(follow, **sk)
                        responses.append(r2)
                        break

            else:
                responses.append(await primary.generate(prompt, **kwargs))

        except Exception as e:
            logger.exception("Router execution error")
            return self._empty_result(task_type, mode, str(e))

        total_cost = sum(r.cost_usd for r in responses)
        self._total_cost_session += total_cost
        max_cost = float(self.policy.get("max_cost_per_task_usd", 0.08))
        over_budget = total_cost > max_cost

        chosen = self._select(responses, mode)
        agreement = self._agreement(responses)
        duration_ms = int((time.perf_counter() - start) * 1000)

        return {
            "task_type": task_type,
            "mode": mode,
            "chosen": _response_to_dict(chosen) if chosen else None,
            "all_responses": [_response_to_dict(r) for r in responses],
            "cost_usd": round(total_cost, 6),
            "duration_ms": duration_ms,
            "agreement": round(agreement, 4),
            "over_budget": over_budget,
            "providers_used": list({r.provider for r in responses}),
        }

    # ─── Convenience: structured lead scoring ─────────────────────────────

    async def score_lead(
        self,
        lead: Dict[str, Any],
        genome_scoring: Optional[Dict[str, Any]] = None,
        task_type: str = "bulk_score",
    ) -> Dict[str, Any]:
        """
        Ask the routed model(s) for a structured score.
        Returns router result plus parsed score/reasons when possible.
        """
        system = (
            "You are a B2B lead qualification engine. "
            "Respond with JSON only: "
            '{"score": <0-100 integer>, "reasons": ["..."]}'
        )
        rules_ctx = genome_scoring or {}
        prompt = (
            f"Score this lead.\n"
            f"Lead: {json.dumps(lead, default=str)}\n"
            f"Scoring context: {json.dumps(rules_ctx, default=str)}"
        )
        result = await self.route(
            task_type,
            prompt,
            system=system,
            temperature=0.1,
            json_mode=True,
            max_tokens=512,
        )
        parsed: Dict[str, Any] = {"score": None, "reasons": []}
        chosen = result.get("chosen") or {}
        content = chosen.get("content") or ""
        try:
            text = content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
                if text.endswith("```"):
                    text = text[:-3]
            data = json.loads(text)
            parsed["score"] = int(data.get("score", 0))
            parsed["reasons"] = list(data.get("reasons") or [])
        except Exception:
            pass
        result["parsed"] = parsed
        return result

    # ─── Selection & agreement ────────────────────────────────────────────

    def _select(
        self, responses: List[ProviderResponse], mode: str
    ) -> Optional[ProviderResponse]:
        ok = [r for r in responses if r.ok]
        if not ok:
            return responses[0] if responses else None
        if mode in ("consensus", "majority", "cross") and len(ok) > 1:
            return max(ok, key=lambda r: (r.confidence, -r.cost_usd))
        if mode == "sequential":
            return ok[-1]
        return ok[0]

    def _agreement(self, responses: List[ProviderResponse]) -> float:
        ok = [r for r in responses if r.ok]
        if len(ok) < 2:
            return 0.0
        return min(1.0, len(ok) / max(len(responses), 1))

    def _empty_result(self, task_type: str, mode: str, error: str) -> Dict[str, Any]:
        return {
            "task_type": task_type,
            "mode": mode,
            "chosen": None,
            "all_responses": [],
            "cost_usd": 0.0,
            "duration_ms": 0,
            "agreement": 0.0,
            "over_budget": False,
            "error": error,
            "providers_used": [],
        }

    @property
    def session_cost(self) -> float:
        return self._total_cost_session


def _response_to_dict(r: Optional[ProviderResponse]) -> Optional[Dict[str, Any]]:
    if r is None:
        return None
    return {
        "provider": r.provider,
        "model": r.model,
        "content": r.content,
        "cost_usd": r.cost_usd,
        "input_tokens": r.input_tokens,
        "output_tokens": r.output_tokens,
        "latency_ms": r.latency_ms,
        "confidence": r.confidence,
        "citations": r.citations,
        "error": r.error,
    }


def build_router_from_env(policy: Optional[Dict[str, Any]] = None) -> MultiModelRouter:
    """
    Construct router with whatever providers have API keys present.
    Missing keys → provider simply not registered (graceful degrade).
    """
    import os

    providers: Dict[str, BaseProvider] = {}

    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            from .anthropic_client import AnthropicProvider
            providers["anthropic"] = AnthropicProvider()
        except Exception as e:
            logger.warning("Anthropic provider unavailable: %s", e)

    if os.getenv("OPENAI_API_KEY"):
        try:
            from .openai_client import OpenAIProvider
            providers["openai"] = OpenAIProvider()
        except Exception as e:
            logger.warning("OpenAI provider unavailable: %s", e)

    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        try:
            from .gemini_client import GeminiProvider
            providers["gemini"] = GeminiProvider()
        except Exception as e:
            logger.warning("Gemini provider unavailable: %s", e)

    if os.getenv("PERPLEXITY_API_KEY"):
        try:
            from .perplexity_client import PerplexityProvider
            providers["perplexity"] = PerplexityProvider()
        except Exception as e:
            logger.warning("Perplexity provider unavailable: %s", e)

    if not providers:
        logger.warning(
            "No LLM providers registered — router will return errors until keys are set"
        )

    return MultiModelRouter(providers, policy=policy)
