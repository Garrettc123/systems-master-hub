"""No-network regression tests for the GitHub Actions-independent supervisor."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import github_ci_supervisor as supervisor

SHA = 'a' * 40


class SupervisorTests(unittest.TestCase):
    def test_network_failure_never_returns_stale_green(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / 'supervisor-state.json').write_text(json.dumps(
                {'status': 'passed', 'last_validated_status': 'passed', 'remote_sha': SHA}))
            def broken(*args):
                raise RuntimeError('offline')
            result = supervisor.one_cycle('Garrettc123/systems-master-hub',
                                          'main', root, discover=broken)
            self.assertEqual(result['status'], 'network_error')
            self.assertFalse(result['remote_sha_verified'])

    def test_unchanged_revision_skips_clone(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / 'supervisor-state.json').write_text(json.dumps(
                {'status': 'passed', 'last_validated_status': 'passed', 'remote_sha': SHA}))
            with patch.object(supervisor.subprocess, 'run', side_effect=AssertionError('clone')):
                result = supervisor.one_cycle('Garrettc123/systems-master-hub', 'main', root,
                                              discover=lambda *args: SHA)
            self.assertEqual(result['status'], 'unchanged')
            self.assertFalse(result['validation_executed'])

    def test_repeated_skip_preserves_last_validated_status(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            (root / 'supervisor-state.json').write_text(json.dumps(
                {'status': 'unchanged', 'last_validated_status': 'passed', 'remote_sha': SHA}))
            with patch.object(supervisor.subprocess, 'run', side_effect=AssertionError('clone')):
                result = supervisor.one_cycle('Garrettc123/systems-master-hub', 'main', root,
                                              discover=lambda *args: SHA)
            self.assertEqual(result['status'], 'unchanged')

    def test_invalid_or_missing_report_never_green(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            process = supervisor.subprocess.CompletedProcess([], 2, stdout=b'', stderr=b'')
            with patch.object(supervisor.subprocess, 'run', return_value=process):
                result = supervisor.one_cycle('Garrettc123/systems-master-hub', 'main', root,
                                              discover=lambda *args: SHA)
            self.assertNotEqual(result['status'], 'passed')
            self.assertIsNone(result['report_sha256'])

    def test_failed_check_is_reported(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            def failing(cmd, **kwargs):
                (root / SHA / 'fallback-manifest.json').write_text(json.dumps(
                    {'status': 'failed', 'git': {'git_sha': SHA}}))
                return supervisor.subprocess.CompletedProcess(cmd, 1, stdout=b'', stderr=b'')
            with patch.object(supervisor.subprocess, 'run', side_effect=failing):
                result = supervisor.one_cycle('Garrettc123/systems-master-hub', 'main', root,
                                              discover=lambda *args: SHA)
            self.assertEqual(result['status'], 'failed')
            self.assertTrue(result['report_sha256'])

    def test_revision_race_never_masquerades_as_success(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            def raced(cmd, **kwargs):
                (root / SHA / 'fallback-manifest.json').write_text(json.dumps(
                    {'status': 'passed', 'git': {'git_sha': 'b' * 40}}))
                return supervisor.subprocess.CompletedProcess(cmd, 0, stdout=b'', stderr=b'')
            with patch.object(supervisor.subprocess, 'run', side_effect=raced):
                result = supervisor.one_cycle('Garrettc123/systems-master-hub', 'main', root,
                                              discover=lambda *args: SHA)
            self.assertEqual(result['status'], 'revision_mismatch')

    def test_financial_secrets_not_passed_to_checks(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            def checked(cmd, **kwargs):
                self.assertNotIn('GH_TOKEN', kwargs['env'])
                self.assertNotIn('AWS_SECRET_ACCESS_KEY', kwargs['env'])
                self.assertNotIn('STRIPE_SECRET_KEY', kwargs['env'])
                (root / SHA / 'fallback-manifest.json').write_text(json.dumps(
                    {'status': 'passed', 'git': {'git_sha': SHA}}))
                return supervisor.subprocess.CompletedProcess(cmd, 0, stdout=b'', stderr=b'')
            with patch.dict(supervisor.os.environ, {
                    'GH_TOKEN': 'dummy-token', 'AWS_SECRET_ACCESS_KEY': 'not-to-propagate',
                    'STRIPE_SECRET_KEY': 'not-to-propagate'}):
                with patch.object(supervisor.subprocess, 'run', side_effect=checked):
                    result = supervisor.one_cycle('Garrettc123/systems-master-hub', 'main', root,
                                                  discover=lambda *args: SHA)
            self.assertEqual(result['status'], 'passed')


if __name__ == '__main__':
    unittest.main()
