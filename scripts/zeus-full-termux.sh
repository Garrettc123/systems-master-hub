#!/data/data/com.termux/files/usr/bin/bash
# ZEUS Full Termux Operator for Garcar Enterprise
# Safe by default: sync/status/doctor do not start services or deploy infrastructure.
# Services run only after explicit registration with a command you choose.
set -Eeuo pipefail
umask 077

OWNER="Garrettc123"
STATE="${ZEUS_HOME:-$HOME/ZEUS}"
ROOT="${ZEUS_REPOS_DIR:-$STATE/repos}"
SCRIPTS="$STATE/scripts"
LOGS="$STATE/logs"
PIDS="$STATE/pids"
CONFIG="$STATE/services"
SYNC_SCRIPT="$SCRIPTS/zeus-sync-termux.sh"
SELF_URL="https://raw.githubusercontent.com/$OWNER/systems-master-hub/main/scripts/zeus-full-termux.sh"
SYNC_URL="https://raw.githubusercontent.com/$OWNER/systems-master-hub/main/scripts/zeus-sync-termux.sh"

mkdir -p "$STATE" "$SCRIPTS" "$LOGS" "$PIDS" "$CONFIG"
chmod 700 "$STATE" "$LOGS" "$PIDS" "$CONFIG"

log() { printf '[%s] %s\n' "$(date -Iseconds 2>/dev/null || date)" "$*"; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1"; return 1; }; }
valid_name() { [[ "${1:-}" =~ ^[A-Za-z0-9._-]+$ ]]; }
service_config() { printf '%s/%s.json' "$CONFIG" "$1"; }
pid_file() { printf '%s/%s.pid' "$PIDS" "$1"; }
log_file() { printf '%s/%s.log' "$LOGS" "$1"; }

install_scripts() {
  need curl
  curl -fsSL "$SYNC_URL" -o "$SYNC_SCRIPT"
  curl -fsSL "$SELF_URL" -o "$SCRIPTS/zeus-full-termux.sh"
  chmod 700 "$SYNC_SCRIPT" "$SCRIPTS/zeus-full-termux.sh"
  log "Downloaded current ZEUS sync and operator scripts."
}

doctor() {
  echo "=== ZEUS environment diagnostics ==="
  echo "Time: $(date -Iseconds 2>/dev/null || date)"
  echo "Android/Termux: ${PREFIX:-not detected}"
  echo "Home: $HOME"
  echo "Repo root: $ROOT"
  echo
  for c in bash git curl python; do
    if command -v "$c" >/dev/null 2>&1; then printf 'OK      %-10s %s\n' "$c" "$(command -v "$c")"; else printf 'MISSING %-10s\n' "$c"; fi
  done
  python --version 2>&1 || true
  git --version 2>&1 || true
  curl --version 2>&1 | head -n 1 || true
  echo
  df -h "$HOME" 2>/dev/null || true
  echo
  if [[ -n "${GH_PAT:-}${GITHUB_TOKEN:-}" ]]; then
    echo "GitHub token: present in environment (value hidden)"
  else
    echo "GitHub token: not present; sync will be public-repositories-only"
  fi
  echo "Note: secret presence does not prove token validity."
}

sync_repos() {
  need git; need curl; need python
  if [[ ! -x "$SYNC_SCRIPT" ]]; then
    log "Installing the repository sync helper."
    curl -fsSL "$SYNC_URL" -o "$SYNC_SCRIPT"
    chmod 700 "$SYNC_SCRIPT"
  fi
  ZEUS_REPOS_DIR="$ROOT" bash "$SYNC_SCRIPT"
}

inventory() {
  echo "=== ZEUS repository inventory ==="
  echo "Root: $ROOT"
  if [[ ! -d "$ROOT" ]]; then echo "No repositories yet. Run: $0 sync"; return 0; fi
  printf '%-38s %-16s %-10s %s\n' "REPOSITORY" "BRANCH" "CHANGES" "CONFIG"
  for d in "$ROOT"/*; do
    [[ -d "$d/.git" ]] || continue
    name="${d##*/}"
    branch="$(git -C "$d" branch --show-current 2>/dev/null || echo unknown)"
    changes="$(git -C "$d" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
    cfg="$(service_config "$name")"
    [[ -f "$cfg" ]] && configured=yes || configured=no
    printf '%-38s %-16s %-10s %s\n' "$name" "$branch" "$changes" "$configured"
  done
}

status() {
  inventory
  echo
  echo "=== ZEUS managed processes ==="
  found=0
  for f in "$PIDS"/*.pid; do
    [[ -f "$f" ]] || continue
    found=1
    name="${f##*/}"; name="${name%.pid}"
    pid="$(cat "$f" 2>/dev/null || true)"
    if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
      printf 'RUNNING %-30s pid=%s\n' "$name" "$pid"
    else
      printf 'STOPPED %-30s stale-pid-record\n' "$name"
    fi
  done
  [[ "$found" -eq 1 ]] || echo "No managed services registered as running."
  echo
  echo "Commands: doctor | sync | status | register REPO | start REPO | stop REPO | restart REPO | logs REPO | health REPO | list"
}

register_service() {
  local name="${1:-}"
  valid_name "$name" || { echo "Usage: $0 register REPOSITORY_NAME (letters, digits, dot, underscore, hyphen only)"; return 2; }
  local dir="$ROOT/$name"
  [[ -d "$dir/.git" ]] || { echo "Repository not found at $dir. Run sync first."; return 1; }
  local cfg; cfg="$(service_config "$name")"
  [[ ! -e "$cfg" ]] || { echo "Service already registered: $cfg. Edit it deliberately or remove it first."; return 1; }
  echo "Registering $name. This does not install dependencies or start the service."
  echo "Working directory: $dir"
  local command health
  read -r -p "Exact start command for this repository (required): " command
  [[ -n "$command" ]] || { echo "Start command cannot be empty."; return 2; }
  read -r -p "Optional health URL (blank to skip): " health
  REPO_NAME="$name" REPO_DIR="$dir" START_COMMAND="$command" HEALTH_URL="$health" CONFIG_PATH="$cfg" python - <<'PY'
import json, os
obj = {
  "name": os.environ["REPO_NAME"],
  "working_directory": os.environ["REPO_DIR"],
  "start_command": os.environ["START_COMMAND"],
  "health_url": os.environ["HEALTH_URL"],
  "created_by": "zeus-full-termux"
}
with open(os.environ["CONFIG_PATH"], "w", encoding="utf-8") as f:
    json.dump(obj, f, indent=2)
    f.write("\n")
PY
  chmod 600 "$cfg"
  echo "Registered $name. Review config: $cfg"
  echo "Only run start after confirming the command and its dependencies are correct."
}

read_config() {
  local name="$1" field="$2" cfg
  cfg="$(service_config "$name")"
  [[ -f "$cfg" ]] || { echo "Service not registered: $name. Run: $0 register $name" >&2; return 1; }
  CONFIG_PATH="$cfg" FIELD="$field" python - <<'PY'
import json, os, sys
try:
    with open(os.environ["CONFIG_PATH"], encoding="utf-8") as f: d=json.load(f)
    v=d.get(os.environ["FIELD"], "")
    if not isinstance(v, str): raise ValueError("field must be a string")
    print(v)
except Exception as e:
    print("Invalid service configuration: "+str(e), file=sys.stderr)
    sys.exit(1)
PY
}

start_service() {
  local name="${1:-}"
  valid_name "$name" || { echo "Usage: $0 start REPOSITORY_NAME"; return 2; }
  local cfg dir command pidfile outfile
  cfg="$(service_config "$name")"
  [[ -f "$cfg" ]] || { echo "Service not registered. Run: $0 register $name"; return 1; }
  dir="$(read_config "$name" working_directory)"
  command="$(read_config "$name" start_command)"
  [[ -d "$dir" ]] || { echo "Configured working directory missing: $dir"; return 1; }
  [[ -n "$command" ]] || { echo "Empty start command; refusing to run."; return 1; }
  pidfile="$(pid_file "$name")"; outfile="$(log_file "$name")"
  if [[ -f "$pidfile" ]]; then
    pid="$(cat "$pidfile" 2>/dev/null || true)"
    if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then echo "$name already running (pid $pid)."; return 0; fi
    rm -f "$pidfile"
  fi
  echo "About to execute the explicitly registered command for $name:"
  printf '  %s\n' "$command"
  echo "Directory: $dir"
  read -r -p "Start this process? Type YES to confirm: " confirm
  [[ "$confirm" == "YES" ]] || { echo "Cancelled."; return 0; }
  (
    cd "$dir"
    nohup bash -lc "$command" >>"$outfile" 2>&1 &
    echo $! > "$pidfile"
  )
  chmod 600 "$pidfile" "$outfile" 2>/dev/null || true
  sleep 2
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    log "Started $name (pid $pid); logs: $outfile"
  else
    rm -f "$pidfile"
    echo "Process exited quickly. Recent log output:"
    tail -n 60 "$outfile" 2>/dev/null || true
    return 1
  fi
}

stop_service() {
  local name="${1:-}" pidfile pid
  valid_name "$name" || { echo "Usage: $0 stop REPOSITORY_NAME"; return 2; }
  pidfile="$(pid_file "$name")"
  [[ -f "$pidfile" ]] || { echo "No managed PID file for $name."; return 1; }
  pid="$(cat "$pidfile" 2>/dev/null || true)"
  [[ "$pid" =~ ^[0-9]+$ ]] || { echo "Invalid PID record; removing stale record."; rm -f "$pidfile"; return 1; }
  if kill -0 "$pid" 2>/dev/null; then
    kill -TERM "$pid"
    for _ in 1 2 3 4 5; do
      sleep 1
      if ! kill -0 "$pid" 2>/dev/null; then rm -f "$pidfile"; log "Stopped $name."; return 0; fi
    done
    echo "TERM sent to PID $pid; it has not exited yet. No force-kill was sent."
    return 1
  fi
  rm -f "$pidfile"
  echo "$name was not running; stale record removed."
}

health_check() {
  local name="${1:-}" url
  valid_name "$name" || { echo "Usage: $0 health REPOSITORY_NAME"; return 2; }
  url="$(read_config "$name" health_url)"
  if [[ -z "$url" ]]; then echo "No health URL configured for $name."; return 2; fi
  [[ "$url" == http://* || "$url" == https://* ]] || { echo "Refusing non-HTTP health URL."; return 2; }
  need curl
  if curl --fail --silent --show-error --max-time 8 "$url" >/dev/null; then
    echo "HEALTHY $name — $url"; return 0
  else
    echo "UNHEALTHY $name — $url"; return 1
  fi
}

logs() {
  local name="${1:-}" file
  valid_name "$name" || { echo "Usage: $0 logs REPOSITORY_NAME"; return 2; }
  file="$(log_file "$name")"
  [[ -f "$file" ]] || { echo "No log file yet: $file"; return 1; }
  tail -n 100 "$file"
}

help_text() {
  cat <<'HELP'
ZEUS Full Termux Operator
Usage: bash zeus-full-termux.sh COMMAND [REPOSITORY]

  doctor             Check tools, storage, and token presence (never prints token)
  install            Download the latest ZEUS helper scripts
  sync               Clone/update repositories; preserves dirty local repositories
  status             Show repository inventory and managed process records
  list               Same as status
  register REPO      Explicitly register a repository's start command and optional health URL
  start REPO         Show command and require typing YES before starting
  stop REPO          Send TERM to a managed process; never force-kills
  restart REPO       Stop then explicitly confirm start
  logs REPO          Show last 100 lines of the service log
  health REPO        Check the registered HTTP(S) health URL

Important:
- No pip upgrade, mass dependency install, automatic deployment, or arbitrary repo startup.
- Use only commands you understand and trust. Registered start commands execute as your Termux user.
- A PID file tracks the launched shell/process; some applications may spawn child processes.
- For private repositories, set GH_PAT or GITHUB_TOKEN in your Termux session securely.
HELP
}

cmd="${1:-help}"
case "$cmd" in
  doctor) doctor ;;
  install) install_scripts ;;
  sync) sync_repos ;;
  status|list) status ;;
  register) register_service "${2:-}" ;;
  start) start_service "${2:-}" ;;
  stop) stop_service "${2:-}" ;;
  restart)
    name="${2:-}"
    stop_service "$name" || true
    start_service "$name"
    ;;
  logs) logs "${2:-}" ;;
  health) health_check "${2:-}" ;;
  help|-h|--help) help_text ;;
  *) echo "Unknown command: $cmd"; help_text; exit 2 ;;
esac
