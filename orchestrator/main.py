"""
Garcar Orchestrator — Cloudflare Worker entrypoint
Full Autonomous Wealth Loop
"""
from agents.lead_agent import run_lead_agent

async def on_fetch(request):
    path = getattr(request, "url", None)
    path_str = str(path) if path else ""
    if "/lead-agent/run" in path_str or path_str.endswith("/run"):
        result = await run_lead_agent({"trigger": "manual"})
        return Response(str(result), headers={"Content-Type": "application/json"})
    return Response("Garcar Orchestrator — Autonomous Wealth Loop ONLINE", status=200)

async def on_scheduled(event):
    cron = getattr(event, "cron", "") or ""
    if "*/15" in cron or cron == "*/15 * * * *":
        await run_lead_agent({"trigger": "cron", "cron": cron})
    # Additional agents can be wired here as they are promoted
