"""Offline contract tests for the Perplexity Agent API provider."""
import asyncio
import json
import unittest
from unittest.mock import patch

from orchestrator.providers.perplexity_client import PerplexityProvider


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class PerplexityProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_agent_api_request_extracts_text_sources_and_cost(self):
        payload = {
            "id": "resp_test",
            "status": "completed",
            "model": "sonar",
            "output": [
                {"type": "search_results", "results": [
                    {"title": "Source A", "url": "https://example.com/a"}
                ]},
                {"type": "message", "content": [
                    {"type": "output_text", "text": "Verified answer."}
                ]},
            ],
            "usage": {
                "input_tokens": 10,
                "output_tokens": 20,
                "cost": {"total_cost": 0.0123},
            },
        }
        provider = PerplexityProvider(api_key="test-key")
        with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(payload)) as mocked:
            result = await provider.generate("Find current evidence", system="Research only")

        self.assertTrue(result.ok)
        self.assertEqual(result.content, "Verified answer.")
        self.assertEqual(result.citations, ["https://example.com/a"])
        self.assertEqual(result.cost_usd, 0.0123)
        request = mocked.call_args.args[0]
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://api.perplexity.ai/v1/agent")
        self.assertEqual(body["tools"], [{"type": "web_search"}])
        self.assertEqual(body["input"], "Find current evidence")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-key")

    async def test_missing_key_fails_closed(self):
        provider = PerplexityProvider(api_key="")
        with patch.dict("os.environ", {"PERPLEXITY_API_KEY": ""}):
            provider.api_key = ""
            result = await provider.generate("query")
        self.assertFalse(result.ok)
        self.assertIn("not configured", result.error)

    async def test_json_mode_is_explicit_in_instructions(self):
        payload = {
            "status": "completed",
            "output": [{"type": "message", "content": [
                {"type": "output_text", "text": "{\"ok\":true}"}
            ]}],
            "usage": {},
        }
        provider = PerplexityProvider(api_key="test-key")
        with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(payload)) as mocked:
            result = await provider.generate("return JSON", json_mode=True)
        body = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertTrue(result.ok)
        self.assertIn("valid JSON only", body["instructions"])


if __name__ == "__main__":
    unittest.main()
