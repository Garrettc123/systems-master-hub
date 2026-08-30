"""GARCAR Shopify Bridge
Connects Shopify storefront to garcar-payment-loop Stripe handler.
Fed into NEXUS-AI-CORE deal pipeline and Supabase gc_ledger.

Deploy: Railway service → autonomous-butler-core triggers
"""
import os
import json
import hmac
import hashlib
import requests
from datetime import datetime

# Config from environment (set in GitHub Secrets / Railway)
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")
SHOPIFY_ACCESS_TOKEN = os.getenv("SHOPIFY_ACCESS_TOKEN")
SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET")
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SLACK_REVENUE_WEBHOOK = os.getenv("SLACK_REVENUE_OPS_WEBHOOK")
NEXUS_WEBHOOK_URL = os.getenv("NEXUS_WEBHOOK_URL")

SHOPIFY_API = f"https://{SHOPIFY_STORE}.myshopify.com/admin/api/2024-01"
HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
    "Content-Type": "application/json"
}


def verify_shopify_webhook(data: bytes, hmac_header: str) -> bool:
    """Verify Shopify webhook authenticity."""
    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode('utf-8'),
        data,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(digest, hmac_header)


def log_revenue_to_supabase(event: dict):
    """Push revenue event to Supabase gc_ledger."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("[WARN] Supabase not configured")
        return
    
    payload = {
        "source": "shopify",
        "event_type": event.get("type", "order.paid"),
        "amount": float(event.get("total_price", 0)),
        "currency": event.get("currency", "USD").upper(),
        "customer_email": event.get("email"),
        "customer_id": str(event.get("customer", {}).get("id", "")),
        "product_name": ", ".join([li["title"] for li in event.get("line_items", [])]),
        "metadata": {"shopify_order_id": event.get("id"), "order_number": event.get("order_number")}
    }
    
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/revenue_events",
        headers={"apikey": SUPABASE_SERVICE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}", "Content-Type": "application/json", "Prefer": "return=minimal"},
        json=payload
    )
    print(f"[Supabase] Revenue logged: {resp.status_code}")


def notify_slack(order: dict):
    """Send revenue alert to Slack #revenue-ops."""
    if not SLACK_REVENUE_WEBHOOK:
        return
    amount = order.get("total_price", "0")
    customer = order.get("email", "unknown")
    items = ", ".join([li["title"] for li in order.get("line_items", [])])
    requests.post(SLACK_REVENUE_WEBHOOK, json={
        "text": f"🛒 *Shopify Sale* — ${amount} from {customer}",
        "attachments": [{"color": "#437a22", "text": f"Products: {items}"}]
    })


def get_products():
    """List all active Shopify products."""
    resp = requests.get(f"{SHOPIFY_API}/products.json?status=active", headers=HEADERS)
    return resp.json().get("products", [])


def get_revenue_summary(days: int = 30) -> dict:
    """Get revenue summary for the last N days."""
    resp = requests.get(
        f"{SHOPIFY_API}/orders.json?status=any&financial_status=paid&limit=250",
        headers=HEADERS
    )
    orders = resp.json().get("orders", [])
    total = sum(float(o["total_price"]) for o in orders)
    return {"total_revenue_usd": total, "order_count": len(orders), "period_days": days}


if __name__ == "__main__":
    print("[GARCAR Shopify Bridge] Initialized")
    products = get_products()
    print(f"[Shopify] Active products: {len(products)}")
    summary = get_revenue_summary()
    print(f"[Shopify Revenue] Last 30d: ${summary['total_revenue_usd']:.2f} ({summary['order_count']} orders)")
