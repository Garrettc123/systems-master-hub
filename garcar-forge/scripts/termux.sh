#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
ACTION="${1:-status}"
VENV="$PWD/.venv"
PIDDIR="${GARCAR_FORGE_PIDDIR:-$PWD/.run}"
mkdir -p "$PIDDIR" "$PWD/data"

install_deps() {
  command -v pkg >/dev/null 2>&1 || { echo "This install command is for Termux." >&2; exit 1; }
  pkg install -y python coreutils curl
  python -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip
  "$VENV/bin/pip" install .
  if [ ! -f .env ]; then
    "$VENV/bin/python" - <<'PY'
import secrets
from pathlib import Path
p = Path('.env')
p.write_text('GARCAR_OPERATOR_TOKEN=' + secrets.token_hex(32) + '\nGARCAR_LEDGER_PATH=' + str(Path('data/garcar-forge.sqlite3').resolve()) + '\n')
p.chmod(0o600)
PY
  fi
  chmod 600 .env
  echo "Install complete. Operator token saved in .env with owner-only permissions."
}

legacy_process_matches() {
  local name="$1" pid="$2" proc_env cmdline cwd
  [ -r "/proc/$pid/environ" ] || return 1
  [ -r "/proc/$pid/cmdline" ] || return 1
  proc_env="$(tr '\000' '\n' < "/proc/$pid/environ" 2>/dev/null || true)"
  proc_env=$'\n'"$proc_env"$'\n'
  [[ "$proc_env" != *$'\n'"GARCAR_FORGE_PROCESS="* ]] || return 1
  [[ "$proc_env" == *$'\n'"GARCAR_LEDGER_PATH=$PWD/data/garcar-forge.sqlite3"$'\n'* ]] || return 1
  cwd="$(readlink "/proc/$pid/cwd" 2>/dev/null || true)"
  [ "$cwd" = "$PWD" ] || return 1
  cmdline="$(tr '\000' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
  case "$name" in
    api) [[ "$cmdline" == *"$VENV/bin/uvicorn"* && "$cmdline" == *"app.main:app"* ]] ;;
    worker) [[ "$cmdline" == *"$VENV/bin/python"* && "$cmdline" == *"-m app.worker"* ]] ;;
    scheduler) [[ "$cmdline" == *"$VENV/bin/python"* && "$cmdline" == *"-m app.scheduler"* ]] ;;
    *) return 1 ;;
  esac
}

process_matches() {
  local name="$1" pid="$2" proc_env
  [ -r "/proc/$pid/environ" ] || return 1
  proc_env="$(tr '\000' '\n' < "/proc/$pid/environ" 2>/dev/null || true)"
  proc_env=$'\n'"$proc_env"$'\n'
  if [[ "$proc_env" == *$'\n'"GARCAR_FORGE_PROCESS=$name"$'\n'* ]] &&
     [[ "$proc_env" == *$'\n'"GARCAR_FORGE_HOME=$PWD"$'\n'* ]]; then
    return 0
  fi
  legacy_process_matches "$name" "$pid"
}

stop_one() {
  local name="$1" pidfile="$PIDDIR/$1.pid" pid
  [ -f "$pidfile" ] || return 0
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  case "$pid" in
    ''|*[!0-9]*)
      echo "$name: removing invalid PID file"
      rm -f "$pidfile"
      return 0
      ;;
  esac
  if ! kill -0 "$pid" 2>/dev/null; then
    echo "$name: process already stopped"
    rm -f "$pidfile"
    return 0
  fi
  if ! process_matches "$name" "$pid"; then
    echo "$name: refusing to signal PID $pid; process identity does not match this Forge instance" >&2
    rm -f "$pidfile"
    return 0
  fi
  kill -TERM "$pid" 2>/dev/null || true
  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null || ! process_matches "$name" "$pid"; then break; fi
    sleep 0.2
  done
  if kill -0 "$pid" 2>/dev/null && process_matches "$name" "$pid"; then
    kill -KILL "$pid" 2>/dev/null || true
  fi
  rm -f "$pidfile"
  echo "stopped $name"
}

stop_services() {
  stop_one scheduler
  stop_one worker
  stop_one api
}

start_one() {
  local name="$1" pidfile="$PIDDIR/$1.pid" existing_pid pid
  shift
  if [ -f "$pidfile" ]; then
    existing_pid="$(cat "$pidfile" 2>/dev/null || true)"
    case "$existing_pid" in
      ''|*[!0-9]*) rm -f "$pidfile" ;;
      *)
        if kill -0 "$existing_pid" 2>/dev/null && process_matches "$name" "$existing_pid"; then
          if legacy_process_matches "$name" "$existing_pid"; then
            echo "$name: replacing legacy Forge process (pid $existing_pid)"
            stop_one "$name"
          else
            echo "$name already running (verified pid $existing_pid)"
            return 0
          fi
        else
          rm -f "$pidfile"
        fi
        ;;
    esac
  fi
  GARCAR_FORGE_PROCESS="$name" GARCAR_FORGE_HOME="$PWD" nohup "$@" >> "$PWD/data/$name.log" 2>&1 < /dev/null &
  pid=$!
  printf '%s\n' "$pid" > "$pidfile"
  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo "$name failed to stay running; inspect $PWD/data/$name.log" >&2
      rm -f "$pidfile"
      return 1
    fi
    if process_matches "$name" "$pid"; then
      echo "started $name (pid $pid)"
      return 0
    fi
    sleep 0.1
  done
  echo "$name did not expose a verifiable process identity; refusing to treat it as started" >&2
  stop_one "$name"
  return 1
}

if [ "${GARCAR_TERMUX_LIBRARY_ONLY:-false}" = "true" ]; then
  return 0
fi

case "$ACTION" in
  install) install_deps ;;
  start)
    [ -x "$VENV/bin/uvicorn" ] || { echo "Run: $0 install" >&2; exit 1; }
    [ -f .env ] || { echo "Missing .env. Run: $0 install" >&2; exit 1; }
    set -a
    . ./.env
    set +a
    token="${GARCAR_OPERATOR_TOKEN:-}"
    [ "${#token}" -ge 32 ] || { echo "Operator token is missing or too short. Repair .env before starting." >&2; exit 1; }
    export GARCAR_LEDGER_PATH="${GARCAR_LEDGER_PATH:-$PWD/data/garcar-forge.sqlite3}"
    if ! start_one api "$VENV/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8080 --workers 1; then
      stop_services
      exit 1
    fi
    if ! start_one worker "$VENV/bin/python" -m app.worker; then
      stop_services
      exit 1
    fi
    if ! start_one scheduler "$VENV/bin/python" -m app.scheduler; then
      stop_services
      exit 1
    fi
    READY=0
    for _ in $(seq 1 30); do
      if curl -fsS http://127.0.0.1:8080/readyz >/dev/null 2>&1; then READY=1; break; fi
      sleep 1
    done
    if [ "$READY" -ne 1 ]; then
      echo "API failed readiness check; stopping only verified Forge processes." >&2
      stop_services
      echo "Inspect logs with: $0 logs" >&2
      exit 1
    fi
    echo "GARCAR FORGE READY: http://127.0.0.1:8080/healthz"
    ;;
  stop)
    stop_services
    ;;
  status)
    for name in api worker scheduler; do
      pidfile="$PIDDIR/$name.pid"
      if [ -f "$pidfile" ]; then
        pid="$(cat "$pidfile" 2>/dev/null || true)"
        if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null && process_matches "$name" "$pid"; then
          echo "$name: running (verified pid $pid)"
        elif [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
          echo "$name: PID $pid exists but is not verified as this Forge process; stop will not signal it"
        else
          echo "$name: stopped (stale PID file)"
        fi
      else
        echo "$name: stopped"
      fi
    done
    ;;
  logs)
    for name in api worker scheduler; do [ ! -f "$PWD/data/$name.log" ] || { echo "--- $name ---"; tail -n 30 "$PWD/data/$name.log"; }; done
    ;;
  *) echo "Usage: $0 {install|start|stop|status|logs}" >&2; exit 2 ;;
esac
