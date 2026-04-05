#!/data/data/com.termux/files/usr/bin/bash
###############################################################################
# Pixel 10 Edge Node — Self-ADB Setup Helper
#
# Enables ADB-over-TCP on the device itself so that Termux can issue adb
# commands locally (e.g. input tap, input swipe, screencap, etc.) for
# UI automation without a USB-connected host.
#
# PREREQUISITES:
#   1. Developer Options enabled (Settings > About Phone > tap Build Number 7x)
#   2. USB Debugging enabled (Settings > Developer Options)
#   3. Wireless Debugging enabled AND paired at least once
#      (Settings > Developer Options > Wireless Debugging)
#   4. android-tools installed in Termux: pkg install android-tools
#
# HOW IT WORKS:
#   Android 11+ supports wireless debugging. Once paired, Termux can connect
#   to the local ADB daemon over TCP (127.0.0.1) and issue commands.
#
# SECURITY NOTE:
#   Self-ADB only exposes ADB on localhost. It does NOT open ADB to the
#   network. The pairing code is a one-time auth step.
#
# Usage:  bash self-adb-setup.sh
###############################################################################
set -euo pipefail

R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m' N='\033[0m'
info()  { printf "${B}[INFO]${N}  %s\n" "$*"; }
ok()    { printf "${G}[OK]${N}    %s\n" "$*"; }
warn()  { printf "${Y}[WARN]${N}  %s\n" "$*"; }
fail()  { printf "${R}[FAIL]${N}  %s\n" "$*"; exit 1; }

###############################################################################
# Check prerequisites
###############################################################################
info "Checking prerequisites..."

if ! command -v adb >/dev/null 2>&1; then
  info "Installing android-tools..."
  pkg install -y android-tools 2>/dev/null || fail "Cannot install android-tools"
fi

ok "adb available: $(adb --version 2>/dev/null | head -1)"

###############################################################################
# Guide the user through wireless debugging pairing
###############################################################################
echo ""
echo "================================================================"
echo "  Self-ADB Setup for Pixel 10"
echo "================================================================"
echo ""
echo "This script helps you pair Termux with on-device ADB so you can"
echo "run adb commands locally (screencap, input, etc.)."
echo ""
echo "STEP 1: Open Android Settings"
echo "  Settings > Developer Options > Wireless Debugging"
echo "  Make sure Wireless Debugging is ON."
echo ""
echo "STEP 2: Tap 'Pair device with pairing code'"
echo "  You will see:"
echo "    - A 6-digit pairing code"
echo "    - An IP:Port like 127.0.0.1:XXXXX"
echo ""

# Check if already connected
if adb devices 2>/dev/null | grep -q "device$"; then
  ok "ADB already connected!"
  adb devices
  echo ""
  echo "You can test with:  adb shell wm size"
  exit 0
fi

read -rp "Enter the pairing port (from Wireless Debugging screen): " PAIR_PORT
read -rp "Enter the 6-digit pairing code: " PAIR_CODE

if [ -z "$PAIR_PORT" ] || [ -z "$PAIR_CODE" ]; then
  fail "Port and code are required"
fi

info "Pairing with ADB on 127.0.0.1:${PAIR_PORT}..."

# adb pair requires the code on stdin or as an argument
adb pair "127.0.0.1:${PAIR_PORT}" "$PAIR_CODE" 2>&1 || {
  warn "Pairing failed. Make sure:"
  warn "  - Wireless Debugging is ON"
  warn "  - The pairing code hasn't expired (get a new one)"
  warn "  - The port is correct"
  exit 1
}

ok "Pairing successful!"

###############################################################################
# Connect to the local ADB daemon
###############################################################################
echo ""
echo "STEP 3: Now we connect to the running ADB daemon."
echo "  Look at the Wireless Debugging screen for the main port"
echo "  (NOT the pairing port — it's the one shown at the top)."
echo ""

read -rp "Enter the ADB connection port (shown under Wireless Debugging): " CONNECT_PORT

if [ -z "$CONNECT_PORT" ]; then
  fail "Connection port is required"
fi

info "Connecting to 127.0.0.1:${CONNECT_PORT}..."
adb connect "127.0.0.1:${CONNECT_PORT}" 2>&1

if adb devices 2>/dev/null | grep -q "device$"; then
  ok "ADB connected!"
  echo ""
  echo "Connected devices:"
  adb devices
  echo ""
  echo "Test commands:"
  echo "  adb shell wm size          # screen resolution"
  echo "  adb shell dumpsys battery   # battery info"
  echo "  adb shell input tap 500 500 # tap screen at (500,500)"
  echo "  adb shell screencap -p /sdcard/screen.png  # screenshot"
  echo ""

  # Save connection info for boot-init
  mkdir -p "${HOME}/edge-node/config"
  echo "$CONNECT_PORT" > "${HOME}/edge-node/config/adb-port"
  ok "ADB port saved to ~/edge-node/config/adb-port"
  echo ""
  echo "NOTE: After reboot, you'll need to re-enable Wireless Debugging"
  echo "and re-pair. Android requires this for security."
else
  warn "Connection may not have worked. Check 'adb devices'."
fi
