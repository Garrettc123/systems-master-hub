#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")/.."
printf '\n== Python compile ==\n'
python -m compileall -q app tests
printf '\n== Unit tests ==\n'
python -m pytest -q
printf '\n== Shell syntax ==\n'
sh -n scripts/preflight.sh
if command -v bash >/dev/null 2>&1; then
  bash -n scripts/termux.sh
  bash -n scripts/e2e-smoke.sh
  bash -n scripts/test-termux-pid-guard.sh
  bash scripts/test-termux-pid-guard.sh
fi
if command -v ruff >/dev/null 2>&1; then
  printf '\n== Ruff ==\n'
  ruff check app tests
else
  echo 'SKIP: Ruff not installed; install the dev extra for lint checks.'
fi
printf '\n== Package build ==\n'
rm -rf build dist ./*.egg-info
python -m pip wheel --no-deps --no-build-isolation . -w dist
printf '\n== Compose validation ==\n'
if command -v docker >/dev/null 2>&1; then
  docker compose config --quiet
  echo 'Docker Compose config valid.'
else
  echo 'SKIP: Docker unavailable; container image/runtime was not built.'
fi
printf '\nLOCAL SOFTWARE CHECKS PASSED. Review Docker skip status separately.\n'
