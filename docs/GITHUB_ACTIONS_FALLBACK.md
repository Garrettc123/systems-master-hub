# GitHub Actions-independent Garcar operator

## Scope and status

GitHub Actions failures in `Garrettc123/systems-master-hub` have been observed with zero executed steps. This runner **bypasses** those GitHub-hosted Actions runners; it does not repair runner allocation, GitHub billing, or repository Actions settings. No code merge, deployment, financial transfer, email, secret rotation, or order execution occurs.

All five actions use the trusted `scripts/operator_manual.py`. JSON/Markdown reports are produced with SHA-256 checksums. Hashes establish local self-consistency; without an external trusted anchor they are **not** immutable proof.

## Android Termux / Linux: local audit, no GitHub Actions

From your existing **systems-master-hub** checkout:

```bash
pkg install python git # Termux only; on Ubuntu use apt if needed
python -m pip install PyYAML==6.0.2 # optional dependency needed for validate-all
bash scripts/garcar-fallback.sh --actions all --trusted-tests
cat operator-evidence/fallback-summary.md
```

If you prefer no package installs, omit `validate-all` and run `--actions inventory-report,security-scan,dry-run-deploy`.

## Clone and audit a public GitHub branch, no GitHub Actions

```bash
python scripts/github_ci_fallback.py \
  --repository Garrettc123/systems-master-hub \
  --ref fix/operator-manual-audit-20261106 \
  --actions all --trusted-tests \
  --output ./external-operator-evidence
```

The source is cloned into a temporary directory without submodules. The trusted local runner performs the inspections; it does not execute scripts from that clone. GitHub authentication is not necessary for a public clone. `--repository` is restricted to `owner/name` on `github.com`; private repositories require a separately authenticated, locally prepared checkout via `--root`.

## External runner/container option

This project contains `Dockerfile.external-ci`, which can run on a machine with Docker (or be built as a private, non-public Railway worker after owner approval). It has no public HTTP control endpoint.

```bash
docker build -f Dockerfile.external-ci -t garcar-external-ci .
mkdir -p operator-evidence
docker run --rm -v "$PWD:/source:ro" -v "$PWD/operator-evidence:/reports" \
  garcar-external-ci --root /source --actions all --output /reports
```

The container does not expose ports or have access to Stripe/bank keys. Do not put personal financial data into repository reports or attach live secrets to the worker. Docker Compose schema inspection may warn when Docker CLI is unavailable inside the isolated container, and that warning must not be disguised as a pass.

## GitHub commit statuses (optional; requires write-scoped token)

With a token already managed in your shell environment and explicitly authorized for **Commit statuses: write**:

```bash
python scripts/github_ci_fallback.py --repository Garrettc123/systems-master-hub \
  --ref fix/operator-manual-audit-20261106 --actions all \
  --publish-status --output ./operator-evidence
```

Publishes ONLY the separate `garcar/external-operator` status on the inspected commit. It does not override, fake, or satisfy any existing required GitHub Actions checks. No tokens are printed or stored in reports. If the token is unavailable or permissions fail, reports are still produced and the status remains unpublished. Do not grant a broad token solely for this option.

## Fail-closed limits

- Repository issues may remain: GitHub Actions `startup_failure` requires GitHub-side diagnosis. Branch protection may require GitHub-hosted checks; external operator evidence cannot bypass those requirements.
- A green external check only covers its explicitly listed actions. It does not certify build/deployment success, live Stripe settlement, security compliance, or real customer revenue.
- `check-external-repos` without a verified token reports unknown access instead of incorrectly claiming repositories are missing.
- `--trusted-tests` executes ONLY the bundled operator test files, never arbitrary scripts from a freshly cloned repository.
- Manual reports are local artifacts; owner is responsible for storing an authenticated copy if third-party audit proof is needed.