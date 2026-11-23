from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

RISK_PATTERNS = {
    "secret_reference": re.compile(r"\$\{\{\s*secrets\.|[A-Z0-9_]*(TOKEN|API_KEY|SECRET|PASSWORD)"),
    "deployment": re.compile(r"\b(deploy|terraform\s+apply|kubectl\s+apply|wrangler\s+deploy|railway|render)\b", re.I),
    "financial_or_commerce": re.compile(r"\b(stripe|shopify|settle|payment|invoice|charge|payout)\b", re.I),
    "customer_outreach": re.compile(r"\b(send|email|sms|outreach|lead|resend)\b", re.I),
    "repository_mutation": re.compile(r"\b(auto.?merge|approve|create.?pull.?request|contents:\s*write|pull-requests:\s*write)\b", re.I),
    "self_healing": re.compile(r"\b(self.?heal|remediat|rollback|rotate)\b", re.I),
    "shell_execution": re.compile(r"^\s*(?:-\s*)?(run:|shell:)", re.M),
    "privileged_trigger": re.compile(r"\b(pull_request_target|workflow_run)\b"),
    "write_permission": re.compile(r"\b[a-z-]+:\s*write\b"),
    "third_party_action": re.compile(r"^\s*-\s*uses:\s*([^\s]+)", re.M),
}
WORKFLOW_DIRS = (".github/workflows", "local-actions/workflows")

def classify_file(path: Path, root: Path) -> dict:
    raw = path.read_bytes()
    content = raw.decode("utf-8", errors="replace")
    flags = [name for name, pattern in RISK_PATTERNS.items() if pattern.search(content)]
    rel = path.relative_to(root).as_posix()
    if "financial_or_commerce" in flags or "customer_outreach" in flags:
        tier = "restricted_business_action"
    elif any(x in flags for x in ("deployment", "repository_mutation", "self_healing", "secret_reference", "privileged_trigger", "write_permission")):
        tier = "approval_required"
    elif re.search(r"self[-_]hosted", content, re.I):
        tier = "host_isolation_review"
    else:
        tier = "read_only_candidate"
    return {
        "path": rel,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "classification": tier,
        "risk_flags": flags,
        "migration_status": "discovered_not_translated",
    }

def scan(root: Path) -> dict:
    root = root.resolve()
    found = []
    for directory in WORKFLOW_DIRS:
        base = root / directory
        if base.is_dir() and not any(p.is_symlink() for p in (base, *base.parents) if p != root and root in p.parents):
            for path in sorted(base.rglob("*")):
                if path.is_file() and not path.is_symlink() and path.suffix.lower() in (".yml", ".yaml", ".json"):
                    found.append(classify_file(path, root))
    return {
        "schema_version": "1.0",
        "repository_root": str(root),
        "workflow_count": len(found),
        "classification_counts": {
            tier: sum(1 for item in found if item["classification"] == tier)
            for tier in ("read_only_candidate", "approval_required", "restricted_business_action", "host_isolation_review")
        },
        "workflows": found,
    }

def main():
    parser = argparse.ArgumentParser(description="Inventory and classify workflow definitions; never executes them.")
    parser.add_argument("repository", nargs="?", default=".")
    parser.add_argument("--output", default="garcar-actions-inventory.json")
    args = parser.parse_args()
    report = scan(Path(args.repository))
    Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "workflows"}, indent=2))
    print(f"Report: {args.output}")

if __name__ == "__main__":
    main()
