"""Linear Sprint Automation — GARCAR Enterprise"""
import os, requests

LINEAR_API = 'https://api.linear.app/graphql'
API_KEY = os.environ.get('LINEAR_API_KEY', '')
TEAM_ID = os.environ.get('LINEAR_TEAM_ID', '')
HEADERS = {'Authorization': API_KEY, 'Content-Type': 'application/json'}

REVENUE_ACTIVATION_TASKS = [
    ('🔵 Activate Base USDC settlement', 'Connect garcar-payment-loop to Base L2 mainnet. Deploy base_payment_check.py. Set BASE_RPC_URL and WALLET_ADDRESS secrets.', 1),
    ('🛒 Launch Shopify AI product catalog', 'Deploy 5 AI products to Shopify storefront. Run shopify_sync.py deploy_catalog(). Connect Stripe payment gateway.', 1),
    ('🗄️ Wire Supabase realtime to Zeus Dashboard', 'Run Supabase schema SQL. Enable realtime on gc_ledger. Connect Zeus dashboard websocket to supabase_realtime.', 1),
    ('🤖 Deploy HuggingFace lead scorer to production', 'Deploy hf_score_leads.py as Supabase Edge Function. Wire to lead-enrichment-engine output queue.', 2),
    ('📝 Notion CRM pipeline sync', 'Connect atlas-dashboard to Notion deal database. Sync all confirmed revenue entries daily.', 2),
    ('💬 Slack revenue alert bot', 'Deploy Supabase Edge Function revenue-alert. Wire to #revenue-ops Slack channel.', 2),
    ('⚡ Full GitHub Actions sweep workflow', 'Deploy full-sweep.yml to all 5 core revenue repos. Test all 7 platform integrations.', 3),
    ('🔐 Audit and rotate all API secrets', 'Review GARCAR-AUTOKEY.md. Rotate any secrets older than 30 days. Document in GARCAR-SECURITY-OPS.', 3),
]

def create_issue(title: str, description: str, priority: int) -> dict:
    mutation = '''
    mutation CreateIssue($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
        issue { id identifier title url }
      }
    }'''
    variables = {
        'input': {
            'title': title,
            'description': description,
            'teamId': TEAM_ID,
            'priority': priority,
        }
    }
    r = requests.post(LINEAR_API,
                      json={'query': mutation, 'variables': variables},
                      headers=HEADERS)
    data = r.json()
    if 'errors' in data:
        print(f'Linear error: {data["errors"]}')
        return {}
    return data.get('data', {}).get('issueCreate', {}).get('issue', {})

def auto_create_sweep_issues():
    if not API_KEY or not TEAM_ID:
        print('Set LINEAR_API_KEY and LINEAR_TEAM_ID')
        return
    print('Creating GARCAR Full Sweep issues in Linear...')
    for title, desc, priority in REVENUE_ACTIVATION_TASKS:
        issue = create_issue(title, desc, priority)
        if issue:
            print(f"✅ {issue.get('identifier')} — {issue.get('url')}")
        else:
            print(f"⚠️  Failed to create: {title}")

if __name__ == '__main__':
    auto_create_sweep_issues()
