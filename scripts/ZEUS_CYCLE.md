# ZEUS governed cycle

This entrypoint fixes the missing scripts/zeus-cycle.sh without replacing the existing ZEUS Termux operator or duplicating the Garcar Command Center.

## Command

    bash scripts/zeus-cycle.sh \
      "Upgrade systems off dry-run — full Sovereign One stack" \
      "Garcar revenue + BioForge organs + AXIOM-12" \
      5000

The three positional parameters are a directive, a reporting scope, and a **maximum work-unit ceiling** (1–5000). The number 5000 is NOT an instruction to execute 5,000 API calls or make 5,000 changes.

Default ZEUS_MODE=observe performs actual outbound read-only HTTPS checks to the existing deployed RHNS Command Center (/api/health) and Garcar Revenue app (/health). It is not a simulator, but a reachable health endpoint alone does not prove authentication, paid customers, or integration.

Optional ZEUS_MODE=l0 performs **at most four** signed L0 requests to the existing Garcar RHNS endpoint /api/eve/l0/dispatch, for the observer, governance, revenue_intelligence and ceo roles. L0 requires an existing EVE_L0_DISPATCH_KEY in the host's secure environment, length >=48. Never put this key in source control or chat. The client signs each request using the actual server contract, verifies the signed response, and requires a completed_local/effect=none receipt plus a ledger event hash. It stops immediately after a failed signed request. These operations are local-only analytical directives, not customer outreach, billing, CRM modifications, or full-stack agent delegation.

Run L0 on an approved host only:

    ZEUS_MODE=l0 bash scripts/zeus-cycle.sh "Observe verified revenue operations" "RHNS local L0" 5000

## Results and evidence

Every accepted invocation writes .zeus/receipts/<run_id>.json, including checks, receipt IDs and hashes (when independently returned by the server), unverified and missing targets, and a SHA-256 hash of the local report. The report is locally hashable, **not immutable or independently attested**. Keep evidence artifacts in controlled storage.

Exit 0: full declared stack verified.
Exit 2: shell invocation error.
Exit 3: blocked or incomplete: never report a simulated or partial result as a successful full-stack upgrade.

Known missing evidence (as of initial implementation):
- The Sovereign worker is a deployed, scheduled **diagnostic** process, not a remote arbitrary command executor. Its audit is not accessible from this script.
- BioForge Revenue has a source manifest, but its deployed endpoint and execution receipts have not been verified.
- AXIOM-12 has no verified authenticated implementation.
- Existence of a service or a successful Railway deploy is not proof of runtime authorization or that revenue occurred.

## GitHub-hosted execution (no extra server required)

After the PR is merged, Actions > ZEUS Governed Cycle > Run workflow provides an on-demand hosted runner. Choose observe or l0; l0 only works if EVE_L0_DISPATCH_KEY is already present as an authorized GitHub Actions secret. The workflow uploads the JSON evidence and exits nonzero when the full stack remains blocked. GitHub-hosted runner availability depends on the account's Actions/billing state. It does not silently turn on production effects.

## Existing systems and next gates

- Garcar command center source: Garrettc123/garcar-command-center.
- Sovereign Railway worker source: Garrettc123/garcar-deploy-engine, feat/sovereign-worker-auditability-20261107; local diagnostic grants only.
- BioForge source: Garrettc123/revenue-automation-organ.
- Existing mobile operator: scripts/zeus-full-termux.sh.

Before enabling full live business automation, authenticate the actual BioForge/AXIOM-12 implementations, define action-specific grants with narrow scopes, verify replay protection and ledger reconciliation, and require separate explicit approval for outbound messages, payment initiation, refunds and customer-data mutations. No generic shell-execution or disable-safety command is provided by this cycle.
