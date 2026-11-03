"""Run the pinned structure-check port against this hub using disposable state."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

package = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(package))
from garcar_actions.engine import job_environment

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
with tempfile.TemporaryDirectory(prefix="garcar-hub-canary-") as directory:
    env = job_environment(directory)
    env.update(GARCAR_ACTIONS_DB=str(Path(directory) / "state/actions.db"), GARCAR_WORKSPACE=str(package.parent))

    def run(*command):
        result = subprocess.run([sys.executable, "-m", *command], cwd=package, env=env,
                                capture_output=True, text=True, check=True, timeout=30)
        return json.loads(result.stdout) if result.stdout.strip() else None

    queued = run("garcar_actions.migration.workflow", "--submit", "--idempotency-key", "hub-structure-canary")
    run("garcar_actions.engine", "worker", "--once")
    jobs = run("garcar_actions.engine", "status")
    audit = run("garcar_actions.engine", "audit-verify")
    if len(jobs) != 1 or jobs[0]["id"] != queued["id"] or jobs[0]["status"] != "succeeded" or not audit["valid"]:
        raise SystemExit(f"Hub canary failed: {jobs}, {audit}")
    report = {"result": "passed", "scope": "local_hub_structure_canary", "repository": queued["repository"],
              "source_path": queued["source_path"], "source_sha256": queued["source_sha256"],
              "source_job": queued["source_job"], "action": queued["action"], "exit_code": jobs[0]["exit_code"],
              "audit": audit, "semantic_changes": queued["semantic_changes"],
              "untranslated_jobs": queued["untranslated_jobs"], "production_enabled": False}
    serialized = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
