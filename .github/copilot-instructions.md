# Systems Master Hub — Copilot Instructions

## Purpose
Master coordination hub for all 89+ Garcar Enterprise repositories.
Contains architecture docs, cross-repo automation scripts, and the unified system registry.

## Standards
- Shell scripts must be POSIX-compatible (bash 4+)
- Python scripts must work on Python 3.11+
- Cross-repo operations require a PAT (`GARCAR_PAT` / `PAT_TOKEN` / `GHPAT`);
  `GITHUB_TOKEN` is scoped to this repository and cannot trigger or push elsewhere
- New repo integrations must be added to `registry/repos.json`
- All automation scripts must be idempotent (safe to re-run)

## Key Files
- `registry/repos.json` — canonical deploy registry (tiers, platform, dispatch event,
  required secrets). The deploy pipeline builds its matrix from this file
- `SYSTEM_REGISTRY.json` — descriptive inventory of all systems and their roles
- `scripts/` — cross-repo automation scripts
- `architecture/` — system design docs
- `.github/workflows/` — hub-level orchestration workflows

## PR Standards
- Shell scripts must pass `shellcheck` before merge
- Docs must be updated in `SYSTEM_REGISTRY.json` for new repos
- No hardcoded repo names — resolve them from `registry/repos.json`
- Workflows must pass `actionlint`, declare least-privilege `permissions:`, and never
  interpolate `${{ }}` values directly into `run:` bodies (bind them to `env:` instead)
