"""Disposable local API/worker integration canary. No external service calls."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import selectors
import subprocess
import sys
import tempfile
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from garcar_actions.engine import job_environment

PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def run_smoke():
    with tempfile.TemporaryDirectory(prefix="garcar-smoke-") as temporary:
        root = Path(temporary)
        workspace = root / "workspaces"
        workspace.mkdir()
        for name in ("passing", "failing", "empty"):
            directory = workspace / name / "tests"
            directory.mkdir(parents=True)
            if name != "empty":
                assertion = "self.assertEqual(2 + 2, 4)" if name == "passing" else "self.fail('expected canary failure')"
                (directory / "test_sample.py").write_text(
                    "import unittest\nclass Sample(unittest.TestCase):\n    def test_case(self): " + assertion + "\n")
        token = secrets.token_urlsafe(32)
        env = job_environment(str(root))
        env.update(GARCAR_ACTIONS_TOKEN=token, GARCAR_ACTIONS_DB=str(root / "state/actions.db"),
                   GARCAR_WORKSPACE=str(workspace))
        opener = build_opener(ProxyHandler({}))
        receipts = []
        with (root / "api.log").open("w+") as logs:
            api = subprocess.Popen([sys.executable, "-m", "garcar_actions.engine", "serve", "--port", "0"],
                                   cwd=PACKAGE_ROOT, env=env, stdout=subprocess.PIPE,
                                   stderr=logs, text=True)
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(api.stdout, selectors.EVENT_READ)
                    if not selector.select(10):
                        raise AssertionError("API did not start within ten seconds")
                    ready = json.loads(api.stdout.readline())
                base = f"http://127.0.0.1:{ready['port']}"

                def request(path, body=None, *, authorized=True, key=None):
                    headers = {"Content-Type": "application/json"}
                    if authorized:
                        headers["Authorization"] = "Bearer " + token
                    if key:
                        headers["Idempotency-Key"] = key
                    data = json.dumps(body).encode() if body is not None else None
                    req = Request(base + path, data=data, headers=headers)
                    try:
                        with opener.open(req, timeout=5) as response:
                            return response.status, json.load(response)
                    except HTTPError as error:
                        return error.code, json.load(error)

                def expect(condition, message):
                    if not condition:
                        raise AssertionError(message)

                expect(request("/health", authorized=False)[0] == 200, "Health probe failed")
                expect(request("/v1/jobs/unknown", authorized=False)[0] == 401, "Authentication did not fail closed")
                expect(request("/v1/jobs", ["invalid"])[0] == 400, "Non-object body accepted")
                expect(request("/v1/jobs", {"action": "shell"})[0] == 400, "Arbitrary command accepted")
                expect(request("/v1/jobs", {"action": "python_tests", "repo_path": ".."})[0] == 400,
                       "Workspace traversal accepted")
                expect(request("/v1/jobs", {"action": "python_tests", "extra": True})[0] == 400,
                       "Unknown request field accepted")
                expect(request("/v1/jobs", {"action": "python_tests", "repo_path": []})[0] == 400,
                       "Invalid path type accepted")
                expect(request("/v1/jobs", {"action": "x" * 17000})[0] == 400,
                       "Oversized body accepted")
                jobs = []
                for action, path, expected_code in (("python_tests", "passing", 0),
                                                    ("python_tests", "failing", 1),
                                                    ("python_tests", "empty", 5),
                                                    ("python_compile", "passing", 0)):
                    payload = {"action": action, "repo_path": path}
                    key = f"smoke-{len(jobs)}"
                    code, queued = request("/v1/jobs", payload, key=key)
                    expect(code == 202, "Submission failed")
                    code, duplicate = request("/v1/jobs", payload, key=key)
                    expect(code == 202 and duplicate["id"] == queued["id"], "Duplicate request created another job")
                    jobs.append((queued["id"], action, path, expected_code))
                for job_id, action, path, expected_code in jobs:
                    worker = subprocess.run([sys.executable, "-m", "garcar_actions.engine", "worker", "--once"],
                                            cwd=PACKAGE_ROOT, env=env, capture_output=True, text=True, timeout=20)
                    expect(worker.returncode == 0, f"Worker failed: {worker.stderr}")
                    code, job = request("/v1/jobs/" + job_id)
                    expected_status = "succeeded" if expected_code == 0 else "failed"
                    expect(code == 200 and job["status"] == expected_status and job["exit_code"] == expected_code,
                           f"Unexpected job outcome: {job}")
                    receipts.append({"action": action, "fixture": path, "status": job["status"],
                                     "exit_code": job["exit_code"]})
                code, ledger = request("/v1/audit/verify")
                expect(code == 200 and ledger == {"valid": True, "entries_checked": 12},
                       f"Audit verification failed: {ledger}")
                return {"schema_version": "1.0", "result": "passed", "scope": "disposable_local_canary",
                        "auth_and_request_rejection_checks": 8, "duplicate_requests_reused": 4,
                        "jobs": receipts, "audit": ledger}
            finally:
                api.terminate()
                try:
                    api.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    api.kill()
                    api.wait(timeout=5)
                api.stdout.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = run_smoke()
    serialized = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(serialized, encoding="utf-8")
    print(serialized, end="")


if __name__ == "__main__":
    main()
