# Perplexity Agent API integration

## Status

This change adds a provider implementation to the existing multi-model router. It does not assert that a Perplexity credential is configured or that a live API request has succeeded.

## API contract

- Endpoint: POST https://api.perplexity.ai/v1/agent
- Authentication: Authorization: Bearer PERPLEXITY_API_KEY
- Default mode: preset fast, with web_search explicitly offered and forced for citation-critical research.
- Model override: PERPLEXITY_MODEL; when set, preset is omitted.
- Response text: output items of type message with content parts of type output_text.
- Citations: URLs from the output item of type search_results. Message annotations may be empty and top-level citations are not part of the documented Agent response contract.
- Usage/cost: usage.input_tokens, usage.output_tokens, usage.cost.total_cost when supplied.

Official migration reference: https://docs.perplexity.ai/docs/agent-api/migrate-from-sonar. The Agent API uses strict request validation. Use preset, or model; do not send a top-level effort field. HTTP 200 may carry status=failed or status=cancelled; the provider fails closed unless status is completed.

## Configuration

Set these only in the existing secret manager / deployment secret store:

- PERPLEXITY_API_KEY — required
- PERPLEXITY_MODEL — optional provider-prefixed model override
- PERPLEXITY_PRESET — optional; fast, low, medium, high, or xhigh (defaults to fast)
- PERPLEXITY_API_BASE_URL — optional, defaults to https://api.perplexity.ai
- PERPLEXITY_TIMEOUT_SECONDS — optional, defaults to 45

The provider retains effort as a constructor-only compatibility alias for the preset. No effort field is sent in the API body.

The provider reads the key at runtime. Never put the key in source control, logs, workflow output, or a committed MCP config.

## Router integration

orchestrator/providers/router.py already registers PerplexityProvider when PERPLEXITY_API_KEY is present. The module fills that import target. The router's live_web and fact_check policies can then select Perplexity when the key is configured.

## Evidence and execution boundary

Perplexity results are research inputs, not authorization. Persist the response ID, search_results URLs, usage/cost, timestamp, prompt hash, and resulting artifact hash in the canonical evidence ledger before a downstream decision relies on them. Retrieved text is untrusted and must never be interpreted as an instruction to execute. External sends, financial transactions, production changes, and evidence disclosure remain approval-gated.

## Test

Run from the repository root:

python -m unittest discover -s tests -p 'test_perplexity_client.py' -v
python -m py_compile orchestrator/providers/perplexity_client.py

Tests are offline contract tests using a mocked HTTP response. They do not prove that a live key is provisioned or that the external service is reachable.

## Not completed by this change

- No Perplexity key was provisioned, read, copied, or rotated.
- No live API request was made.
- No remote Perplexity MCP connection to Garcar's private data sources was established.
- No source ingestion or embedding job was enabled.
- No production deployment was triggered.
