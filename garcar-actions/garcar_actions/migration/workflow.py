"""Plan or submit the reviewed, source-pinned hub structure canary."""
import argparse
import json
from pathlib import Path

from garcar_actions import engine


def plan(repo_path="."):
    profile = json.loads((Path(__file__).resolve().parents[2] / "migration/hub-structure.json").read_text())
    target = engine.workspace_target(repo_path)
    engine.verify_source_pin(target, profile["source_path"], profile["source_sha256"])
    return {**profile, "repo_path": str(target), "source_verified": True, "status": "planned_not_executed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--submit", action="store_true", help="Queue the reviewed local canary; default only plans")
    parser.add_argument("--idempotency-key")
    args = parser.parse_args()
    report = plan(args.repo)
    if args.submit:
        report["id"] = engine.enqueue(report["action"], report["repo_path"],
                                      requested_by="hub-structure-canary", idempotency_key=args.idempotency_key,
                                      source_path=report["source_path"], source_sha256=report["source_sha256"])
        report["status"] = "queued_local_canary"
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
