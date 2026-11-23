#!/usr/bin/env bash
# Run without GitHub Actions on Linux, Ubuntu, or Android Termux.
set -euo pipefail
BASE="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else echo 'Install Python 3.11+ first (Termux: pkg install python git)' >&2; exit 2
fi
if ! "$PY" -c 'import yaml' >/dev/null 2>&1; then
  echo 'PyYAML not found. Validate-all will fail until installed: python -m pip install PyYAML' >&2
fi
exec "$PY" "$BASE/scripts/github_ci_fallback.py" --root "$BASE" --output "$BASE/operator-evidence" "$@"