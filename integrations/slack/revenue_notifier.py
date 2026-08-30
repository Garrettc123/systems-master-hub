"""GARCAR Slack Revenue Notifier
Sends real-time revenue alerts to Slack channels.
Triggered by: Stripe webhooks, Shopify orders, Supabase realtime, Base L2 events.

Channels:
  #revenue-ops   — payment events, deal closures
  #deployments   — GitHub Actions, Railway deploys
  #alerts        — system health, security events
"""
import os
import json
import requests
from datetime import datetime
from typing import Optional

# Webhook URLs from GitHub Secrets / Railway env
WEBHOOKS = {
    "revenue_ops": os.getenv("SLACK_REVENUE_OPS_WEBHOOK"),
    "deployments": os.getenv("SLACK_DEPLOYMENTS_WEBHOOK"),
    "alerts": os.getenv("SLACK_ALERTS_WEBHOOK"),
    "general": os.getenv("SLACK_GENERAL_WEBHOOK")
}


def send_revenue_alert(
    amount: float,
    currency: str,
    source: str,
    customer: Optional[str] = None,
    product: Optional[str] = None,
    event_type: str = "payment.succeeded"
):
    """Send revenue alert to #revenue-ops."""
    webhook = WEBHOOKS.get("revenue_ops")
    if not webhook:
        print("[Slack] SLACK_REVENUE_OPS_WEBHOOK not configured")
        return

    emoji_map = {"stripe": "💳", "shopify": "🛒", "base_l2": "⛓️", "huggingface": "🤗", "linear": "📋"}
    emoji = emoji_map.get(source, "💰")
    
    payload = {
        "text": f"{emoji} *Revenue Event* — ${amount:,.2f} {currency.upper()}",
        "attachments": [{
            "color": "#437a22",
            "fields": [
                {"title": "Source", "value": source.upper(), "short": True},
                {"title": "Type", "value": event_type, "short": True},
                {"title": "Amount", "value": f"${amount:,.2f} {currency.upper()}", "short": True},
                {"title": "Time", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"), "short": True},
            ] + (
                [{"title": "Customer", "value": customer, "short": True}] if customer else []
            ) + (
                [{"title": "Product", "value": product, "short": True}] if product else []
            ),
            "footer": "GARCAR Revenue Multiplex | autonomous-butler-core"
        }]
    }
    resp = requests.post(webhook, json=payload)
    print(f"[Slack Revenue Alert] Status: {resp.status_code}")


def send_deployment_alert(repo: str, status: str, url: Optional[str] = None):
    """Send deployment notification to #deployments."""
    webhook = WEBHOOKS.get("deployments")
    if not webhook:
        return
    emoji = "✅" if status == "success" else "❌"
    payload = {
        "text": f"{emoji} *Deploy* — `{repo}` → {status.upper()}",
        "attachments": [{
            "color": "#437a22" if status == "success" else "#a12c7b",
            "text": url or "No URL",
            "footer": "GARCAR CI/CD | autonomous-butler-core"
        }]
    }
    requests.post(webhook, json=payload)


def send_system_alert(system: str, message: str, severity: str = "info"):
    """Send system health alert to #alerts."""
    webhook = WEBHOOKS.get("alerts")
    if not webhook:
        return
    colors = {"info": "#006494", "warning": "#d19900", "error": "#a12c7b", "critical": "#a13544"}
    emojis = {"info": "ℹ️", "warning": "⚠️", "error": "🔴", "critical": "🚨"}
    payload = {
        "text": f"{emojis.get(severity, 'ℹ️')} *System Alert* [{severity.upper()}] — {system}",
        "attachments": [{
            "color": colors.get(severity, "#006494"),
            "text": message,
            "footer": f"GARCAR Security Ops | {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        }]
    }
    requests.post(webhook, json=payload)


def send_daily_revenue_summary(total: float, breakdown: dict):
    """Send daily revenue summary to #revenue-ops."""
    webhook = WEBHOOKS.get("revenue_ops")
    if not webhook:
        return
    fields = [{"title": src.upper(), "value": f"${amt:,.2f}", "short": True}
              for src, amt in breakdown.items()]
    fields.append({"title": "🏆 TOTAL", "value": f"${total:,.2f}", "short": False})
    payload = {
        "text": f"📊 *GARCAR Daily Revenue Summary* — ${total:,.2f}",
        "attachments": [{
            "color": "#01696f",
            "fields": fields,
            "footer": f"GARCAR Revenue Multiplex | {datetime.utcnow().strftime('%Y-%m-%d')}"
        }]
    }
    requests.post(webhook, json=payload)


if __name__ == "__main__":
    # Test notification
    send_revenue_alert(
        amount=297.00,
        currency="USD",
        source="stripe",
        customer="test@garcar.io",
        product="GARCAR AI Consulting — Starter",
        event_type="payment.succeeded"
    )
    print("[Slack Notifier] Test complete")
