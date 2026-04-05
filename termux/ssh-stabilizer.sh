#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PORT="8022"
BOOT_DIR="$HOME/.termux/boot"
BOOT_SCRIPT="$BOOT_DIR/00-start-edge-node.sh"
LOG_DIR="$HOME/edge-node/logs"
STATUS_FILE="$HOME/edge-node/ssh-status.json"

mkdir -p "$LOG_DIR" "$BOOT_DIR" "$HOME/edge-node"

log() {
  printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1"
}

install_if_missing() {
  local pkg_name="$1"
  if ! command -v "$pkg_name" >/dev/null 2>&1; then
    yes | pkg install "$pkg_name" >/dev/null 2>&1 || pkg install -y "$pkg_name" >/dev/null 2>&1 || true
  fi
}

log "Preparing Termux edge environment"
install_if_missing openssh
install_if_missing termux-api
install_if_missing jq
install_if_missing procps
install_if_missing net-tools

termux-wake-lock || true

if pgrep -f sshd >/dev/null 2>&1; then
  pkill -f sshd || true
  sleep 1
fi

sshd
sleep 2

IP="$(ip addr show 2>/dev/null | awk '/inet / && $2 !~ /^127\./ {print $2}' | cut -d/ -f1 | head -n1)"
USER_NAME="$(whoami)"
UPTIME="$(uptime 2>/dev/null | sed 's/^ *//')"
BATTERY="$(termux-battery-status 2>/dev/null || echo '{}')"
WIFI="$(termux-wifi-connectioninfo 2>/dev/null || echo '{}')"

cat > "$STATUS_FILE" <<EOF
{
  "timestamp": "$(date -Iseconds)",
  "user": "$USER_NAME",
  "port": "$PORT",
  "ip": "$IP",
  "uptime": $(printf '%s' "$UPTIME" | jq -Rs .),
  "battery": $BATTERY,
  "wifi": $WIFI,
  "sshd_running": true
}
EOF

cat > "$BOOT_SCRIPT" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
termux-wake-lock || true
pgrep -f sshd >/dev/null 2>&1 || sshd
EOF
chmod +x "$BOOT_SCRIPT"

termux-notification \
  --id 4242 \
  --title "Pixel 10 SSH Ready" \
  --content "User: $USER_NAME | IP: $IP | Port: $PORT" \
  --priority high >/dev/null 2>&1 || true

log "SSH is running"
log "User: $USER_NAME"
log "IP: ${IP:-unknown}"
log "Port: $PORT"
log "Boot script installed: $BOOT_SCRIPT"
log "Status file: $STATUS_FILE"

echo
echo "Run this to verify immediately:"
echo "  ss -tlnp | grep 8022 || netstat -tln 2>/dev/null | grep 8022"
echo
echo "Then send this exact message back:"
echo "  sshd running"
