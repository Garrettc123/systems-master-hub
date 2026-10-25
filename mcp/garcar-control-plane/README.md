# Garcar Control Plane MCP

A local-first, fail-closed MCP server for Garcar Enterprise. This initial release provides governance primitives and integration inventory; it does **not** claim that external services are connected or that production actions are enabled.

## Included tools

- `control_plane_status` — process and ledger status.
- `list_integrations` — allowlisted integrations and **credential presence only**.
- `evaluate_action_policy` — evaluate an action without executing it.
- `request_action` — create a durable approval request with evidence references.
- `decide_action` — approve/reject a request using a separately configured operator token.
- `get_action_request` — inspect request status.
- `recent_audit_events` — inspect hash-linked audit events.
- `execute_action` — fail-closed execution entrypoint; blocks because no external action adapters are registered.

## Safety model

- Default transport is MCP stdio. Do not expose this process to a network without adding authenticated transport, authorization, rate limits, and deployment review.
- No shell, arbitrary SQL, arbitrary URL fetch, arbitrary HTTP write, or secret-read tool is exposed.
- Secret values are never returned. Environment checks return booleans only.
- Actions are allowlisted. Evidence references are required to create requests.
- Approval is separate from execution. Approval alone never executes an external action.
- All unknown actions and unregistered adapters fail closed.
- SQLite is suitable for local development/single-node use only. Production multi-worker deployment requires PostgreSQL, migrations, retention, backup/restore, monitoring, and security review.
- The audit hash chain detects accidental/tampered changes but is not a substitute for a remote immutable audit sink.

## Install and run

Python 3.11+ is required.

```bash
cd mcp/garcar-control-plane
python -m venv .venv
. .venv/bin/activate
pip install -e '.[test]'
export GARCAR_MCP_DB="$PWD/data/garcar_mcp.sqlite3"
# Set this only in the trusted local operator environment; never commit it.
export GARCAR_OPERATOR_APPROVAL_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
garcar-control-plane-mcp
```

The process speaks MCP over stdio and is intended to be launched by an MCP-compatible client. Keep the operator token in the secret manager/environment of that client host.

## MCP client configuration example

Add the following to the MCP client's configuration, adjusting the absolute path to your checkout. Do not put tokens in this JSON.

```json
{
  "mcpServers": {
    "garcar-control-plane": {
      "command": "/absolute/path/to/systems-master-hub/mcp/garcar-control-plane/.venv/bin/garcar-control-plane-mcp",
      "args": [],
      "env": {
        "GARCAR_MCP_DB": "/absolute/path/to/secure-state/garcar_mcp.sqlite3"
      }
    }
  }
}
```

If the client needs `GARCAR_OPERATOR_APPROVAL_TOKEN`, inject it using the host's supported secret facility; do not paste it into project files.

## Existing ecosystem integrations

The repository already documents a source gateway and separate integration patterns for GitHub, Notion, Linear, Stripe, Vercel, SendGrid, Vault, and other services. This MCP server inventories those integrations but does not assume their credentials or runtime endpoints are available.

Before connecting an integration:
1. identify the authoritative existing adapter and its repository/revision;
2. register a narrow, typed adapter for that service;
3. use the minimum credential scopes and retrieve secrets from the approved secret manager at runtime;
4. add mocked contract tests and a read-only canary;
5. enable writes only after a human-approved change and end-to-end evidence.

## Test

```bash
pytest
```

Tests cover fail-closed policy, missing evidence, operator-token rejection, approval separation, and audit recording. Passing unit tests does not establish external connectivity or production readiness.
