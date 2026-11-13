# v3.2 Master Systems Release — evidence gate (proposed)

This directory is an **audit candidate**, not a production release or certificate.

## Scope and findings (2026-11-13)

The operator supplied the assertion that there are 23 production-baseline systems.
That outline named 21 components when compound bullets were split, leaving two
unnamed entries. This manifest retains **23 explicit slots** without inventing
the last two names.

At the time of the audit:
- 14 slots are mapped to candidate repositories actually located in GitHub.
  A repository match is **not** proof of the exact claimed capability or version.
- 9 slots remain unmapped, including the two unspecified entries.
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
and **zero production source matches** for the 14 candidate mappings.
This does **not** mean other deployed systems are nonexistent; it means
the documented v3.2 candidate revisions have not been proven deployed.

Run both classes of tests and generate a second coverage artifact:

    cd release_v3_2 && python -m unittest -v test_verify test_reconcile
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
