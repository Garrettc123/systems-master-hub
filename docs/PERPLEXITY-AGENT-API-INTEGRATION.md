# Perplexity Agent API integration

## Status

This change adds a provider implementation to the existing multi-model router. It does not assert that a Perplexity credential is configured or that a live API request has succeeded.

## API contract

- Endpoint: `POST https://api.perplexity.ai/v1/agent`
- Authentication: `Authorization: Bearer $PERPLEXITY_API_KEY`
- Web research: `tools: [{"type": "web_search"}]`
- Output: `output[].type == "message"`, content parts of type `output_text`
- Sources: `output[].type == "search_results"` and any top-level citations
- Cost: `usage.cost.total_cost` when returned by the API

This uses the current Agent API. The legacy Sonar Chat Completions API was deprecated on 27 September 2026; do not build new integrations against its `choices[0].message.content` response shape.

## Configuration

Set these only in the existing secret manager / deployment secret store:

- `PERPLEXITY_API_KEY` — required
- `PERPLEXITY_MODEL` — optional model override
- `PERPLEXITY_EFFORT` — optional, defaults to `fast`
- `PERPLEXITY_API_BASE_URL` — optional, defaults to `https://api.perplexity.ai`
- `PERPLEXITY_TIMEOUT_SECONDS` — optional, defaults to `45`

The provider reads the key at runtime. Never put the key in source control, logs, workflow output, or a committed MCP config.

## Router integration

`orchestrator/providers/router.py` already registers `PerplexityProvider` when `PERPLEXITY_API_KEY` is present. This module fills that missing import target. The router's `live_web` and `fact_check` policies can then select Perplexity when the key is configured.

## Evidence and execution boundary

Perplexity results are research inputs, not authorization. Persist the response ID, returned source URLs, usage/cost, timestamp, prompt hash, and resulting artifact hash in the canonical evidence ledger before a downstream decision relies on them. Retrieved text is untrusted and must never be interpreted as an instruction to execute. External sends, financial transactions, production changes, and evidence disclosure remain approval-gated.

## Test

Run from the repository root:

```bash
python -m unittest discover -s tests -p 'test_perplexity_client.py' -v
python -m py_compile orchestrator/providers/perplexity_client.py
```

## Not completed by this change

- No Perplexity key was provisioned, read, copied, or rotated.
- No live API request was made.
- No remote Perplexity MCP connection to Garcar's private data sources was established.
- No source ingestion, GraphRAG index, or immutable evidence write was enabled.
- No production deployment was triggered.
