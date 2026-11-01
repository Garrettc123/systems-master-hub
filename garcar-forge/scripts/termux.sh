#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
ACTION="${1:-status}"
VENV="$PWD/.venv"
PIDDIR="$PWD/.run"
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
  echo "Install complete. Operator token saved in .env with owner-only permissions."
}
start_one() {
  name="$1"; shift
  pidfile="$PIDDIR/$name.pid"
  if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then
    echo "$name already running (pid $(cat "$pidfile"))"; return
  fi
  nohup "$@" >> "$PWD/data/$name.log" 2>&1 < /dev/null &
  echo $! > "$pidfile"
  echo "started $name (pid $!)"
}
case "$ACTION" in
  install) install_deps ;;
  start)
    [ -x "$VENV/bin/uvicorn" ] || { echo "Run: $0 install" >&2; exit 1; }
    set -a; [ ! -f .env ] || . ./.env; set +a
    export GARCAR_LEDGER_PATH="${GARCAR_LEDGER_PATH:-$PWD/data/garcar-forge.sqlite3}"
    start_one api "$VENV/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8080 --workers 1
    start_one worker "$VENV/bin/python" -m app.worker
    start_one scheduler "$VENV/bin/python" -m app.scheduler
    ;;
  stop)
    for name in scheduler worker api; do
      pidfile="$PIDDIR/$name.pid"
      if [ -f "$pidfile" ]; then
        pid="$(cat "$pidfile")"
        kill "$pid" 2>/dev/null || true
        rm -f "$pidfile"
        echo "stopped $name"
      fi
    done
    ;;
  status)
    for name in api worker scheduler; do
      pidfile="$PIDDIR/$name.pid"
      if [ -f "$pidfile" ] && kill -0 "$(cat "$pidfile")" 2>/dev/null; then echo "$name: running (pid $(cat "$pidfile"))"; else echo "$name: stopped"; fi
    done
    ;;
  logs)
    for name in api worker scheduler; do [ ! -f "$PWD/data/$name.log" ] || { echo "--- $name ---"; tail -n 30 "$PWD/data/$name.log"; }; done
    ;;
  *) echo "Usage: $0 {install|start|stop|status|logs}" >&2; exit 2 ;;
esac
