#!/usr/bin/env sh
set -eu

fail() {
  printf 'BLOCKED: %s\n' "$1" >&2
  exit 1
}

command -v docker >/dev/null 2>&1 || fail "Docker CLI is not installed."
docker info >/dev/null 2>&1 || fail "Docker Engine is unavailable or the current user lacks access."
docker compose version >/dev/null 2>&1 || fail "Docker Compose plugin is unavailable."

[ -f .env ] || fail "Missing .env. Copy .env.example to .env and set a unique operator token."

if grep -Eq '^GARCAR_OPERATOR_TOKEN=(REPLACE_WITH_A_LONG_RANDOM_SECRET)?$' .env; then
  fail "GARCAR_OPERATOR_TOKEN is still a placeholder or empty."
fi

if ! grep -q '^GARCAR_OPERATOR_TOKEN=.' .env; then
  fail "GARCAR_OPERATOR_TOKEN is not configured."
fi

docker compose config --quiet || fail "Docker Compose configuration is invalid."

printf 'PREFLIGHT PASSED: Docker, Compose, operator-token presence, and Compose configuration verified.\n'
printf 'No containers were started, stopped, or changed.\n'
