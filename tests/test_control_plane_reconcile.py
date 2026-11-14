import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "control-plane" / "reconcile.py"


class ControlPlaneReconcileTests(unittest.TestCase):
    def run_registry(self, payload):
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "systems.json"
            registry.write_text(json.dumps(payload), encoding="utf-8")
            env = os.environ.copy()
            env["GARCAR_REGISTRY"] = str(registry)
            return subprocess.run(
                [sys.executable, str(SCRIPT)],
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )

    def test_repository_registry_passes_but_does_not_claim_runtime_health(self):
        registry = Path(__file__).resolve().parents[1] / "control-plane" / "systems.json"
        env = os.environ.copy()
        env["GARCAR_REGISTRY"] = str(registry)
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("RUNTIME HEALTH: NOT CHECKED", result.stdout)

    def test_production_entry_without_evidence_fails_closed(self):
        result = self.run_registry({
            "version": "1",
            "systems": [{
                "repository": "example-service",
                "environment": "prod",
                "production": True,
                "desired": {},
                "observed": {},
            }],
            "invariants": [],
        })
        self.assertEqual(result.returncode, 1)
        self.assertIn("missing valid healthcheck", result.stdout)
        self.assertIn("missing valid artifact_digest_source", result.stdout)
        self.assertIn("missing valid deployment_evidence", result.stdout)

    def test_unknown_properties_are_rejected(self):
        result = self.run_registry({
            "version": "1",
            "systems": [{
                "repository": "example-service",
                "environment": "dev",
                "desired": {},
                "observed": {},
                "unapproved": True,
            }],
            "invariants": [],
        })
        self.assertEqual(result.returncode, 1)
        self.assertIn("unsupported properties: unapproved", result.stdout)


if __name__ == "__main__":
    unittest.main()
