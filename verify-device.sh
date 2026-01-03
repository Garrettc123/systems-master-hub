#!/bin/bash
# Device Verification Script
# Run this in Termux to verify prerequisites

set -e

echo ""
echo "========================================"
echo "DEVICE VERIFICATION"
echo "========================================"
echo ""

echo "1. Checking Termux user..."
USERNAME=$(whoami)
echo "   Username: $USERNAME"

echo ""
echo "2. Checking SSH status..."
if pgrep sshd > /dev/null; then
    echo "   SSH: RUNNING"
else
    echo "   SSH: NOT RUNNING (starting...)"
    sshd
fi

echo ""
echo "3. Checking SSH key..."
if [ -f ~/.ssh/pixel10_github ]; then
    echo "   Key exists: YES"
    echo "   Key type: $(head -1 ~/.ssh/pixel10_github)"
else
    echo "   Key exists: NO"
fi

echo ""
echo "4. Checking 5G connection..."
IP_ADDR=$(ip addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v 127 | head -1)
if [ -n "$IP_ADDR" ]; then
    echo "   5G IP: $IP_ADDR"
else
    echo "   5G IP: NOT FOUND"
fi

echo ""
echo "5. Checking storage..."
STORAGE=$(df /data | tail -1 | awk '{printf "%.1f", $4/1048576}')
echo "   Free storage: ${STORAGE}GB"

echo ""
echo "6. Checking SSH authorized_keys..."
if [ -f ~/.ssh/authorized_keys ]; then
    KEYS=$(wc -l < ~/.ssh/authorized_keys)
    echo "   Authorized keys: $KEYS"
else
    echo "   Authorized keys: NONE"
fi

echo ""
echo "========================================"
echo "SUMMARY"
echo "========================================"
echo ""
echo "Username: $USERNAME"
echo "IP: $IP_ADDR"
echo "SSH: $(pgrep sshd > /dev/null && echo 'RUNNING' || echo 'NOT RUNNING')"
echo "SSH Key: $([ -f ~/.ssh/pixel10_github ] && echo 'EXISTS' || echo 'MISSING')"
echo ""
echo "Copy this info for GitHub setup:"
echo "  PIXEL10_SSH_USER: $USERNAME"
echo "  PIXEL10_IP: $IP_ADDR"
echo "  PIXEL10_SSH_PORT: 8022"
echo ""
