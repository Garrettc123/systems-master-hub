import importlib.util
import json
import tempfile
import unittest
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

if __name__ == "__main__":
    unittest.main()
