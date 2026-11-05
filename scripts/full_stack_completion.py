"""Run local completion checks and report production blockers without deploying."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "garcar-actions"))
from garcar_actions.execution import execute

EXCLUDE = {".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", "data", ".pytest_cache", ".ruff_cache"}


def files():
    for directory, names, filenames in os.walk(ROOT, followlinks=False):
        names[:] = sorted(name for name in names if name not in EXCLUDE and not (Path(directory) / name).is_symlink())
        for name in sorted(filenames):
            path = Path(directory) / name
            if not path.is_symlink():
                yield path


def validate_sources():
    import yaml
    counts = {"python": 0, "javascript": 0, "shell": 0, "json": 0, "yaml": 0}
    errors = []
    for path in files():
        try:
            suffix = path.suffix
            if suffix == ".py":
                ast.parse(path.read_text(), filename=str(path))
                counts["python"] += 1
            elif suffix == ".json":
                json.loads(path.read_text())
                counts["json"] += 1
            elif suffix in (".yaml", ".yml"):
                yaml.compose(path.read_text())
                counts["yaml"] += 1
            elif suffix in (".js", ".mjs", ".sh"):
                binary = shutil.which("bash" if suffix == ".sh" else "node")
                if binary is None:
                    raise RuntimeError("Required syntax checker unavailable")
                result = subprocess.run([binary, "-n" if suffix == ".sh" else "--check", str(path)],
                                        capture_output=True, text=True, timeout=10, check=False)
                counts["shell" if suffix == ".sh" else "javascript"] += 1
                if result.returncode:
                    raise RuntimeError(result.stderr[-1500:])
        except (OSError, ValueError, SyntaxError, RuntimeError, subprocess.TimeoutExpired, yaml.YAMLError) as error:
            errors.append({"path": path.relative_to(ROOT).as_posix(), "error": str(error)[:1800]})
    return {"result": "passed" if not errors else "failed", "counts": counts, "errors": errors}


def production_preflight():
    import yaml
    config = yaml.safe_load((ROOT / "docker-compose.yml").read_text())
    services = config.get("services", {})
    missing, weak, exposed = [], [], []
    for name, service in services.items():
        build = service.get("build")
        if build:
            context = build if isinstance(build, str) else build.get("context", ".")
            directory = (ROOT / context).resolve()
            dockerfile = "Dockerfile" if isinstance(build, str) else build.get("dockerfile", "Dockerfile")
            if not directory.is_dir() or not (directory / dockerfile).is_file():
                missing.append({"service": name, "context": context, "dockerfile": dockerfile})
        environment = service.get("environment", {})
        if isinstance(environment, list):
            environment = dict(item.split("=", 1) if "=" in item else (item, "") for item in environment)
        for key, value in environment.items():
            text = str(value)
            if ("PASSWORD" in key and text in {"enterprise", "admin123", "password", "admin", "changeme"}) or "enterprise:enterprise@" in text:
                weak.append(f"{name}:{key}")
        for port in service.get("ports", []):
            if isinstance(port, str) and not port.startswith(("127.0.0.1:", "[::1]:")):
                exposed.append(name)
                break
    blockers = []
    if not shutil.which("docker"):
        blockers.append({"code": "docker_unavailable", "detail": "Docker image build and Compose runtime cannot be verified on this host."})
    if missing:
        blockers.append({"code": "missing_build_sources", "services": missing})
    if weak:
        blockers.append({"code": "legacy_default_credentials", "environment_keys": sorted(weak)})
    if exposed:
        blockers.append({"code": "legacy_non_loopback_ports", "services": sorted(exposed)})
    if "store = InMemoryStore()" in (ROOT / "revenue/garcar_core/app.py").read_text():
        blockers.append({"code": "lead_store_not_durable", "detail": "Core lead ingestion is still an in-memory prototype."})
    else:
        blockers.append({"code": "core_lead_volume_unverified", "detail": "SQLite persistence is canary-tested; a private persistent GARCAR_CORE_DB volume and its target-host backup/recovery still require verification."})
    blockers.extend([
        {"code": "live_integrations_unverified", "detail": "No paid provider request, live payment, or customer outreach is exercised by this run."},
        {"code": "production_isolation_unverified", "detail": "Per-job OS isolation, external audit anchoring, host recovery, and protected public access still require target-host evidence."},
    ])
    return {"status": "blocked" if blockers else "ready", "legacy_compose_services": len(services), "blockers": blockers}


def completion_outcome(stages, blockers, local_only=False):
    if not stages or any(stage["status"] not in {"passed", "failed", "blocked"} for stage in stages):
        return "software_evidence_missing", "incomplete", 2
    failed = any(stage["status"] == "failed" for stage in stages)
    blocked = any(stage["status"] == "blocked" for stage in stages)
    if failed:
        return "software_checks_failed", "failed", 1
    if blocked:
        return "local_canary_passed_host_check_blocked", "incomplete_host_check", 2
    if blockers:
        return "local_canary_passed_production_blocked", "passed", 0 if local_only else 2
    return "passed", "passed", 0


def run(report_dir, local_only):
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(ZoneInfo("America/Chicago")).isoformat()
    missing = [name for name in ("yaml", "fastapi", "uvicorn", "httpx", "pytest", "pydantic", "ruff")
               if importlib.util.find_spec(name) is None]
    if missing:
        report = {"result": "dependencies_missing", "software_status": "blocked", "checked_at": timestamp,
                  "missing_modules": missing, "remedy": "Install requirements-completion.lock in an isolated virtual environment."}
        (report_dir / "completion.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return 2
    preflight = production_preflight()
    source_check = validate_sources()
    stages = [{"name": "source_syntax", "status": source_check["result"], "details": source_check}]
    node = shutil.which("node")
    with tempfile.TemporaryDirectory(prefix="garcar-completion-") as temporary:
        env = {"PATH": os.pathsep.join([str(Path(sys.executable).parent), *( [str(Path(node).parent)] if node else []), os.defpath]),
               "HOME": temporary, "TMPDIR": temporary, "LANG": "C.UTF-8", "CI": "1",
               "PYTHONDONTWRITEBYTECODE": "1", "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
               "GARCAR_LEDGER_PATH": str(Path(temporary) / "forge-test.sqlite3")}
        python = sys.executable
        commands = [
            ("dependency_consistency", [python, "-m", "pip", "check"], ROOT),
            ("security_provider_registry_tests", [python, "-m", "unittest", "discover", "-s", "tests", "-v"], ROOT),
            ("sovereign_tests", [python, "-m", "unittest", "discover", "-s", "sovereign/tests", "-v"], ROOT),
            ("phone_core_tests", [python, "-m", "pytest", "-q", "revenue/garcar_core"], ROOT),
            ("forge_tests", [python, "-m", "pytest", "-q", "-o", "addopts="], ROOT / "garcar-forge"),
            ("forge_core_lint", [python, "-m", "ruff", "check", "garcar-forge/app", "garcar-forge/tests", "revenue/garcar_core"], ROOT),
            ("actions_ci", [python, "scripts/ci.py", "--report-dir", str(report_dir / "actions")], ROOT / "garcar-actions"),
            ("termux_pid_guard", [shutil.which("bash") or "bash", "scripts/test-termux-pid-guard.sh"], ROOT / "garcar-forge"),
            ("forge_wheel", [python, "-m", "pip", "wheel", "--no-index", "--no-deps", "--no-build-isolation", ".", "-w", str(Path(temporary) / "wheel")], ROOT / "garcar-forge"),
            ("sovereign_promotion_rollback", [python, "scripts/sovereign_smoke.py", "--report", str(report_dir / "sovereign-smoke.json")], ROOT),
            ("full_stack_process_canary", [python, "scripts/full_stack_smoke.py", "--report", str(report_dir / "full-stack-smoke.json")], ROOT),
        ]
        for name, command, cwd in commands:
            if name == "termux_pid_guard":
                probe = subprocess.Popen([python, "-c", "import time;time.sleep(10)"], env=env)
                try:
                    try:
                        Path(f"/proc/{probe.pid}/environ").read_bytes()
                        readable = True
                    except OSError:
                        readable = False
                finally:
                    probe.terminate()
                    probe.wait(timeout=3)
                if not readable:
                    (report_dir / (name + ".txt")).write_text(
                        "BLOCKED: this host denies reading a child process environment through /proc. "
                        "The process ownership guard remains fail-closed; run its regression test on the target device.\n")
                    stages.append({"name": name, "status": "blocked", "tests_passed": 0,
                                   "reason": "host_denies_proc_environ", "log": name + ".txt"})
                    print(name + ": blocked (host denies process identity inspection)", flush=True)
                    continue
            started = time.monotonic()
            result = execute(command, cwd=cwd, env=env, timeout=120, output_limit=2_097_152, tail_bytes=131072)
            (report_dir / (name + ".txt")).write_text(result.output, encoding="utf-8")
            count = sum(int(x) for x in re.findall(r"Ran (\d+) tests?", result.output))
            if not count:
                matches = re.findall(r"(\d+) passed", result.output)
                count = sum(map(int, matches))
            stages.append({"name": name, "status": "passed" if result.returncode == 0 else "failed",
                           "exit_code": result.returncode, "tests_passed": count if result.returncode == 0 else 0,
                           "seconds": round(time.monotonic() - started, 3), "log": name + ".txt"})
            print(name + ": " + stages[-1]["status"], flush=True)
    outcome, software_status, exit_code = completion_outcome(stages, preflight["blockers"], local_only)
    versions = {name: importlib.metadata.version(name) for name in ("fastapi", "uvicorn", "httpx", "pytest", "pydantic", "PyYAML", "ruff")}
    source_manifest = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in files() if (path.suffix in {".py", ".js", ".sh", ".yml", ".yaml", ".toml", ".json", ".lock"} or path.name == "Makefile") and not path.is_relative_to(report_dir)}
    report = {"schema_version": "1.0", "checked_at": timestamp,
              "result": outcome,
              "software_status": software_status,
              "tests_passed": sum(stage.get("tests_passed", 0) for stage in stages),
              "stages": stages, "production_readiness": preflight, "runtime_versions": versions,
              "production_deployment_performed": False, "external_payment_or_outreach_performed": False}
    (report_dir / "source-sha256.json").write_text(json.dumps(source_manifest, indent=2) + "\n")
    (report_dir / "completion.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"result": report["result"], "tests_passed": report["tests_passed"],
                      "production_blockers": len(preflight["blockers"])}, indent=2))
    return exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-dir", type=Path, default=ROOT / "validation/full-stack")
    parser.add_argument("--local-only", action="store_true", help="Return success for passing local checks while reporting production blockers")
    args = parser.parse_args()
    raise SystemExit(run(args.report_dir.resolve(), args.local_only))
