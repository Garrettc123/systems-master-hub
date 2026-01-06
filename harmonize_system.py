import os
import subprocess
import json
from datetime import datetime

# --- CONFIGURATION ---
GITHUB_USER = "Garrettc123"
ROOT_DIR = "GARRETT_ENTERPRISE_SYSTEM"

# Harmonious Structure Definition
STRUCTURE = {
    "01_Core_Intelligence": [
        "APEX-Universal-AI-Operating-System",
        "async-automation-framework",
        "systems-master-hub"
    ],
    "02_Neural_Infrastructure": [
        "autohelix",
        "hypervelocity-orchestrator",
        "neural-mesh-pipeline",
        "ueep-ha-system",
        "enterprise-automation-system",
        "enterprise-mlops-platform"
    ],
    "03_Economic_Engine": [
        "revenue-agent-system",
        "stablecoin-protocol",
        "ai-business-platform"
    ],
    "04_Operations_Interface": [
        "ai-ops-studio",
        "process-copilot",
        "tree-of-life-system",
        "portfolio-website",
        "enterprise-unified-platform"
    ],
    "05_Protocols": [
        "nwu-protocol",
        "gwc1"
    ]
}

def run_command(command, cwd=None):
    """Executes a shell command harmoniously."""
    try:
        subprocess.run(command, shell=True, check=True, cwd=cwd, stdout=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        return False

def build_repo(repo_path):
    """Detects and builds the software system."""
    build_log = []
    
    # Python Build
    if os.path.exists(os.path.join(repo_path, "requirements.txt")):
        print(f"  🐍 Python system detected. Installing dependencies...")
        if run_command("pip install -r requirements.txt", cwd=repo_path):
            build_log.append("Python dependencies installed.")
            
    # Node/JS Build
    if os.path.exists(os.path.join(repo_path, "package.json")):
        print(f"  📦 Node system detected. Installing dependencies...")
        if run_command("npm install", cwd=repo_path):
            build_log.append("Node dependencies installed.")

    return build_log

def main():
    print(f"🌌 Initializing Harmonization Sequence for {GITHUB_USER}...")
    
    if not os.path.exists(ROOT_DIR):
        os.makedirs(ROOT_DIR)
        
    manifest = {
        "system_owner": GITHUB_USER,
        "harmonization_date": str(datetime.now()),
        "systems": {}
    }

    for domain, repos in STRUCTURE.items():
        domain_path = os.path.join(ROOT_DIR, domain)
        if not os.path.exists(domain_path):
            os.makedirs(domain_path)
            print(f"📂 Created Domain: {domain}")

        for repo in repos:
            repo_path = os.path.join(domain_path, repo)
            print(f"⚡ Harmonizing: {repo}...")
            
            # Clone if not exists
            if not os.path.exists(repo_path):
                clone_url = f"https://github.com/{GITHUB_USER}/{repo}.git"
                success = run_command(f"git clone {clone_url}", cwd=domain_path)
                if not success:
                    print(f"  ⚠️  Could not clone {repo}. Skipping.")
                    continue
            
            # Build System
            build_status = build_repo(repo_path)
            
            manifest["systems"][repo] = {
                "domain": domain,
                "path": repo_path,
                "build_status": build_status
            }

    # Generate Manifest
    with open(os.path.join(ROOT_DIR, "system_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=4)
        
    print("\n✨ Harmonization Complete. All systems unified.")

if __name__ == "__main__":
    main()
