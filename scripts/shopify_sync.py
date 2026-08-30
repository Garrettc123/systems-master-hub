"""Shopify Revenue Sync — GARCAR Enterprise"""
import os, requests
from datetime import date

STORE = os.environ.get('SHOPIFY_STORE', 'garcar-enterprise.myshopify.com')
TOKEN = os.environ.get('SHOPIFY_API_KEY', '')
BASE_URL = f'https://{STORE}/admin/api/2024-10'

HEADERS = {'X-Shopify-Access-Token': TOKEN, 'Content-Type': 'application/json'}

AI_PRODUCT_CATALOG = [
    {'title': 'Smart Contract Audit (Basic)', 'price': '499.00', 'sku': 'GC-AUDIT-001',
     'description': '<p>AI-powered smart contract vulnerability detection. Audit report in 24 hours.</p>'},
    {'title': 'Lead Enrichment API (1,000 Leads)', 'price': '299.00', 'sku': 'GC-LEAD-001',
     'description': '<p>Enrich 1,000 leads with 50+ data points including company, role, intent signals.</p>'},
    {'title': 'NEXUS AI Core — Monthly Access', 'price': '997.00', 'sku': 'GC-NEXUS-001',
     'description': '<p>Full access to GARCAR NEXUS AI: deal scoring, revenue automation, onchain analytics.</p>'},
    {'title': 'Butler Automation Setup', 'price': '2499.00', 'sku': 'GC-BUTLER-001',
     'description': '<p>Complete multi-agent business automation deployment. 6-agent stack, fully configured.</p>'},
    {'title': 'AI Revenue Architect Consultation', 'price': '1499.00', 'sku': 'GC-ARCH-001',
     'description': '<p>1:1 strategy session to architect your autonomous revenue system.</p>'},
]

def get_revenue_today():
    today = date.today().isoformat() + 'T00:00:00'
    r = requests.get(f'{BASE_URL}/orders.json?status=paid&created_at_min={today}',
                     headers=HEADERS)
    if r.status_code != 200:
        return 0.0, 0
    orders = r.json().get('orders', [])
    return sum(float(o['total_price']) for o in orders), len(orders)

def create_product(product_def: dict):
    payload = {
        'product': {
            'title': product_def['title'],
            'body_html': product_def['description'],
            'vendor': 'GARCAR Enterprise',
            'product_type': 'AI Service',
            'status': 'active',
            'variants': [{'price': product_def['price'], 'sku': product_def['sku'],
                          'inventory_management': None, 'fulfillment_service': 'manual'}]
        }
    }
    r = requests.post(f'{BASE_URL}/products.json', json=payload, headers=HEADERS)
    return r.json()

def deploy_catalog():
    print('Deploying GARCAR AI Product Catalog to Shopify...')
    for product in AI_PRODUCT_CATALOG:
        result = create_product(product)
        if 'product' in result:
            print(f"✅ Created: {result['product']['title']} — ID {result['product']['id']}")
        else:
            print(f"⚠️  {product['title']}: {result.get('errors', result)}")

if __name__ == '__main__':
    revenue, count = get_revenue_today()
    print(f"Today's Shopify Revenue: ${revenue:.2f} ({count} orders)")
    if TOKEN:
        deploy_catalog()
    else:
        print('Set SHOPIFY_API_KEY to deploy catalog')
