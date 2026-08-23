"""
Garcar Orchestrator — Cloudflare Worker entrypoint
Keyless Autonomous Wealth Loop
"""
from agents.lead_agent import run_lead_agent

# Keyless + webhook nervous system
try:
    from keyless import configure_resolver, health
    from keyless.webhook_bridge import keyless_require_valid_stripe
    from webhooks.router import normalize_stripe
    from webhooks.subscribers import build_default_router

    configure_resolver()
    router = build_default_router()
    KEYLESS_READY = True
except Exception as _boot_err:
    KEYLESS_READY = False
    _boot_msg = str(_boot_err)


async def on_fetch(request):
    path = str(getattr(request, "url", "") or "")

    # Keyless health (never returns secret values)
    if "/health/keyless" in path:
        import json
        if KEYLESS_READY:
            body = json.dumps(health())
        else:
            body = json.dumps({"keyless": False, "error": _boot_msg})
        return Response(body, status=200, headers={"Content-Type": "application/json"})

    # Stripe money path
    if "/webhooks/stripe" in path and KEYLESS_READY:
        try:
            body_bytes = await request.body()
            sig = request.headers.get("Stripe-Signature") or ""
            keyless_require_valid_stripe(body_bytes, sig)
            import json
            raw = json.loads(body_bytes.decode("utf-8"))
            event = normalize_stripe(raw)
            outcome = await router.process(event)
            return Response(
                outcome.model_dump_json(),
                status=200,
                headers={"Content-Type": "application/json"},
            )
        except PermissionError as e:
            return Response(str(e), status=401)
        except Exception as e:
            return Response(f"Webhook error: {e}", status=500)

    if "/webhooks/stripe" in path and not KEYLESS_READY:
        return Response(f"Keyless boot failed: {_boot_msg}", status=503)

    # Lead agent
    if "/lead-agent/run" in path or path.endswith("/run"):
        result = await run_lead_agent({"trigger": "manual"})
        return Response(str(result), headers={"Content-Type": "application/json"})

    status = "KEYLESS ONLINE" if KEYLESS_READY else "DEGRADED"
    return Response(f"Garcar Orchestrator — Autonomous Wealth Loop {status}", status=200)


async def on_scheduled(event):
    cron = getattr(event, "cron", "") or ""
    if "*/15" in cron or cron == "*/15 * * * *":
        await run_lead_agent({"trigger": "cron", "cron": cron})
