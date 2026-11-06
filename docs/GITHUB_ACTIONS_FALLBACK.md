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
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/source:ro" -v "$PWD/operator-evidence:/reports" \
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

## Repeated validation independent of Actions: new supervisor

The trusted supervisor `scripts/github_ci_supervisor.py` monitors a **public GitHub branch** from a Linux machine, Termux or a private background worker. It fetches the remote HEAD SHA with `git ls-remote`, avoids repeated costly validation for unchanged passing/warning commits, runs the trusted existing validator on new commits, and keeps evidence in a folder named for the actual inspected SHA.

### Run immediately once (no GitHub Actions)

```bash
python scripts/github_ci_supervisor.py \
  --repository Garrettc123/systems-master-hub \
  --branch fix/operator-manual-audit-20261106 \
  --max-cycles 1 --output ./operator-evidence-supervised
```

### Continuous periodic schedule (Linux, Termux or private Docker worker)

```bash
python scripts/github_ci_supervisor.py \
  --repository Garrettc123/systems-master-hub \
  --branch main --interval-seconds 3600 --max-cycles 0 \
  --output ./operator-evidence-supervised
```

For Android Termux, run this command when the device is powered and awake; Android background limits mean a persistent process is **not a guaranteed scheduled service**. For reliable 24/7 operation, use your existing always-on Linux host or an approved private Railway worker.

The operator report is written at `operator-evidence-supervised/<commit-sha>/fallback-manifest.json`; the latest inspection and evidence hash are recorded in `operator-evidence-supervised/supervisor-state.json`. The program enforces a single process for the same output directory using an OS file lock. It will **not** report a prior success as a fresh success after a network error or SHA mismatch.

### Container worker (optional, no new paid service created)

Build the existing Dockerfile once, then run the same source as a persistent private worker:

```bash
docker build -f Dockerfile.external-ci -t garcar-external-ci .
mkdir -p operator-evidence-supervised
docker run --rm --read-only --tmpfs /tmp:rw,nosuid,nodev,size=256m \
  --mount "type=bind,src=$PWD/operator-evidence-supervised,dst=/reports" \
  --entrypoint python garcar-external-ci \
  /work/scripts/github_ci_supervisor.py \
  --repository Garrettc123/systems-master-hub --branch main \
  --interval-seconds 3600 --max-cycles 0 --output /reports
```

This reads public GitHub source only and does not need Stripe, Supabase, Railway or GitHub write credentials. For private repositories, provide a separately prepared authorized local checkout to the original fallback runner; do not enable a public remote clone with embedded credentials.

**Important:** The container needs outbound access to `github.com`, write access to its report volume, and git. It must not expose a public HTTP endpoint. Stop the worker before changing its trust policy.

### Optional publication boundary

The supervisor accepts `--publish-status` only when the owner explicitly supplies an appropriately scoped `GH_TOKEN`. It publishes the separate `garcar/external-operator` commit status via the underlying fallback runner; it never overrides existing required checks. No publication occurs by default.

### Current failure / recovery limitations

A GitHub Actions `startup_failure` with **zero executed steps** cannot be repaired just by changing application scripts. Review run annotations, GitHub Actions billing/budget and repository workflow state, then contact GitHub Support if those are healthy. The external supervisor does **not** override branch protection, GitHub billing holds, paid runner limits, or missing privileges.

The full hub has not been inspected end-to-end by this session's container because DNS resolution to `github.com` is unavailable; offline supervisor regression tests do not establish a clean remote execution. No paid worker was provisioned.
