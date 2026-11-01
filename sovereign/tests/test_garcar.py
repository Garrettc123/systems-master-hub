import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

MODULE = Path(__file__).parents[1] / "garcar.py"
spec = importlib.util.spec_from_file_location("garcar_sovereign", MODULE)
garcar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(garcar)

class ManifestTests(unittest.TestCase):
    def write(self, root, payload):
        path = Path(root) / "garcar.deploy.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def base(self):
        return {
            "name": "test-api",
            "build": [],
            "start": ["python", "app.py"],
            "port": 18080,
            "canary_port": 18081,
            "health": {"path": "/health"},
            "env_passthrough": []
        }

    def test_valid_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            self.write(temp, self.base())
            self.assertEqual(garcar.load_deploy(temp)["name"], "test-api")

    def test_rejects_shell_command_string(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = self.base()
            cfg["start"] = "python app.py"
            self.write(temp, cfg)
            with self.assertRaises(ValueError):
                garcar.load_deploy(temp)

    def test_rejects_same_ports(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = self.base()
            cfg["canary_port"] = cfg["port"]
            self.write(temp, cfg)
            with self.assertRaises(ValueError):
                garcar.load_deploy(temp)

    def test_rejects_unsafe_health_path(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = self.base()
            cfg["health"] = {"path": "/../secrets"}
            self.write(temp, cfg)
            with self.assertRaises(ValueError):
                garcar.load_deploy(temp)

    def test_rejects_secret_values_in_passthrough(self):
        with tempfile.TemporaryDirectory() as temp:
            cfg = self.base()
            cfg["env_passthrough"] = ["not a variable name"]
            self.write(temp, cfg)
            with self.assertRaises(ValueError):
                garcar.load_deploy(temp)

class CIManifestTests(unittest.TestCase):
    def test_ci_steps_must_be_argument_arrays(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "garcar.ci.json").write_text(json.dumps({"steps": ["python -m unittest"]}))
            with self.assertRaises(ValueError):
                garcar.load_ci(temp)

    def test_ci_secret_is_not_inherited_by_default(self):
        with patch.dict("os.environ", {"GARCAR_TEST_SECRET": "do-not-leak"}, clear=True):
            env = garcar.ci_environment([])
            self.assertNotIn("GARCAR_TEST_SECRET", env)

    def test_ci_secret_requires_explicit_name_allowlist(self):
        with patch.dict("os.environ", {"GARCAR_TEST_SECRET": "allowed-only-on-request"}, clear=True):
            env = garcar.ci_environment(["GARCAR_TEST_SECRET"])
            self.assertEqual(env["GARCAR_TEST_SECRET"], "allowed-only-on-request")

if __name__ == "__main__":
    unittest.main()
