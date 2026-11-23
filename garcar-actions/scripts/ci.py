"""Local validation entry point independent of hosted CI and third-party packages."""
from pathlib import Path
import argparse
import py_compile
import subprocess
import sys

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--report-dir", type=Path)
args = parser.parse_args()
smoke = [sys.executable, "-m", "garcar_actions.smoke"]
hub = [sys.executable, "scripts/hub-canary.py"]
if args.report_dir:
    target = args.report_dir.resolve()
    smoke.extend(["--report", str(target / "local-smoke.json")])
    hub.extend(["--report", str(target / "hub-canary.json")])
for directory in (root / "garcar_actions", root / "tests", root / "scripts"):
    for source in directory.rglob("*.py"):
        py_compile.compile(str(source), doraise=True)
for command in ([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                smoke, hub):
    result = subprocess.run(command, cwd=root, check=False, timeout=120)
    if result.returncode:
        raise SystemExit(result.returncode)
print("Garcar Actions local CI passed: compilation, unit tests, API/worker canary, pinned hub canary.")
