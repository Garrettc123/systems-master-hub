"""Notion CRM Sync — GARCAR Enterprise"""
import os, requests
from datetime import date

NOTION_API = 'https://api.notion.com/v1'
HEADERS = {
    'Authorization': f'Bearer {os.environ.get("NOTION_API_KEY", "")}',
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json'
}

def create_deal(company: str, contact_email: str, value: float, source: str, stage: str = 'Prospecting'):
    db_id = os.environ.get('NOTION_DB_ID', '')
    if not db_id:
        print('Set NOTION_DB_ID environment variable')
        return None
    payload = {
        'parent': {'database_id': db_id},
        'properties': {
            'Company': {'title': [{'text': {'content': company}}]},
            'Contact Email': {'email': contact_email},
            'Deal Value': {'number': value},
            'Source': {'select': {'name': source}},
            'Stage': {'select': {'name': stage}},
            'Date': {'date': {'start': date.today().isoformat()}}
        }
    }
    r = requests.post(f'{NOTION_API}/pages', json=payload, headers=HEADERS)
    return r.json()

def sync_revenue_to_notion(ledger_entries: list):
    """Push confirmed revenue from gc_ledger to Notion"""
    synced = 0
    for entry in ledger_entries:
        result = create_deal(
            company=entry.get('customer_id', 'Unknown Customer'),
            contact_email=entry.get('email', 'noreply@garcar.app'),
            value=float(entry.get('amount', 0)),
            source=entry.get('source', 'stripe'),
            stage='Closed Won'
        )
        if result and 'id' in result:
            synced += 1
    print(f'Synced {synced}/{len(ledger_entries)} entries to Notion')
    return synced

if __name__ == '__main__':
    # Test
    result = create_deal('Test Corp', 'test@testcorp.com', 999.00, 'shopify', 'Closed Won')
    if result and 'id' in result:
        print(f"✅ Created Notion deal: {result['id']}")
    else:
        print(f"Result: {result}")
