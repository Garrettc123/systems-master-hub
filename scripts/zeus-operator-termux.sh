#!/data/data/com.termux/files/usr/bin/bash
# ZEUS Termux operator: repository inventory, local health, logs, and explicit service controls.
# Safe defaults: status/inventory only. Never deploys or starts arbitrary repositories automatically.
set -Eeuo pipefail
umask 077
ROOT="${ZEUS_REPOS_DIR:-$HOME/ZEUS/repos}"
STATE="$HOME/ZEUS"
LOGS="$STATE/logs"
PIDS="$STATE/pids"
mkdir -p "$LOGS" "$PIDS"
cmd="${1:-status}"
case "$cmd" in
  status)
    echo "ZEUS local status — $(date -Iseconds)"
    echo "Repository root: $ROOT"
    echo "Disk:"
    df -h "$HOME" 2>/dev/null || true
    echo
    if [[ ! -d "$ROOT" ]]; then echo "No repository directory yet. Run the sync script first."; exit 0; fi
    printf "%-36s %-12s %s\n" "REPOSITORY" "GIT" "LOCAL CHANGES"
    for d in "$ROOT"/*; do
      [[ -d "$d/.git" ]] || continue
      name="${d##*/}"
      branch="$(git -C "$d" branch --show-current 2>/dev/null || echo unknown)"
      changes="$(git -C "$d" status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
      printf "%-36s %-12s %s\n" "$name" "$branch" "$changes"
    done
    echo
    echo "Managed process records:"
    found=0
    for f in "$PIDS"/*.pid; do
      [[ -f "$f" ]] || continue
      found=1; pid="$(cat "$f" 2>/dev/null || true)"; name="${f##*/}"; name="${name%.pid}"
      if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then echo "$name RUNNING pid=$pid"; else echo "$name STOPPED (stale PID file)"; fi
    done
    [[ "$found" -eq 1 ]] || echo "No ZEUS-managed services registered."
    ;;
  logs)
    name="${2:-}"
    [[ -n "$name" ]] || { echo "Usage: $0 logs REPOSITORY_NAME"; exit 2; }
    file="$LOGS/$name.log"
    [[ -f "$file" ]] || { echo "No log found: $file"; exit 1; }
    tail -n 100 "$file"
    ;;
  stop)
    name="${2:-}"
    [[ -n "$name" ]] || { echo "Usage: $0 stop REPOSITORY_NAME"; exit 2; }
    file="$PIDS/$name.pid"
    [[ -f "$file" ]] || { echo "No ZEUS-managed PID file for $name"; exit 1; }
    pid="$(cat "$file")"
    [[ "$pid" =~ ^[0-9]+$ ]] || { echo "Invalid PID record"; exit 1; }
    if kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid"
      echo "TERM signal sent to $name (pid $pid). Verify shutdown with status."
    else echo "$name is not running."; fi
    ;;
  doctor)
    echo "ZEUS environment check"
    for tool in git curl python; do command -v "$tool" >/dev/null && echo "OK $tool" || echo "MISSING $tool"; done
    python --version 2>&1 || true
    git --version 2>&1 || true
    curl --version 2>&1 | head -n 1 || true
    echo "Free storage:"
    df -h "$HOME" 2>/dev/null || true
    echo "Repo directory: $ROOT"
    [[ -d "$ROOT" ]] || echo "NOTE: run the repository sync script first."
    ;;
  *)
    echo "ZEUS Termux operator"
    echo "Usage: $0 {status|doctor|logs REPOSITORY_NAME|stop REPOSITORY_NAME}"
    exit 2
    ;;
esac
