# Full Autonomous Wealth Loop — Integration Runbook
_Owner: Garrett Carrol — Garcar Enterprise_
_Priority: CRITICAL — Revenue Blocking_
_Created: 2026-08-17_

---

## The Loop in Plain Language

```
Apollo finds lead
  → Agent sends Stripe checkout link
    → Lead pays
      → Stripe webhook fires
        → Zeus MRR updates
          → Linear task auto-closes
            → Loop repeats
```

Zero human steps. Zero manual touchpoints.

---

## STEP 1 — garcar-payments: Register Stripe Webhooks

1. Go to https://dashboard.stripe.com/webhooks
2. Click **Add endpoint**
3. Enter your endpoint URL:
   ```
   https://[YOUR-RAILWAY-URL]/webhooks/stripe
   ```
4. Add these 5 events:
   ```
   payment_intent.succeeded
   invoice.paid
   customer.subscription.created
   customer.subscription.deleted
   checkout.session.completed
   ```
5. Copy the **Webhook Signing Secret** → add to Railway env vars as `STRIPE_WEBHOOK_SECRET`

**Test from Termux:**
```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
stripe trigger payment_intent.succeeded
# Expect: 200 OK in terminal
```

---

## STEP 2 — garcar-autonomous-wealth-system: Apollo → Stripe Checkout

Add this function to your agent (`agents/wealth_loop.py`):

```python
import os
import stripe

stripe.api_key = os.environ['STRIPE_SECRET_KEY']

def create_checkout_link(lead_email: str, product_name: str, price_cents: int) -> str:
    price = stripe.Price.create(
        unit_amount=price_cents,
        currency="usd",
        product_data={"name": product_name},
    )
    link = stripe.PaymentLink.create(
        line_items=[{"price": price.id, "quantity": 1}],
        metadata={"lead_email": lead_email, "source": "apollo_auto"}
    )
    return link.url

def process_apollo_leads():
    """Pull leads from Apollo, send Stripe checkout link to each."""
    import requests
    headers = {"X-Api-Key": os.environ['APOLLO_API_KEY']}
    resp = requests.post(
        "https://api.apollo.io/v1/mixed_people/search",
        headers=headers,
        json={"page": 1, "per_page": 25, "contact_email_status": ["verified"]}
    )
    leads = resp.json().get("people", [])
    for lead in leads:
        email = lead.get("email")
        if email:
            link = create_checkout_link(email, "Garcar AI Services", 99900)  # $999
            print(f"Checkout link sent to {email}: {link}")
            # TODO: Send via email/SMS agent

if __name__ == "__main__":
    process_apollo_leads()
```

---

## STEP 3 — GitHub Actions: Automated Cron Schedule

Create `.github/workflows/wealth-agent.yml` in garcar-autonomous-wealth-system:

```yaml
name: Wealth Agent Loop
on:
  schedule:
    - cron: '0 */6 * * *'  # Runs every 6 hours
  workflow_dispatch:       # Can also trigger manually

jobs:
  run-agent:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Run Wealth Loop Agent
        run: python agents/wealth_loop.py
        env:
          STRIPE_SECRET_KEY: ${{ secrets.STRIPE_SECRET_KEY }}
          APOLLO_API_KEY: ${{ secrets.APOLLO_API_KEY }}
          LINEAR_API_KEY: ${{ secrets.LINEAR_API_KEY }}
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
```

**Required GitHub Secrets to add in each repo:**
```
RAILWAY_TOKEN
STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET
APOLLO_API_KEY
LINEAR_API_KEY
SUPABASE_URL
SUPABASE_KEY
```

---

## STEP 4 — zeus-dashboard: Live MRR Feed

Add this to your Zeus API (`api/revenue.py`):

```python
import os
import stripe

stripe.api_key = os.environ['STRIPE_SECRET_KEY']

def get_live_mrr() -> dict:
    """Pull real MRR from active Stripe subscriptions."""
    total_mrr = 0
    for sub in stripe.Subscription.list(status='active').auto_paging_iter():
        for item in sub['items']['data']:
            price = item['price']
            amount = price['unit_amount'] / 100
            interval = price.get('recurring', {}).get('interval', 'month')
            if interval == 'year':
                amount = amount / 12
            total_mrr += amount
    return {
        "mrr": round(total_mrr, 2),
        "arr": round(total_mrr * 12, 2)
    }
```

---

## STEP 5 — Self-Healing Deploy (autonomous-income-deployment)

Add to your deploy workflow:

```yaml
- name: Deploy garcar-payments to Railway
  run: railway up --service garcar-payments
  env:
    RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}

- name: Health Check with Auto-Rollback
  run: |
    sleep 30
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" ${{ secrets.RAILWAY_URL }}/health)
    if [ "$STATUS" != "200" ]; then
      echo "FAILED: Health check returned $STATUS — rolling back"
      railway rollback
      exit 1
    fi
    echo "HEALTHY: Service live at $STATUS"
```

---

## Final Verification Checklist

Run from Termux once deployed:

```bash
# 1. Stripe webhook live check
curl -X POST https://[RAILWAY-URL]/webhooks/stripe \
  -H 'Content-Type: application/json' -d '{}'
# Expect: 400 (means endpoint exists + signature check active)

# 2. Generate a test payment link
python3 -c "
import stripe, os
stripe.api_key = os.environ['STRIPE_SECRET_KEY']
p = stripe.Price.create(unit_amount=100, currency='usd', product_data={'name':'test'})
l = stripe.PaymentLink.create(line_items=[{'price': p.id, 'quantity': 1}])
print(l.url)
"
# Expect: https://buy.stripe.com/...

# 3. Check live MRR
curl https://[ZEUS-URL]/api/revenue/mrr
# Expect: {"mrr": X.XX, "arr": X.XX}

# 4. Confirm all pipelines green
# → Go to GitHub Actions on each repo → last run = ✅
```

---

## Definition of Done — Issue #28
- [ ] Stripe webhooks registered + receiving live events
- [ ] Apollo lead → Stripe checkout link flowing automatically every 6 hours
- [ ] All GitHub Actions pipelines green
- [ ] Zeus dashboard shows MRR > $0
- [ ] Zero manual steps required for daily operations

_When all boxes checked → close issue #28_
