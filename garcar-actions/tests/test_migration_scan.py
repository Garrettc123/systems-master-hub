import tempfile
import unittest
from pathlib import Path
from garcar_actions.migration.scan import scan

class MigrationScanTests(unittest.TestCase):
    def test_classifies_revenue_and_deploy_workflow_as_restricted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wf = root / ".github/workflows/revenue.yml"
            wf.parent.mkdir(parents=True)
            wf.write_text("run: python revenue_loop.py\n# stripe payment\n", encoding="utf-8")
            result = scan(root)
            self.assertEqual(result["workflow_count"], 1)
            self.assertEqual(result["workflows"][0]["classification"], "restricted_business_action")
            self.assertIn("financial_or_commerce", result["workflows"][0]["risk_flags"])
    def test_does_not_follow_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wfdir = root / ".github/workflows"
            wfdir.mkdir(parents=True)
            outside = root / "outside.yml"
            outside.write_text("name: hidden", encoding="utf-8")
            (wfdir / "linked.yml").symlink_to(outside)
            result = scan(root)
            self.assertEqual(result["workflow_count"], 0)
    def test_read_only_workflow_is_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wfdir = root / ".github/workflows"
            wfdir.mkdir(parents=True)
            (wfdir / "ci.yml").write_text("name: CI\nrun: python -m unittest\n", encoding="utf-8")
            result = scan(root)
            self.assertEqual(result["workflows"][0]["classification"], "read_only_candidate")
            self.assertEqual(len(result["workflows"][0]["sha256"]), 64)

if __name__ == "__main__":
    unittest.main()
