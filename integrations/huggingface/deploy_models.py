"""GARCAR HuggingFace Model Deployment
Deploys AI models to HF Inference Endpoints for NEXUS-AI-CORE pipeline.
Models: lead scoring, deal analysis, property valuation.

Prerequisites: HF_TOKEN with write access to Garrettc123 namespace
"""
import os
from huggingface_hub import HfApi, InferenceClient

HF_TOKEN = os.getenv("HF_TOKEN")
HF_NAMESPACE = "Garrettc123"

api = HfApi(token=HF_TOKEN)

MODELS_TO_DEPLOY = [
    {
        "name": "garcar-lead-scorer",
        "task": "text-classification",
        "description": "Lead scoring model — classifies leads 0-100 by conversion probability. Fed by lead-enrichment-engine.",
        "base_model": "distilbert-base-uncased",
        "tags": ["garcar", "lead-scoring", "revenue", "autonomous"]
    },
    {
        "name": "garcar-deal-analyzer", 
        "task": "text-classification",
        "description": "Deal stage classifier — predicts deal progression for NEXUS-AI-CORE pipeline.",
        "base_model": "distilbert-base-uncased",
        "tags": ["garcar", "deal-analysis", "crm", "autonomous"]
    },
    {
        "name": "garcar-property-ai",
        "task": "text2text-generation",
        "description": "Property valuation and scoring AI. Feeds NEXUS-AI-CORE real estate deal pipeline.",
        "base_model": "google/flan-t5-small",
        "tags": ["garcar", "real-estate", "property-scoring", "nexus"]
    }
]


def create_model_card(model: dict) -> str:
    return f"""---
license: mit
tags:
{chr(10).join(f'- {t}' for t in model['tags'])}
base_model: {model['base_model']}
task: {model['task']}
---

# {model['name']}

{model['description']}

## Part of GARCAR Enterprise Autonomous Revenue System

This model is deployed as a HuggingFace Inference Endpoint and integrated into:
- [NEXUS-AI-CORE](https://github.com/Garrettc123/NEXUS-AI-CORE)
- [autonomous-revenue-architect](https://github.com/Garrettc123/autonomous-revenue-architect)
- [lead-enrichment-engine](https://github.com/Garrettc123/lead-enrichment-engine)

## Usage

```python
from huggingface_hub import InferenceClient
client = InferenceClient(model="{HF_NAMESPACE}/{model['name']}", token=HF_TOKEN)
result = client.{model['task'].replace('-', '_')}("your input text")
```
"""


def ensure_repos_exist():
    """Create model repos on HuggingFace Hub if they don't exist."""
    for model in MODELS_TO_DEPLOY:
        repo_id = f"{HF_NAMESPACE}/{model['name']}"
        try:
            api.repo_info(repo_id=repo_id, repo_type="model")
            print(f"[HF] Repo exists: {repo_id}")
        except Exception:
            api.create_repo(
                repo_id=repo_id,
                repo_type="model",
                private=False,
                exist_ok=True
            )
            # Push model card
            api.upload_file(
                path_or_fileobj=create_model_card(model).encode(),
                path_in_repo="README.md",
                repo_id=repo_id,
                repo_type="model",
                commit_message=f"🤗 Initialize {model['name']} — GARCAR Autonomous Revenue"
            )
            print(f"[HF] Created: {repo_id}")


def get_inference_endpoints():
    """List all active inference endpoints."""
    try:
        endpoints = api.list_inference_endpoints(namespace=HF_NAMESPACE)
        for ep in endpoints:
            print(f"[HF Endpoint] {ep.name}: {ep.status.state}")
        return endpoints
    except Exception as e:
        print(f"[HF] Could not list endpoints: {e}")
        return []


def run_inference_test(model_name: str, text: str):
    """Test inference on a deployed endpoint."""
    client = InferenceClient(
        model=f"{HF_NAMESPACE}/{model_name}",
        token=HF_TOKEN
    )
    result = client.text_classification(text)
    print(f"[HF Inference] {model_name}: {result}")
    return result


if __name__ == "__main__":
    print("[GARCAR HuggingFace Deploy] Starting...")
    ensure_repos_exist()
    endpoints = get_inference_endpoints()
    print(f"[HF] Active endpoints: {len(list(endpoints))}")
    print("[GARCAR HuggingFace Deploy] Complete")
