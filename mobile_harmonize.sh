#!/bin/bash

# POCKET COMMANDER - Mobile Harmonization System
# Run this in Termux on Android

echo "📱 Initializing Pocket Commander..."

# Install essential tools
pkg update -y
pkg install -y git python nodejs-lts nano

# Create mobile workspace
cd ~
MOBILE_HQ="MobileHQ"
mkdir -p $MOBILE_HQ
cd $MOBILE_HQ

# Lightweight structure (only essentials for mobile)
declare -A MOBILE_SYSTEMS=(
    ["CoreControl"]="APEX-Universal-AI-Operating-System systems-master-hub"
    ["QuickOps"]="tree-of-life-system portfolio-website"
    ["MoneyWatch"]="revenue-agent-system ai-business-platform"
    ["Scripts"]="async-automation-framework neural-mesh-pipeline"
)

echo "🗂️  Creating mobile folder structure..."

for domain in "${!MOBILE_SYSTEMS[@]}"; do
    mkdir -p "$domain"
    echo "✓ Created: $domain/"
done

# Clone only the most essential repositories
ESSENTIAL_REPOS=(
    "systems-master-hub"
    "tree-of-life-system"
    "async-automation-framework"
    "portfolio-website"
)

echo "⬇️  Downloading essential systems..."

for repo in "${ESSENTIAL_REPOS[@]}"; do
    if [ ! -d "$repo" ]; then
        git clone --depth 1 https://github.com/Garrettc123/$repo.git 2>/dev/null
        [ $? -eq 0 ] && echo "  ✓ $repo" || echo "  ✗ $repo (skipped)"
    fi
done

# Create mobile dashboard script
cat > ~/MobileHQ/dashboard.sh << 'DASHBOARD'
#!/bin/bash
clear
echo "╔════════════════════════════════════╗"
echo "║   POCKET COMMANDER DASHBOARD      ║"
echo "╚════════════════════════════════════╝"
echo ""
echo "📂 Your Mobile Systems:"
ls -d */ | nl
echo ""
echo "⚡ Quick Actions:"
echo "  1) Update all repos (git pull)"
echo "  2) View system status"
echo "  3) Edit README files"
echo "  4) Push changes to GitHub"
echo "  q) Quit"
echo ""
read -p "Choose action: " choice

case $choice in
    1) find . -name .git -type d -execdir git pull \; ;;
    2) du -sh */ ;;
    3) find . -name README.md | fzf | xargs nano ;;
    4) read -p "Commit message: " msg; 
       find . -name .git -type d -execdir sh -c 'git add -A && git commit -m "$1" && git push' _ "$msg" \; ;;
    q) exit 0 ;;
esac
DASHBOARD

chmod +x ~/MobileHQ/dashboard.sh

echo ""
echo "✨ Pocket Commander ready!"
echo ""
echo "📍 Location: ~/MobileHQ"
echo "🚀 Launch: bash ~/MobileHQ/dashboard.sh"
