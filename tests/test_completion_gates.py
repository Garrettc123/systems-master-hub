import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("completion_gates", Path(__file__).resolve().parents[1] / "scripts/full_stack_completion.py")
completion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(completion)


class CompletionGateTests(unittest.TestCase):
    def test_empty_or_skipped_evidence_is_not_completion(self):
        for stages in ([], [{"status": "skipped"}]):
            self.assertEqual(completion.completion_outcome(stages, []), ("software_evidence_missing", "incomplete", 2))

    def test_failed_software_cannot_be_overridden_by_local_only(self):
        result, status, code = completion.completion_outcome([{"status": "failed"}], [], local_only=True)
        self.assertEqual((result, status, code), ("software_checks_failed", "failed", 1))

    def test_unavailable_host_identity_check_cannot_count_as_pass(self):
        for local in (False, True):
            result, status, code = completion.completion_outcome([{"status": "passed"}, {"status": "blocked"}], [], local)
            self.assertEqual(status, "incomplete_host_check")
            self.assertEqual(code, 2)
            self.assertIn("blocked", result)

    def test_production_blockers_remain_visible_in_local_validation(self):
        for local, expected_code in ((False, 2), (True, 0)):
            result, status, code = completion.completion_outcome([{"status": "passed"}], [{"code": "missing_host"}], local)
            self.assertEqual(result, "local_canary_passed_production_blocked")
            self.assertEqual(status, "passed")
            self.assertEqual(code, expected_code)

    def test_only_all_passed_without_blockers_reports_completion(self):
        self.assertEqual(completion.completion_outcome([{"status": "passed"}], []), ("passed", "passed", 0))
