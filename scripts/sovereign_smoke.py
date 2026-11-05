"""Verify a real loopback promotion and rollback using disposable fixture processes."""
import argparse
import importlib.util
import json
import socket
import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sovereign_canary", ROOT / "sovereign/garcar.py")
garcar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(garcar)


def run_smoke():
    with tempfile.TemporaryDirectory(prefix="garcar-sovereign-smoke-") as directory:
        root = Path(directory)
        source = root / "source"
        source.mkdir()
        with socket.socket() as main, socket.socket() as canary:
            main.bind(("127.0.0.1", 0))
            canary.bind(("127.0.0.1", 0))
            port, canary_port = main.getsockname()[1], canary.getsockname()[1]
        config = {"name": "garcar-sovereign-canary", "build": [],
                  "start": [sys.executable, "api.py"], "port": port, "canary_port": canary_port,
                  "health": {"path": "/health"}, "env_passthrough": []}
        (source / "garcar.deploy.json").write_text(json.dumps(config))

        def application(fail_promotion):
            return ("from http.server import BaseHTTPRequestHandler,HTTPServer\nimport os\n"
                    "port=int(os.environ['PORT'])\n"
                    f"failure={fail_promotion!r} and port=={port}\n"
                    "class Health(BaseHTTPRequestHandler):\n"
                    "    def do_GET(self):\n"
                    "        self.send_response(503 if failure else 200);self.end_headers();self.wfile.write(b'canary')\n"
                    "    def log_message(self,*args): pass\n"
                    "HTTPServer(('127.0.0.1',port),Health).serve_forever()\n")

        original_health = garcar.health
        with patch.object(garcar, "ROOT", root / "state"), patch.object(garcar, "DB", root / "state/state/control.sqlite3"), \
                patch.object(garcar, "health", lambda port, path, timeout=20: original_health(port, path, timeout=1.5)):
            try:
                (source / "api.py").write_text(application(False))
                garcar.deploy(source)
                first = garcar.current_record(config["name"])
                assert first and garcar.health(port, "/health")[0]
                (source / "api.py").write_text(application(True))
                try:
                    garcar.deploy(source)
                except RuntimeError as error:
                    assert "health check failed" in str(error)
                else:
                    raise AssertionError("Unhealthy promoted release was accepted")
                restored = garcar.current_record(config["name"])
                assert restored[0] == first[0] and restored[1] != first[1]
                assert garcar.health(port, "/health")[0]
                with sqlite3.connect(garcar.DB) as database:
                    events = [row[0] for row in database.execute("SELECT action FROM audit ORDER BY seq")]
                assert "rollback_restored" in events and "deploy_failed" in events
                valid, _ = garcar.verify_ledger()
                assert valid
                return {"result": "passed", "scope": "disposable_local_promotion_and_rollback",
                        "healthy_release_promoted": True, "unhealthy_promotion_rejected": True,
                        "prior_release_restarted_and_healthy": True, "audit_valid": True,
                        "events": events, "target_device_verified": False}
            finally:
                garcar.stop(config["name"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = run_smoke()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
