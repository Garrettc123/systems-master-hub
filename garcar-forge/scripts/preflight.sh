#!/usr/bin/env sh
set -eu
fail() { printf 'BLOCKED: %s\n' "$1" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || fail "Docker CLI is not installed."
docker info >/dev/null 2>&1 || fail "Docker Engine is unavailable or current user lacks access."
docker compose version >/dev/null 2>&1 || fail "Docker Compose plugin is unavailable."
[ -f .env ] || fail "Missing .env. Copy .env.example and set a unique operator token."
token=$(sed -n 's/^GARCAR_OPERATOR_TOKEN=//p' .env | tail -n 1)
[ "${#token}" -ge 32 ] || fail "GARCAR_OPERATOR_TOKEN must be at least 32 characters."
[ "$token" != "REPLACE_WITH_A_64_CHARACTER_RANDOM_SECRET" ] || fail "Operator token is still a placeholder."
docker compose config --quiet || fail "Docker Compose configuration is invalid."
printf 'PREFLIGHT PASSED. No containers were started, stopped, or changed.\n'
