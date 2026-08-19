"""
Lead Agent — Genome-driven, Cloudflare + Supabase native
Runs on Cloudflare Workers (Python) via cron every 15 min
"""
from __future__ import annotations
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from genomes.lead_genome import LeadGenome

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
HUBSPOT_KEY = os.getenv("HUBSPOT_API_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY or "",
    "Authorization": f"Bearer {SUPABASE_KEY or ''}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

async def load_active_genome(client: httpx.AsyncClient) -> LeadGenome:
    try:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/agent_genomes",
            params={"agent_name": "eq.lead_agent", "status": "eq.promoted", "select": "*", "order": "created_at.desc", "limit": "1"},
            headers=HEADERS,
        )
        rows = resp.json()
        if rows:
            return LeadGenome(**rows[0]["genome"])
    except Exception:
        pass
    return LeadGenome.default()

def apply_scoring_rules(lead: Dict[str, Any], genome: LeadGenome) -> int:
    scoring = genome.modules.get("scoring", {})
    score = scoring.get("base_score", 20)
    rules = scoring.get("rules", [])
    email = (lead.get("email") or "").lower()
    source = (lead.get("source") or "").lower()
    company_size = (lead.get("company_size") or "").lower()
    title = (lead.get("title") or lead.get("job_title") or "").lower()
    tech = [t.lower() for t in (lead.get("tech_stack") or [])]

    for rule in rules:
        cond = rule.get("condition")
        params = [p.lower() if isinstance(p, str) else p for p in rule.get("params", [])]
        points = rule.get("points", 0) * rule.get("weight", 1.0)
        if cond == "email_endswith" and any(email.endswith(p) for p in params):
            score += points
        elif cond == "source_in" and source in params:
            score += points
        elif cond == "company_size_in" and company_size in params:
            score += points
        elif cond == "title_contains" and any(p in title for p in params):
            score += points
        elif cond == "tech_stack_intersects" and any(p in tech for p in params):
            score += points

    if scoring.get("normalization") == "clip_0_100":
        score = max(0, min(100, int(score)))
    return score

async def fetch_unprocessed_leads(client: httpx.AsyncClient, batch_size: int) -> List[Dict]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        return []
    resp = await client.get(
        f"{SUPABASE_URL}/rest/v1/leads",
        params={"processed": "eq.false", "select": "*", "order": "created_at.asc", "limit": str(batch_size)},
        headers=HEADERS,
    )
    return resp.json() if resp.status_code == 200 else []

async def upsert_lead(client: httpx.AsyncClient, lead: Dict) -> None:
    if not SUPABASE_URL:
        return
    await client.post(
        f"{SUPABASE_URL}/rest/v1/leads",
        json=lead,
        headers={**HEADERS, "Prefer": "resolution=merge-duplicates,return=minimal"},
    )

async def mark_run(client: httpx.AsyncClient, run_id: str, status: str, result: Dict, duration_ms: int, genome_id: str):
    if not SUPABASE_URL:
        return
    await client.post(
        f"{SUPABASE_URL}/rest/v1/agent_runs",
        json={
            "agent_name": "lead_agent",
            "run_id": run_id,
            "trigger_type": "cron",
            "status": status,
            "output_result": result,
            "duration_ms": duration_ms,
            "genome_id": genome_id,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        },
        headers={**HEADERS, "Prefer": "return=minimal"},
    )

async def sync_to_hubspot(client: httpx.AsyncClient, lead: Dict, genome: LeadGenome) -> Optional[str]:
    if not HUBSPOT_KEY:
        return None
    routing = genome.modules.get("routing", {})
    props = {
        "email": lead["email"],
        "firstname": lead.get("first_name", ""),
        "lastname": lead.get("last_name", ""),
        "company": lead.get("company", ""),
        "lead_score": str(lead.get("lead_score", 0)),
        "lifecyclestage": routing.get("hubspot_lifecycle_stage", "marketingqualifiedlead"),
    }
    resp = await client.post(
        "https://api.hubapi.com/crm/v3/objects/contacts",
        json={"properties": props},
        headers={"Authorization": f"Bearer {HUBSPOT_KEY}", "Content-Type": "application/json"},
    )
    if resp.status_code in (200, 201):
        return resp.json().get("id")
    return None

async def run_lead_agent(payload: Optional[Dict] = None) -> Dict[str, Any]:
    run_id = str(uuid.uuid4())
    start = time.perf_counter()
    results = {"run_id": run_id, "processed": 0, "enriched": 0, "scored": 0, "synced": 0, "discarded": 0, "errors": [], "genome_id": None}

    async with httpx.AsyncClient(timeout=30.0) as client:
        genome = await load_active_genome(client)
        results["genome_id"] = genome.genome_id
        intake = genome.modules.get("intake", {})
        routing = genome.modules.get("routing", {})
        batch_size = intake.get("batch_size", 50)

        leads = await fetch_unprocessed_leads(client, batch_size)
        results["processed"] = len(leads)

        for lead in leads:
            try:
                enriched = {**lead, "enriched": True, "company_size": lead.get("company_size", "unknown")}
                results["enriched"] += 1
                score = apply_scoring_rules(enriched, genome)
                enriched["lead_score"] = score
                enriched["scored_at"] = datetime.now(timezone.utc).isoformat()
                enriched["genome_id"] = genome.genome_id
                results["scored"] += 1

                if score < routing.get("discard_below", 25):
                    enriched["processed"] = True
                    enriched["status"] = "discarded"
                    results["discarded"] += 1
                else:
                    enriched["processed"] = True
                    if score >= routing.get("hubspot_threshold", 60):
                        hs_id = await sync_to_hubspot(client, enriched, genome)
                        if hs_id:
                            enriched["hubspot_contact_id"] = hs_id
                            results["synced"] += 1
                await upsert_lead(client, enriched)
            except Exception as e:
                results["errors"].append({"lead_id": lead.get("id"), "error": str(e)})

        duration_ms = int((time.perf_counter() - start) * 1000)
        status = "success" if not results["errors"] else "partial"
        await mark_run(client, run_id, status, results, duration_ms, genome.genome_id)

    return results
