# v3.2 Master Systems Release — evidence gate (proposed)

This directory is an **audit candidate**, not a production release or certificate.

## Scope and findings (2026-11-13)

The operator supplied the assertion that there are 23 production-baseline systems.
That outline named 21 components when compound bullets were split, leaving two
unnamed entries. This manifest retains **23 explicit slots** without inventing
the last two names.

At the time of the audit:
- 15 slots are mapped to candidate repositories actually located in GitHub.
  A repository match is **not** proof of the exact claimed capability or version.
- 8 slots remain unmapped, including the two unspecified entries.
- 0/23 are independently production-certified by this tool.

Historic fleet totals in SYSTEMS-INVENTORY.json, SYSTEM_REGISTRY.json,
BUILD-STATUS.md, and SYNC-2026-11-04.md refer to different dates. Do not
combine their totals or treat them as a live count.

## Run

Requires Python 3.11+ and no third-party packages:

    python release_v3_2/verify.py --report release-v3.2-audit.json
    cd release_v3_2 && python -m unittest -v test_verify

A **release promotion** is intentionally blocked:

    python release_v3_2/verify.py --release-gate

The inventory command exits 0 for a structurally valid inventory. The
release-gate command exits 3 until independently corroborated evidence is
available. Neither a successful CI run nor an editable JSON flag can bypass
this. This is an **offline schema/consistency gate**, not a remote proof
validator, cryptographic signer, or deployment monitor.

## Production qualification — required future evidence

For each entry, confirm against authenticated provider records:
1. The canonical owning repository, release tag, and exact 40-character SHA.
2. Completed tests and security checks on that *same* SHA, with run references.
3. A successful production deployment pointing to that SHA (not merely staging).
4. A direct authorized health probe and functional end-to-end request.
5. The relevant RHNS policy decision, signed approval where required, event
   receipt, and replay/audit-chain verification.
6. For revenue-bearing paths, a real settled customer charge, paid-order
   identity, fulfillment receipt, and reconciliation. No test cards or
   synthetic revenue evidence.

The verifier never declares any component production-verified on the
strength of operator descriptions, README badges, or untrusted self-attested
JSON. Promotion requires an independently implemented authenticated
re-verification procedure and release-owner review.

## Runtime safety

The audit is read-only. It does not call Stripe, send outreach, change
customer records, publish releases, deploy software, or start agents.

## Sources

- Existing fleet audit: [SYNC-2026-11-04.md](../SYNC-2026-11-04.md)
- Existing registry: [SYSTEM_REGISTRY.json](../SYSTEM_REGISTRY.json)
- Existing verification definitions: [VERIFIED_INVENTORY.md](../VERIFIED_INVENTORY.md)


## Second gate: source-to-deployment reconciliation

Observed against connected Railway on 2026-11-13, five projects
exposed 32 services (24 staging and 8 production). All latest listed
deployments had status SUCCESS, but these are *not* v3.2 certifications.

A deliberately sanitized point-in-time cache is stored in
provider_observations_2026-11-13.json. Only candidate repositories with
matching source names are retained:
- GCE-008 / garcar-data-room — staging deployment at commit
  30ee9796b094c001f812c99116d8c718046d00d2,
  different from the manifest-pinned default-branch commit.
- GCE-010 / mars-api — staging deployment at commit
  429ad12f9bce19e442a652bdddbb35c93a3d859c,
  different from the manifest-pinned default-branch commit.

There are 2 matching repository names, **zero matching source commits**
and **zero production source matches** for the 15 candidate mappings.
This does **not** mean other deployed systems are nonexistent; it means
the documented v3.2 candidate revisions have not been proven deployed.

Run both classes of tests and generate a second coverage artifact:

    cd release_v3_2 && python -m unittest -v test_verify test_reconcile test_verify_commerce
    python reconcile.py --observations provider_observations_2026-11-13.json --report source-deployment-coverage.json

The tool accepts offline observations only. It is not a provider API
client, an independently signed attestation or a replacement for a
fresh authenticated verification at release time. No provider credentials,
internal service IDs, or customer information are stored here.

As of Nov 13 GitHub Actions has been returning failure with **zero
executed job steps** on this PR; the owner must resolve the hosted
runner/Actions execution issue before using a GitHub workflow result as
test evidence. The standalone Python reconciliation code has passed
7 local contract tests, which do not cover the main product suite or
replace hosted CI.


## Third gate: live checkout configuration vs. collected revenue

The 2026-11-13 authenticated read-only Stripe check confirmed:
- Website canonical checkout is pinned in Garrettc123/garcar-enterprise-os-ui,
  commit 619538bc384fb06036616d2afc0b9632084b0d1a,
  checkout-validation.mjs.
- The matching $497 payment link was active in live mode and its line item
  was one unit at 49700 USD cents.
- The separate $2,500 installation link was active in live mode, at
  250000 USD cents. This is **not** the canonical main-site purchase action.
- Stripe GET /v1/charges returned 4 records, all failed, has_more=false,
  and no recorded successful paid charge. This query cannot establish that
  all future payment or payout activity is absent.
- No independent recent direct HTTP probe to the current site deployment,
  authorized paid-customer handoff, complete fulfillment receipt or payment
  ledger reconciliation was verified in this audit.

The sanitized source observations are in
commerce_observations_2026-11-13.json. This is an **unsigned audit snapshot**,
not a Stripe-signed receipt and not something the release gate trusts as
authenticated proof.

    python release_v3_2/verify_commerce.py --observations release_v3_2/commerce_observations_2026-11-13.json --report release_v3_2/commerce-coverage.json
    cd release_v3_2 && python -m unittest -v test_verify test_reconcile test_verify_commerce

The verifier establishes snapshot schema/checkout consistency only. It
**never** reports verified revenue or fulfillment. A configured active
payment link is not a paid order. An operator must independently verify
a real Stripe succeeded payment, customer-authorized intake, delivery
receipt and reconciled ledger before commercial release acceptance.

## Source qualification status after follow-up

GCE-003 RHNS Cognitive Genome is now mapped as a **candidate** to
Garrettc123/RHNS-Architecture at commit
f8f903ec5250ec20793f8eb27022146c2df30780, where code for LATS
reasoning, a tiered memory controller and associated tests was inspected.
There is no independent proof that an RHNS Cognitive Genome version was
deployed. The registry now has 15 candidate repository mappings, 8
unmapped entries, 0 same-commit Railway deployment matches for the
mapped components, and 0 independently production-certified.


## Fourth gate: externally probed public runtime (read-only)

On 2026-11-13, a fresh external GET fetch of the public deployment
returned the homepage and three diagnostic endpoints. A separate
authenticated Railway read confirmed matching HTTP **200** proxy records
between 22:56:24 and 22:56:25 UTC.

- /: Garcar Enterprise | Texas-Wide Lead Follow-Up Review, a $497
  offer and the canonical Stripe-hosted checkout link.
- /health: {"status":"ok","service":"garcar-texas-followup"}.
- /readyz: {"status":"configured","acquisition":"configured_unverified",
  "upstream_probe":"not_performed", ...}.
- /integrationz: authenticated_read_only, credential_match=true,
  lead_created=false, payment_attempted=false, customer_intake=not_tested.

Railway describes the **garcar-commerce-preview** service as
online, with latest deployment SUCCESS, in the production environment
at 2026-11-13T16:52:25Z. The Railway service configuration identifies
the main branch of Garrettc123/garcar-enterprise-os-ui but **does not
show the deployed source SHA** in the observed config; do not assert
commit parity from a repository's HEAD.

Sanitized evidence: runtime_observations_2026-11-13.json.

Scope: externally reachable public site and explicit read-only
diagnostics, NOT a live acquisition transaction or successful
customer payment. In particular, the service's own upstream status
is configured_unverified and it reports no real customer intake test.
Do not alter those facts in the audit to promote a release.
