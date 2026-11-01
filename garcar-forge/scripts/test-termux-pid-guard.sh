#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEST_PID_DIR="$(mktemp -d)"
foreign_pid=""
owned_pid=""

cleanup() {
  [ -z "$foreign_pid" ] || kill "$foreign_pid" 2>/dev/null || true
  [ -z "$owned_pid" ] || kill "$owned_pid" 2>/dev/null || true
  rm -rf "$TEST_PID_DIR"
}
trap cleanup EXIT

export GARCAR_FORGE_PIDDIR="$TEST_PID_DIR"
export GARCAR_TERMUX_LIBRARY_ONLY=true
source "$REPO_ROOT/scripts/termux.sh"
unset GARCAR_TERMUX_LIBRARY_ONLY

sleep 30 &
foreign_pid=$!
printf '%s\n' "$foreign_pid" > "$PIDDIR/api.pid"
stop_one api
kill -0 "$foreign_pid" 2>/dev/null
[ ! -f "$PIDDIR/api.pid" ]

GARCAR_FORGE_PROCESS=worker GARCAR_FORGE_HOME="$PWD" sleep 30 &
owned_pid=$!
matched=0
for _ in $(seq 1 20); do
  if process_matches worker "$owned_pid"; then matched=1; break; fi
  sleep 0.05
done
[ "$matched" -eq 1 ]
printf '%s\n' "$owned_pid" > "$PIDDIR/worker.pid"
stop_one worker
wait "$owned_pid" 2>/dev/null || true
! kill -0 "$owned_pid" 2>/dev/null
[ ! -f "$PIDDIR/worker.pid" ]

echo "PASS: foreign PID was not signalled; owned Forge process was stopped."
