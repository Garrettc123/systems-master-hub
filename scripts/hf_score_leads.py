"""HuggingFace Lead Scoring — GARCAR Enterprise"""
import os, json, re
try:
    from huggingface_hub import InferenceClient
    client = InferenceClient(token=os.environ.get('HF_TOKEN', ''))
except ImportError:
    client = None

LEAD_SCORING_PROMPT = """You are a B2B sales qualification AI for GARCAR Enterprise.
Given this lead profile, output ONLY a JSON object with:
- score (0-100 integer)
- tier ("hot", "warm", or "cold")
- recommended_product (from: "Smart Contract Audit", "Lead Enrichment API", "NEXUS AI Core", "Butler Automation")
- personalized_opener (1 sentence, specific to their company)

Lead: {lead_data}

JSON output:"""

def score_lead(lead_data: dict) -> dict:
    if not client:
        return {'score': 50, 'tier': 'warm', 'recommended_product': 'NEXUS AI Core',
                'personalized_opener': f'We can help {lead_data.get("company", "your company")} automate revenue.'}
    
    response = client.text_generation(
        LEAD_SCORING_PROMPT.format(lead_data=json.dumps(lead_data, indent=2)),
        model='mistralai/Mixtral-8x7B-Instruct-v0.1',
        max_new_tokens=256,
        temperature=0.1
    )
    match = re.search(r'\{.*\}', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            pass
    return {'score': 50, 'tier': 'warm', 'recommended_product': 'NEXUS AI Core',
            'personalized_opener': 'Looking forward to connecting.'}

def batch_score_leads(leads: list) -> list:
    results = []
    for lead in leads:
        scored = {**lead, 'hf_score': score_lead(lead)}
        results.append(scored)
        print(f"Scored {lead.get('email', 'unknown')}: {scored['hf_score'].get('tier', 'unknown')} ({scored['hf_score'].get('score', 0)})")
    return results

if __name__ == '__main__':
    # Test with sample lead
    test_lead = {
        'company': 'TechCorp Inc',
        'email': 'cto@techcorp.com',
        'role': 'CTO',
        'company_size': '50-200',
        'industry': 'SaaS',
        'tech_stack': ['Ethereum', 'Solidity', 'React']
    }
    result = score_lead(test_lead)
    print(json.dumps(result, indent=2))
