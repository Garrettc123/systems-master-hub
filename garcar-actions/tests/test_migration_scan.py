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

    def test_does_not_follow_symlinked_workflow_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            other = root / "outside"
            (other / "workflows").mkdir(parents=True)
            (other / "workflows/ci.yml").write_text("name: external")
            (root / ".github").symlink_to(other, target_is_directory=True)
            self.assertEqual(scan(root)["workflow_count"], 0)

    def test_list_form_self_hosted_runner_requires_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / ".github/workflows"
            directory.mkdir(parents=True)
            (directory / "ci.yml").write_text("runs-on: [self-hosted, linux]\n")
            self.assertEqual(scan(root)["workflows"][0]["classification"], "host_isolation_review")

    def test_privileged_trigger_requires_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = root / ".github/workflows"
            directory.mkdir(parents=True)
            (directory / "ci.yml").write_text("on: pull_request_target\nsteps:\n  - run: python check.py\n")
            report = scan(root)["workflows"][0]
            self.assertEqual(report["classification"], "approval_required")
            self.assertIn("shell_execution", report["risk_flags"])

if __name__ == "__main__":
    unittest.main()
