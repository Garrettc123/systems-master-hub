# Systems Master Hub — Copilot Instructions

## Purpose
Master coordination hub for all 89+ Garcar Enterprise repositories.
Contains architecture docs, cross-repo automation scripts, and the unified system registry.

## Standards
- Shell scripts must be POSIX-compatible (bash 4+)
- Python scripts must work on Python 3.11+
- All cross-repo operations use `GITHUB_TOKEN` via GitHub API
- New repo integrations must be added to `SYSTEM_REGISTRY.md`
- All automation scripts must be idempotent (safe to re-run)

## Key Files
- `SYSTEM_REGISTRY.md` — master list of all repos and their roles
- `scripts/` — cross-repo automation scripts
- `architecture/` — system design docs
- `.github/workflows/` — hub-level orchestration workflows

## PR Standards
- Shell scripts must pass `shellcheck` before merge
- Docs must be updated in `SYSTEM_REGISTRY.md` for new repos
- No hardcoded repo names — use env vars or config files
