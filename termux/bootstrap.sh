#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# Pixel 10 Edge Node — Termux Bootstrap
#
# Idempotent setup script: installs prerequisites, configures SSH, sets up
# the directory layout for an autonomous edge node. Safe to re-run.
#
# Usage (on-device):  bash bootstrap.sh
# Usage (remote):     ssh user@pixel 'bash -s' < bootstrap.sh
###############################################################################
set -euo pipefail

# --- Colours (safe for dumb terminals) ---
if [ -t 1 ]; then
  R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m' N='\033[0m'
else
  R='' G='' Y='' B='' N=''
fi

info()    { printf "${B}[INFO]${N}  %s\n" "$*"; }
ok()      { printf "${G}[OK]${N}    %s\n" "$*"; }
warn()    { printf "${Y}[WARN]${N}  %s\n" "$*"; }
fail()    { printf "${R}[FAIL]${N}  %s\n" "$*"; exit 1; }

EDGE_HOME="${HOME}/edge-node"
EDGE_LOG="${EDGE_HOME}/logs"

###############################################################################
# 1. Package prerequisites
###############################################################################
info "Step 1/6 — Installing prerequisite packages"

# Accept all repository updates non-interactively
pkg update -y 2>/dev/null || true

# Core packages — small footprint, all useful for an autonomous edge node
PACKAGES=(
  openssh          # sshd for remote access
  termux-api       # battery, vibrate, notification, sensor access
  android-tools    # adb (for self-ADB and on-device UI automation prep)
  python           # scripting, automation, lightweight ML
  git              # repo sync
  curl             # HTTP requests
  jq               # JSON parsing (health checks, API responses)
  wget             # file downloads
  openssl          # TLS, cert generation
  net-tools        # ifconfig, netstat
  iproute2         # ip command
  procps           # ps, top, free
  coreutils        # standard GNU utils
  tar              # archive handling
  cronie           # cron daemon for scheduled tasks
  nano             # lightweight editor (for on-device quick edits)
)

installed=0
for pkg_name in "${PACKAGES[@]}"; do
  if dpkg -s "$pkg_name" >/dev/null 2>&1; then
    continue
  fi
  info "  Installing $pkg_name ..."
  if pkg install -y "$pkg_name" 2>/dev/null; then
    ((installed++))
  else
    warn "  Could not install $pkg_name — continuing"
  fi
done

if [ "$installed" -gt 0 ]; then
  ok "Installed $installed new packages"
else
  ok "All packages already present"
fi

###############################################################################
# 2. Directory layout
###############################################################################
info "Step 2/6 — Creating edge-node directory layout"

mkdir -p "$EDGE_HOME"/{logs,data,scripts,config}
mkdir -p ~/.termux/boot

ok "Directories ready: $EDGE_HOME"

###############################################################################
# 3. SSH server configuration
###############################################################################
info "Step 3/6 — Configuring SSH server"

mkdir -p ~/.ssh
chmod 700 ~/.ssh

# Generate host keys if missing (Termux sshd needs them)
if [ ! -f "$PREFIX/etc/ssh/ssh_host_ed25519_key" ]; then
  ssh-keygen -t ed25519 -f "$PREFIX/etc/ssh/ssh_host_ed25519_key" -N '' >/dev/null 2>&1
  info "  Generated ed25519 host key"
fi
if [ ! -f "$PREFIX/etc/ssh/ssh_host_rsa_key" ]; then
  ssh-keygen -t rsa -b 2048 -f "$PREFIX/etc/ssh/ssh_host_rsa_key" -N '' >/dev/null 2>&1
  info "  Generated RSA host key"
fi

# Generate a user keypair for GitHub Actions / remote access
if [ ! -f ~/.ssh/pixel10_edge ]; then
  ssh-keygen -t ed25519 -f ~/.ssh/pixel10_edge -N '' -C "pixel10-edge-$(date +%Y%m%d)" >/dev/null 2>&1
  ok "  Generated user keypair: ~/.ssh/pixel10_edge"
else
  ok "  User keypair already exists"
fi

# Ensure the public key is in authorized_keys
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
if ! grep -qF "$(cat ~/.ssh/pixel10_edge.pub)" ~/.ssh/authorized_keys 2>/dev/null; then
  cat ~/.ssh/pixel10_edge.pub >> ~/.ssh/authorized_keys
  info "  Added public key to authorized_keys"
fi

# Start sshd if not running
if ! pgrep -x sshd >/dev/null 2>&1; then
  sshd
  sleep 1
  if pgrep -x sshd >/dev/null 2>&1; then
    ok "  sshd started (port 8022)"
  else
    warn "  sshd failed to start — check $PREFIX/etc/ssh/sshd_config"
  fi
else
  ok "  sshd already running"
fi

###############################################################################
# 4. Storage check
###############################################################################
info "Step 4/6 — Checking storage"

FREE_KB=$(df /data 2>/dev/null | tail -1 | awk '{print $4}')
FREE_GB=$(( ${FREE_KB:-0} / 1048576 ))

if [ "$FREE_GB" -lt 3 ]; then
  warn "Low storage: ${FREE_GB}GB free. LLM models need 3-5 GB."
else
  ok "Storage OK: ${FREE_GB}GB free"
fi

###############################################################################
# 5. Network info
###############################################################################
info "Step 5/6 — Detecting network"

DEVICE_IP=""
# Try wlan0, then any non-loopback
for iface in wlan0 wlan1 rmnet_data0; do
  DEVICE_IP=$(ip -4 addr show "$iface" 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1 || true)
  [ -n "$DEVICE_IP" ] && break
done
if [ -z "$DEVICE_IP" ]; then
  DEVICE_IP=$(ip -4 route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\d+(\.\d+){3}' || echo "unknown")
fi

ok "Device IP: $DEVICE_IP"

###############################################################################
# 6. Write node identity file
###############################################################################
info "Step 6/6 — Writing node identity"

cat > "$EDGE_HOME/config/node-identity.json" <<IDENTITY
{
  "node_type": "pixel10-edge",
  "hostname": "$(hostname 2>/dev/null || echo pixel10)",
  "user": "$(whoami)",
  "arch": "$(uname -m)",
  "ip": "$DEVICE_IP",
  "ssh_port": 8022,
  "bootstrap_date": "$(date -Iseconds)",
  "edge_home": "$EDGE_HOME"
}
IDENTITY

ok "Node identity written to $EDGE_HOME/config/node-identity.json"

###############################################################################
# Done
###############################################################################
echo ""
echo "============================================"
echo "  Pixel 10 Edge Node — Bootstrap Complete"
echo "============================================"
echo ""
echo "  IP:        $DEVICE_IP"
echo "  SSH port:  8022"
echo "  User:      $(whoami)"
echo "  Edge home: $EDGE_HOME"
echo ""
echo "  Public key (add to GitHub Secrets as PIXEL10_SSH_KEY):"
echo "  $(cat ~/.ssh/pixel10_edge.pub)"
echo ""
echo "  Next steps:"
echo "    1. Copy the PRIVATE key (~/.ssh/pixel10_edge) to GitHub Secrets"
echo "    2. Install Termux:Boot from F-Droid for auto-start"
echo "    3. Run: bash ~/boot-init.sh  (installs boot persistence)"
echo "    4. Run: bash ~/watchdog.sh   (one-shot health check)"
echo ""
