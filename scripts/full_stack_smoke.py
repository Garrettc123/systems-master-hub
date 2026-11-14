"""Disposable phone + Forge + Actions integration run. Loopback only."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import selectors
import signal
import socket
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]


def run_smoke():
    with tempfile.TemporaryDirectory(prefix="garcar-full-stack-") as directory, ExitStack() as stack:
        temporary = Path(directory)
        workspace = temporary / "workspaces"
        workspace.mkdir()
        (workspace / "test_canary.py").write_text(
            "import os,unittest\nclass Canary(unittest.TestCase):\n"
            "    def test_isolated_environment(self):\n"
            "        self.assertNotIn('GARCAR_OPERATOR_TOKEN',os.environ)\n"
            "        self.assertNotIn('GARCAR_ACTIONS_TOKEN',os.environ)\n")
        env = {"PATH": os.pathsep.join([str(Path(sys.executable).parent), os.defpath]),
               "HOME": str(temporary), "TMPDIR": str(temporary), "LANG": "C.UTF-8",
               "PYTHONDONTWRITEBYTECODE": "1", "GARCAR_OPERATOR_TOKEN": secrets.token_hex(32),
               "GARCAR_ACTIONS_TOKEN": secrets.token_hex(32),
               "GARCAR_LEDGER_PATH": str(temporary / "forge.sqlite3"),
               "GARCAR_ACTIONS_DB": str(temporary / "actions.sqlite3"),
               "GARCAR_WORKSPACE": str(workspace), "GARCAR_WORKER_POLL_SECONDS": "1"}
        processes = []
        process_count = [0]
        env["GARCAR_CORE_DB"] = str(temporary / "core-leads.sqlite3")
        opener = build_opener(ProxyHandler({}))

        def start(command, cwd, name, *, descriptor=None, stdout=None):
            log = stack.enter_context((temporary / (name + ".log")).open("w+"))
            process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                       stdout=stdout or log, stderr=log, text=True,
                                       start_new_session=True,
                                       pass_fds=() if descriptor is None else (descriptor,))
            processes.append(process)
            process_count[0] += 1
            return process

        def api(module, cwd, name):
            # Pass a bound socket to uvicorn so concurrent canaries cannot race for a port.
            with socket.socket() as listener:
                listener.bind(("127.0.0.1", 0))
                listener.listen(64)
                port = listener.getsockname()[1]
                start([sys.executable, "-m", "uvicorn", module, "--fd", str(listener.fileno()),
                       "--log-level", "warning"], cwd, name, descriptor=listener.fileno())
            return f"http://127.0.0.1:{port}"

        def request(base, path, body=None, token=None, key=None):
            headers = {"Content-Type": "application/json"}
            if token:
                headers["Authorization"] = "Bearer " + token
            if key:
                headers["Idempotency-Key"] = key
            req = Request(base + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
            try:
                with opener.open(req, timeout=4) as response:
                    raw = response.read()
                    return response.status, json.loads(raw) if "json" in response.headers.get("Content-Type", "") else raw.decode()
            except HTTPError as error:
                return error.code, json.load(error)

        def require(condition, message):
            if not condition:
                raise AssertionError(message)

        def wait_ready(base, path):
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                if any(process.poll() is not None for process in processes):
                    raise RuntimeError("A canary service exited during startup")
                try:
                    if request(base, path)[0] == 200:
                        return
                except (URLError, OSError):
                    pass
                time.sleep(0.1)
            raise RuntimeError("Canary API did not become ready")

        def forge_cli(*arguments):
            completed = subprocess.run([sys.executable, "-m", "app.backup", *arguments],
                                       cwd=ROOT / "garcar-forge", env=env, capture_output=True,
                                       text=True, check=True, timeout=15)
            return json.loads(completed.stdout)

        try:
            forge = api("app.main:app", ROOT / "garcar-forge", "forge-api")
            wait_ready(forge, "/readyz")
            actions_process = start([sys.executable, "-m", "garcar_actions.engine", "serve", "--port", "0"],
                                    ROOT / "garcar-actions", "actions-api", stdout=subprocess.PIPE)
            with selectors.DefaultSelector() as selector:
                selector.register(actions_process.stdout, selectors.EVENT_READ)
                require(bool(selector.select(10)), "Actions API did not start")
                actions_port = json.loads(actions_process.stdout.readline())["port"]
            actions = f"http://127.0.0.1:{actions_port}"
            env.update(GARCAR_FORGE_URL=forge, GARCAR_ACTIONS_URL=actions)
            phone = api("revenue.garcar_core.app:app", ROOT, "phone-api")
            phone_process = processes[-1]
            wait_ready(phone, "/healthz")
            code, view = request(phone, "/api/stack/status")
            require(code == 200 and view["ready"], "Phone console could not authenticate to both services")
            code, page = request(phone, "/")
            require(code == 200 and 'id="forgeState"' in page and 'id="actionsState"' in page,
                    "Phone UI did not serve integrated service cards")
            require(request(phone, "/api/phone/status")[1]["configured_count"] == 0,
                    "External credentials unexpectedly entered the canary")
            require(request(phone, "/api/knowledge/search", {"query": "local canary"})[0] == 503,
                    "Knowledge providers did not fail closed without credentials")
            require(request(forge, "/v1/status")[0] == 401 and request(actions, "/v1/status")[0] == 401,
                    "Management status exposed without authentication")
            require(request(forge, "/v1/deployments/execute", {}, env["GARCAR_OPERATOR_TOKEN"])[0] == 423,
                    "Live deployment execution was not locked")

            lead = {"event_id": "full-stack-local-canary", "tenant_id": "garcar-local-canary",
                    "source": "web_form", "occurred_at": "2026-11-02T20:00:00Z",
                    "customer": {"name": "Garcar Local Canary", "email": "canary@example.invalid"},
                    "request": {"service": "Local integration verification"}}
            first = request(phone, "/v1/events/lead", lead, key="full-stack-lead-canary")
            second = request(phone, "/v1/events/lead", lead, key="full-stack-lead-canary")
            require(first[0] == second[0] == 202 and first[1]["lead_id"] == second[1]["lead_id"],
                    "Lead API idempotency failed")
            os.killpg(phone_process.pid, signal.SIGTERM)
            phone_process.wait(timeout=3)
            processes.remove(phone_process)
            phone = api("revenue.garcar_core.app:app", ROOT, "phone-api-restarted")
            wait_ready(phone, "/healthz")
            replay = request(phone, "/v1/events/lead", lead, key="full-stack-lead-canary")
            require(replay[0] == 202 and replay[1] == first[1], "Lead was lost or recreated after API restart")

            code, queued = request(actions, "/v1/jobs", {"action": "python_tests"},
                                   env["GARCAR_ACTIONS_TOKEN"], key="full-stack-actions-canary")
            require(code == 202, "Actions job submission failed")
            subprocess.run([sys.executable, "-m", "garcar_actions.engine", "worker", "--once"],
                           cwd=ROOT / "garcar-actions", env=env, check=True, timeout=15)
            process_count[0] += 1
            code, result = request(actions, "/v1/jobs/" + queued["id"], token=env["GARCAR_ACTIONS_TOKEN"])
            require(code == 200 and result["status"] == "succeeded", "Actions worker did not complete its canary")
            actions_audit = request(actions, "/v1/audit/verify", token=env["GARCAR_ACTIONS_TOKEN"])[1]
            require(actions_audit["valid"], "Actions audit failed")

            body = {"task_name": "ledger.verify", "idempotency_key": "full-stack-forge-canary", "dry_run": True}
            code, queued = request(forge, "/v1/jobs", body, env["GARCAR_OPERATOR_TOKEN"])
            require(code == 202, "Forge job submission failed")
            start([sys.executable, "-m", "app.worker"], ROOT / "garcar-forge", "forge-worker")
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                result = request(forge, "/v1/jobs/" + queued["job"]["job_id"], token=env["GARCAR_OPERATOR_TOKEN"])[1]["job"]
                if result["status"] in ("succeeded", "failed"):
                    break
                time.sleep(0.1)
            require(result["status"] == "succeeded", "Forge worker did not complete its canary")
            forge_audit = request(forge, "/v1/ledger/verify", token=env["GARCAR_OPERATOR_TOKEN"])[1]
            require(forge_audit["valid"], "Forge audit failed")
            backup = forge_cli("create", "--source", env["GARCAR_LEDGER_PATH"], "--destination", str(temporary / "backups"))
            verified = forge_cli("verify", backup["backup"])
            restored = forge_cli("restore", backup["backup"], "--target", str(temporary / "restored.sqlite3"), "--confirm-restore")
            require(verified["valid"] and restored["verified"], "Backup/restore failed")
            final_view = request(phone, "/api/stack/status")[1]
            require(final_view["ready"] and final_view["services"]["actions"]["queue"]["succeeded"] == 1,
                    "Phone console did not reflect the completed job")
            return {"result": "passed", "scope": "disposable_local_full_stack", "separate_processes_started": process_count[0],
                    "phone_served": True, "phone_service_status": final_view, "lead_idempotency": "passed",
                    "lead_storage": "sqlite_wal", "lead_replay_after_api_restart": "passed",
                    "actions_job": "succeeded", "actions_audit": actions_audit,
                    "forge_job": "succeeded", "forge_audit": forge_audit,
                    "backup_verified": True, "restore_verified": True, "live_execution_http_status": 423,
                    "external_provider_calls": 0, "production_deployment_performed": False}
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    try:
                        os.killpg(process.pid, signal.SIGTERM)
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=3)
                if process.stdout is not None:
                    process.stdout.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = run_smoke()
    serialized = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
