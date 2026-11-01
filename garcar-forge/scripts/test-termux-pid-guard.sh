#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TEST_PID_DIR="$(mktemp -d)"
foreign_pid=""
owned_pid=""
legacy_pid=""

cleanup() {
  [ -z "$foreign_pid" ] || kill "$foreign_pid" 2>/dev/null || true
  [ -z "$owned_pid" ] || kill "$owned_pid" 2>/dev/null || true
  [ -z "$legacy_pid" ] || kill "$legacy_pid" 2>/dev/null || true
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

GARCAR_LEDGER_PATH="$PWD/data/garcar-forge.sqlite3" bash -c 'exec -a "$1 -m app.worker" sleep 30' _ "$VENV/bin/python" &
legacy_pid=$!
matched=0
for _ in $(seq 1 20); do
  if legacy_process_matches worker "$legacy_pid"; then matched=1; break; fi
  sleep 0.05
done
[ "$matched" -eq 1 ]
printf '%s\n' "$legacy_pid" > "$PIDDIR/worker.pid"
start_one worker sleep 30
new_pid="$(cat "$PIDDIR/worker.pid")"
[ "$new_pid" != "$legacy_pid" ]
process_matches worker "$new_pid"
wait "$legacy_pid" 2>/dev/null || true
! kill -0 "$legacy_pid" 2>/dev/null
stop_one worker
wait "$new_pid" 2>/dev/null || true
! kill -0 "$new_pid" 2>/dev/null
[ ! -f "$PIDDIR/worker.pid" ]

echo "PASS: foreign PID preserved; current process verified; legacy process upgraded safely."
