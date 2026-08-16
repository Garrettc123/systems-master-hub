"""Lead Agent Genome — evolvable configuration unit"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import uuid
from datetime import datetime, timezone

class LeadGenome(BaseModel):
    genome_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    generation: int = 0
    parent_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    modules: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def default(cls) -> "LeadGenome":
        return cls(
            modules={
                "intake": {
                    "batch_size": 50,
                    "max_age_hours": 72,
                    "source_priority": {"referral": 1.0, "organic": 0.85, "apollo": 0.70, "paid": 0.55, "other": 0.30},
                    "deduplication_strategy": "email_hash",
                },
                "enrichment": {
                    "providers": [
                        {"name": "apollo", "enabled": True, "timeout_ms": 2500, "fields": ["company_size", "tech_stack", "funding", "seniority"], "cost_weight": 1.0},
                        {"name": "clearbit", "enabled": True, "timeout_ms": 1800, "fields": ["company_size", "industry", "location"], "cost_weight": 0.7},
                        {"name": "internal_cache", "enabled": True, "timeout_ms": 50, "fields": ["*"], "cost_weight": 0.05},
                    ],
                    "fallback_policy": "partial_ok",
                    "max_enrichment_cost_usd": 0.12,
                },
                "scoring": {
                    "version": "rules_v3",
                    "base_score": 20,
                    "rules": [
                        {"id": "email_tld", "condition": "email_endswith", "params": [".com", ".io", ".ai", ".co"], "points": 12, "weight": 1.0},
                        {"id": "source_boost", "condition": "source_in", "params": ["referral", "organic"], "points": 25, "weight": 1.2},
                        {"id": "company_size_sweet", "condition": "company_size_in", "params": ["50-200", "200-500", "11-50"], "points": 30, "weight": 1.5},
                        {"id": "seniority", "condition": "title_contains", "params": ["ceo", "founder", "cto", "vp", "director", "head of"], "points": 18, "weight": 1.1},
                        {"id": "tech_stack_signal", "condition": "tech_stack_intersects", "params": ["stripe", "hubspot", "salesforce", "segment"], "points": 15, "weight": 1.0},
                    ],
                    "llm_component": {"enabled": False, "prompt_template": "You are a B2B lead scorer. Lead: {{lead}}. Return JSON {score: 0-100, reasons: []}", "temperature": 0.2, "max_tokens": 150, "weight_in_final": 0.35},
                    "final_aggregation": "weighted_sum",
                    "normalization": "clip_0_100",
                },
                "routing": {
                    "hubspot_threshold": 60,
                    "hubspot_lifecycle_stage": "marketingqualifiedlead",
                    "high_value_threshold": 85,
                    "discard_below": 25,
                    "reprocess_after_hours": 168,
                },
                "cost_control": {
                    "max_cost_per_lead_usd": 0.25,
                    "daily_budget_usd": 180,
                    "throttle_when_error_rate_above": 0.08,
                    "prefer_cheap_providers_when_score_below": 45,
                },
                "behavioral": {
                    "parallelism": 8,
                    "retry_policy": {"max_retries": 2, "backoff_base_ms": 400, "retry_on": ["timeout", "429", "5xx"]},
                    "observability_level": "full",
                },
            }
        )
