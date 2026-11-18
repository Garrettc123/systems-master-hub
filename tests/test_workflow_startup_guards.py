"""Offline regression checks for safe GitHub Actions workflow startup."""
from pathlib import Path
import unittest
import yaml

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"


def load(name):
    text = (WORKFLOWS / name).read_text(encoding="utf-8")
    return yaml.load(text, Loader=yaml.BaseLoader), text


class TestWorkflowStartup(unittest.TestCase):
    def test_omega_has_executable_read_only_job(self):
        spec, content = load("omega-nightly.yml")
        self.assertEqual(spec["permissions"], {"contents": "read"})
        self.assertIn("schedule", spec["on"])
        self.assertIn("workflow_dispatch", spec["on"])
        self.assertIn("repository-evidence", spec["jobs"])
        self.assertIn("checkout", content)
        self.assertNotIn("git push", content)
        self.assertNotIn("createDispatchEvent", content)
        self.assertNotIn("secrets.", content)
        self.assertNotIn("wallet_sign", content)

    def test_daily_evolution_valid_permissions_and_approval_bound_write(self):
        spec, content = load("daily-evolution-v2.yml")
        self.assertNotIn("pull_requests", spec["permissions"])
        self.assertEqual(spec["permissions"]["pull-requests"], "read")
        write_job = spec["jobs"]["create-upgrade-prs"]
        self.assertEqual(write_job["permissions"]["pull-requests"], "write")
        self.assertIn("workflow_dispatch", write_job["if"])
        self.assertIn("dry_run", write_job["if"])
        self.assertIn("--dry-run", content)
        self.assertNotIn("gh issue create", content)

    def test_daily_summary_jq_and_skipped_job_handling(self):
        spec, content = load("daily-evolution-v2.yml")
        self.assertIn("needs['discover-and-plan'].result", spec["jobs"]["notify"]["if"])
        self.assertIn("to_entries[]", content)
        self.assertIn("jq -r", content)
        self.assertNotIn('to_entries[] | "- \\(.key): \\(.value)""', content)


if __name__ == "__main__":
    unittest.main()
