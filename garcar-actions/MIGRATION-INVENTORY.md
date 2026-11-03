# Garcar Actions migration inventory

Date: 2026-11-02
Status: discovery snapshot, not a complete account-wide census.

## Evidence and scope

GitHub code search for runs-on: ubuntu-latest returned 100 matches; filtering those matches identified the workflow files below. A second search found two self-hosted-runner candidates. Search results are an index, not a complete recursive listing of every repository. This is a verified starting inventory, not a claim that all repositories/workflows have been enumerated.

## Discovered workflow candidates

| Repository | Workflow file(s) | Initial classification |
|---|---|---|
| autonomous-income-deployment | deploy.yml; terraform.yml; auto-approve-merge.yml | Deploy / infrastructure / privileged |
| ai-agent-platform | ci.yml | CI |
| termux-workspace-sync | ci.yml | CI / device sync |
| ai-business-automation-tree | ci.yml; deploy.yml; self-heal.yml | CI / deploy / remediation |
| NEXUS-Quantum-Intelligence-Framework | ci.yml | CI |
| devops-portfolio | ci.yml | CI |
| multimodal-input-api | ci.yml; deploy.yml | CI / deploy |
| nwu-protocol | ci.yml; ci-cd.yml; deploy.yml; release.yml; auto-pr.yml; codeql.yml | CI / deploy / release / security |
| garcar-enterprise-production | ci.yml; ci-cd.yml; deploy.yml; codeql.yml; revenue.yml; reach-pack.yml; gateway-ci.yml; sales-fleet.yml | CI / deploy / revenue / sales |
| RHNS-Architecture | ci.yml; deploy.yml | CI / deploy |
| TITAN-Autonomous-Business-Empire | titan-ci.yml | CI |
| tree-of-life-system | aws.yml; ci-cd.yml; ai-review.yml; sync-linear.yml; health-check.yml | Cloud deploy / CI / AI review / integration |
| ai-wealth-ecosystem | ci-cd.yml; docker-image.yml | CI / image build |
| zero-human-enterprise-grid | ci-cd.yml | CI / deploy |
| enterprise-unified-platform | ci-cd.yml; deploy.yml; self-heal.yml; auto-revenue.yml | CI / deploy / remediation / revenue |
| AutoGenesis-AI-Platform | build.yml | Build |
| autonomous-butler-core | ci-cd.yml; deploy.yml | CI / deploy |
| ultra-low-latency-ai-platform | deploy.yml | Deploy |
| nexusai-platform | deploy.yml | Deploy |
| master-deployment-auto-deploy-revenue | deploy.yml | Deploy / revenue |
| zero-human-orchestrator | deploy.yml | Deploy |
| tree-of-life-minimal | deploy.yml | Deploy |
| garcar-sovereign-control-plane | quality.yml | Quality |
| garcar-enterprise-os-ui | ui-check.yml | UI validation |
| garcar-enterprise-os-docs | docs-check.yml | Documentation |
| garcar-enterprise-os-infra | infra-check.yml | Infrastructure validation |
| customer-intelligence-branch | ci.yml | CI |
| ai-sales-engine | ci.yml | CI / sales code |
| enterprise-mlops-platform | ci.yml | CI / ML infrastructure |
| ai-consulting-automaton | ci.yml | CI |
| genesis-consciousness-deploy | ci.yml | CI |
| systems-master-hub | ci.yml | CI |
| atlas-agents | ci.yml | CI / agent code |
| garcar-control-plane | ci.yml | CI |
| NEXUS-AI-CORE | ci.yml | CI |
| autonomous-orchestrator-core | ci.yml | CI / orchestration |
| phone-backend-system-v2 | ci.yml | CI |
| garcar-repo-foundry | ci.yml | CI / repository tooling |
| apex-revenue-system | ci.yml | CI / revenue application |
| garcar-revenue-os | ci.yml; also local-actions/workflows/ci.json | CI / existing local runner |
| garcar-rhns-edge | ci.yml | CI / edge |
| defender-os | ci.yml | CI / security |
| mars-production | ci.yml | CI |
| customer-churn-predictor | ci.yml | CI / ML |
| garcar-qih-core | ci.yml | CI |
| garcar-star | ci.yml | CI |
| garcar-lead-intake | ci.yml | CI / lead intake |
| garcar-revenue-services | ci.yml | CI / revenue |
| smart-contract-auditor-ai | ci.yml | CI / security |
| garcar-shopify-app | ci.yml | CI / commerce |
| atlas-infrastructure | ci.yml | CI / infrastructure |
| lead-enrichment-engine | ci.yml | CI / data enrichment |
| atlas-integrations | ci.yml | CI / integrations |

## Self-hosted workflow candidates

- garcar-data-room/.github/workflows/evidence-release-gate.yml
- defender-os/.github/workflows/defender-os.yml

These require separate host/runner security review; do not assume they are safe to run on the same worker.

## Inspected workflow details

### systems-master-hub / .github/workflows/ci.yml
Four jobs were observed: YAML lint/parse, shell syntax checks, Docker Compose validation, and repository structure/JSON checks. Some checks are explicitly advisory and should retain their advisory semantics in migration tests.

### garcar-enterprise-production / .github/workflows/ci.yml
A least-privilege Python 3.11 smoke job installs backend requirements, compiles the backend, and imports main. The original workflow grants contents: read only to the job. Preserve least privilege; the Garcar runner must not inherit a broad GitHub write token.

### apex-revenue-system / .github/workflows/ci.yml
A CI job installs requirements and pytest, performs import checks, runs pytest tests/, and uploads diagnostics. Artifact retention/upload semantics need a Garcar artifact store before claiming parity.

### garcar-revenue-os / local-actions/runner.mjs
An existing local runner is present. Its runShell() calls spawnSync(..., {shell: true}) with inherited environment variables. Do not reuse that execution path for unattended or network-exposed jobs without isolation and policy hardening. Existing JSON workflow definitions are useful migration inputs, not proof of production safety.

## Migration policy

| Class | Examples | Treatment |
|---|---|---|
| Read-only CI | compile, lint, unit tests, import checks | First migration wave; disposable isolated workspace |
| Build/artifact | package builds, Docker image build, test artifacts | Requires resource limits and artifact retention controls |
| Security scans | CodeQL, dependency checks, secret scanning | Preserve tool/version and result semantics; no auto-remediation |
| Deployment | Railway/AWS/Vercel/SSH/Terraform apply | Disabled pending signed release, staging, rollback, and owner approval |
| Revenue/commerce | Stripe, Shopify, settlement, sales fleet, outreach | Disabled; no payment/customer mutation |
| Secrets/key rotation | Vault sync, token rotation, repository secret writes | Disabled; dedicated approval and audited secret broker required |
| Self-healing/auto-merge | PR merge, issue writes, repo mutation | Disabled pending policy and human approval |

## Migration sequence

1. Complete repository/workflow enumeration using repository trees, not code-search snippets alone.
2. Fetch each actual workflow file at a pinned commit; compute a source SHA-256; classify triggers, jobs, uses actions, commands, secrets, permissions, and side effects.
3. Translate only supported, read-only CI jobs to versioned Garcar workflow definitions.
4. Run in isolated, unprivileged disposable workspaces with no production secrets and compare outputs with the original intended checks.
5. Keep original GitHub workflows unchanged until parity evidence exists. Do not disable GitHub Actions as part of discovery or dry-run.
6. Enable one repository at a time after owner approval and a successful canary.
7. Keep deployments, financial actions, secret writes, outreach, merges, and self-healing behind separate approval gates.

## Current migration status

- Discovery snapshot: created from GitHub code-search results.
- Actual complete repository-tree census: not yet performed.
- Workflow translation: the hub's `structure-check` job has a native local-canary port in `migration/hub-structure.json`; the other jobs/repositories remain untranslated.
- Execution evidence: this port passed through a separate worker on the hub checkout. JSON error handling is deliberately stricter, so full semantic parity is not claimed. See `validation/hub-canary.json`.
- GitHub workflow files: unchanged.
- Production migration: not started.

## Local hub census and canary update — 2026-11-02

A checkout scan enumerated all 53 current hub workflow files and pinned each SHA-256. The scanner marked 7 read-only candidates, 27 requiring approval/review, and 19 restricted business workflows. These are static triage results, not proof that any workflow is safe to execute. The complete per-file inventory is in `validation/hub-inventory.json`; it does not extend the account-wide coverage claim.

The native structure canary validates required files and JSON and reports inventory declarations. It verifies the workflow source hash both at queue submission and before execution. It does not install dependencies, start services, or execute upstream shell text. The default plan command writes nothing. Explicit local submission is available through `python -m garcar_actions.migration.workflow --submit`.


## Additional privileged workflow review

- garcar-enterprise-production revenue.yml is manual-only; its schedule is explicitly disabled. It checks the storefront, installs data-science dependencies, and runs revenue_loop.py. It is not a routine CI job and remains restricted.
- garcar-enterprise-production sales-fleet.yml is manual-only; weekday schedule is explicitly disabled. It contains a dry-run default and an approval-record gate for live email. It also references email, lead, and payment-edge integrations. Keep it disabled in Garcar Actions until approval verification, isolated secrets brokering, and no-send dry-run parity are proven.
- garcar-enterprise-production deploy.yml can trigger a Render deployment hook and poll a health endpoint. It is a production mutation and remains disabled.
- autonomous-income-deployment auto-approve-merge.yml grants contents: write and pull-requests: write and automatically approves/merges pull requests. Do not migrate or enable this unattended.
- tree-of-life-system sync-linear.yml passes multiple external service credentials to a script that may write to Linear. It requires a scoped connector and explicit write approval; never copy GitHub secrets into a general runner environment.

## Read-only scanner added

The migration scanner is available at garcar-actions/garcar_actions/migration/scan.py. It recursively inventories .github/workflows and local-actions/workflows in a checked-out repository, records each source file SHA-256, and flags secret references, deployment, commerce, outreach, repository mutation, self-healing, shell steps, and third-party actions. It does not execute workflows and deliberately does not claim semantic equivalence. Run from the garcar-actions package root:

    python -m garcar_actions.migration.scan /path/to/checkout --output migration-report.json

The scanner's classification is a triage signal, not a security proof. A human review is still required before translation or execution.
