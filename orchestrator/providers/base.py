"""
Base provider interface for Garcar multi-model substrate.
Every call must return cost and be recordable into agent_runs.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProviderResponse:
    provider: str
    model: str
    content: str
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    confidence: float = 0.0
    citations: List[str] = field(default_factory=list)
    raw: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.content)


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> ProviderResponse:
        ...

    async def score_lead(self, lead: Dict[str, Any], rules: Dict[str, Any]) -> ProviderResponse:
        """Structured lead scoring. Override for provider-specific prompts."""
        system = (
            "You are a B2B lead scorer. Return JSON only: "
            '{"score": 0-100, "reasons": ["..."]}'
        )
        prompt = f"Lead: {lead}\nScoring rules context: {rules}"
        return await self.generate(prompt, system=system, json_mode=True, temperature=0.1)
