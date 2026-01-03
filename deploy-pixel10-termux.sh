#!/bin/bash

################################################################################
# Pixel 10 LLM Platform - Direct Termux Deployment
# Run this directly on your Pixel 10 inside Termux
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

print_header() {
    echo ""
    echo "================================================================================"
    echo "  $1"
    echo "================================================================================"
    echo ""
}

print_header "PIXEL 10 LLM PLATFORM - TERMUX DEPLOYMENT"

# Stage 1: Check prerequisites
log_info "Checking prerequisites..."

if ! command -v curl &> /dev/null; then
    log_info "Installing curl..."
    pkg install -y curl
fi

if ! command -v ssh-keygen &> /dev/null; then
    log_info "Installing openssh..."
    pkg install -y openssh
fi

if ! command -v ifconfig &> /dev/null; then
    log_info "Installing net-tools..."
    pkg install -y net-tools
fi

log_success "Termux environment ready"

# Stage 2: Get device IP
print_header "STAGE 1: GET DEVICE IP"

log_info "Getting your device IP address..."

# Try multiple methods to get IP
DEVICE_IP=""

# Method 1: ifconfig
if command -v ifconfig &> /dev/null; then
    DEVICE_IP=$(ifconfig wlan0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1 || echo "")
fi

# Method 2: ip command
if [ -z "$DEVICE_IP" ] && command -v ip &> /dev/null; then
    DEVICE_IP=$(ip addr show wlan0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}' || echo "")
fi

# Method 3: Manual entry
if [ -z "$DEVICE_IP" ]; then
    log_warning "Could not auto-detect IP."
    echo "How to find your IP:"
    echo "  1. Open Settings on your Pixel 10"
    echo "  2. Go to About Phone"
    echo "  3. Look for 'IP address' field"
    echo "  OR"
    echo "  4. Open WiFi settings and long-press your WiFi network"
    echo ""
    read -p "Enter your device WiFi IP (e.g., 192.168.1.100): " DEVICE_IP
fi

if [ -z "$DEVICE_IP" ]; then
    log_error "No IP provided. Cannot continue."
fi

log_success "Device IP: $DEVICE_IP"

# Stage 3: Check storage
print_header "STAGE 2: CHECK STORAGE"

log_info "Checking available storage..."
FREE_SPACE=$(df /data | tail -1 | awk '{print $4}')
FREE_GB=$((FREE_SPACE / 1048576))

log_info "Available storage: ${FREE_GB}GB"

if [ "$FREE_GB" -lt 5 ]; then
    log_error "Need at least 5GB free storage. You have ${FREE_GB}GB. Please free up space."
fi

log_success "Storage OK (${FREE_GB}GB available)"

# Stage 4: Generate SSH keys
print_header "STAGE 3: GENERATE SSH KEYS"

log_info "Creating SSH keys..."
mkdir -p ~/.ssh

if [ ! -f ~/.ssh/pixel10_github ]; then
    ssh-keygen -t ed25519 -f ~/.ssh/pixel10_github -N '' > /dev/null 2>&1
    log_success "SSH key generated"
else
    log_success "SSH key already exists"
fi

chmod 600 ~/.ssh/pixel10_github*

if [ ! -f ~/.ssh/authorized_keys ]; then
    touch ~/.ssh/authorized_keys
fi

grep -q "$(cat ~/.ssh/pixel10_github.pub)" ~/.ssh/authorized_keys || \
    cat ~/.ssh/pixel10_github.pub >> ~/.ssh/authorized_keys

log_success "SSH configured"

# Stage 5: Start SSH server
print_header "STAGE 4: START SSH SERVER"

log_info "Starting SSH server..."
sshd 2>/dev/null || true
sleep 2

if pgrep -x "sshd" > /dev/null 2>&1; then
    log_success "SSH server is running"
else
    log_warning "Starting SSH server in background..."
    sshd
    sleep 2
fi

log_success "SSH ready"

# Stage 7: Display private key
print_header "STAGE 5: YOUR SSH PRIVATE KEY"

echo "Copy everything below (BEGIN to END) and save it to GitHub Secrets:"
echo ""
echo "================================================================================"
cat ~/.ssh/pixel10_github
echo "================================================================================"
echo ""

# Stage 8: Display setup instructions
print_header "STAGE 6: GITHUB SETUP INSTRUCTIONS"

echo "Follow these steps:"
echo ""
echo "1. COPY SSH KEY"
echo "   Copy the private key from above (between the ========== lines)"
echo ""
echo "2. GO TO GITHUB SECRETS"
echo "   https://github.com/garrettc123/systems-master-hub/settings/secrets/actions"
echo ""
echo "3. CREATE 3 SECRETS:"
echo ""
echo "   Secret 1: PIXEL10_SSH_KEY"
echo "   Value: (paste the private key from above)"
echo ""
echo "   Secret 2: PIXEL10_IP"
echo "   Value: $DEVICE_IP"
echo ""
echo "   Secret 3: PIXEL10_SSH_PORT"
echo "   Value: 8022"
echo ""
echo "4. TRIGGER DEPLOYMENT"
echo "   Go to: https://github.com/garrettc123/systems-master-hub/actions"
echo "   Click: Deploy to Pixel 10"
echo "   Click: Run workflow button"
echo "   Fill in:"
echo "     Device IP: $DEVICE_IP"
echo "     SSH Port: 8022"
echo "     Dry Run: false"
echo "   Click: Run workflow"
echo ""
echo "5. WAIT FOR DEPLOYMENT"
echo "   Watch logs on GitHub"
echo "   Takes 20-25 minutes total"
echo ""
echo "6. VERIFY DEPLOYMENT"
echo "   After deployment, test:"
echo "   curl http://127.0.0.1:11434/api/ps"
echo ""

print_header "SUMMARY"

echo "✓ Termux environment ready"
echo "✓ SSH server running"
echo "✓ Device IP: $DEVICE_IP"
echo "✓ Storage checked"
echo "✓ SSH keys generated"
echo ""
echo "Ready for GitHub deployment! 🚀"
echo ""
echo "Next: Copy the SSH key and add the 3 GitHub Secrets"
echo ""
