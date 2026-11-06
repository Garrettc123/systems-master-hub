from pathlib import Path
from tempfile import TemporaryDirectory
import json
import os
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import github_ci_fallback as ci

class ExternalOperatorTests(unittest.TestCase):
    def test_repo_validation_no_dangerous_urls(self):
        for value in ('https://github.com/user/repo', '../repo', '-user/repo', 'user/repo;touch x', 'user//repo', 'user/repo name'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ci.repository_name(value)
        self.assertEqual(ci.repository_name('Garrettc123/systems-master-hub'), 'Garrettc123/systems-master-hub')

    def test_ref_validation(self):
        for value in ('../main', '-oops', 'a..b', 'a//b', 'main;rm', 'bad@{x}', 'abc.lock'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                ci.git_ref(value)
        self.assertEqual(ci.git_ref('fix/operator-manual-audit-20261106'), 'fix/operator-manual-audit-20261106')

    def test_suite_offline_creates_real_evidence(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)/'repo'
            root.mkdir()
            (root/'SYSTEMS-INVENTORY.json').write_text(json.dumps({'categories': {'a': {}}}))
            (root/'Makefile').write_text('help:\n\techo help\n')
            (root/'docker-compose.yml').write_text('services:\n  app:\n    image: alpine\n')
            (root/'run-all-omni.sh').write_text('#!/bin/bash\necho hi\n')
            out = Path(tmp)/'artifacts'
            rc = ci.main(['--root',str(root),'--output',str(out),'--actions','inventory-report,security-scan,dry-run-deploy'])
            self.assertEqual(rc,0)
            data = json.loads((out/'fallback-manifest.json').read_text())
            self.assertEqual(data['schema'],'garcar.external-ci.v1')
            self.assertEqual(len(data['actions']),3)
            self.assertTrue((out/'fallback-summary.md').is_file())
            hashes = json.loads((out/'fallback-checksums.json').read_text())
            self.assertEqual(hashes['files']['fallback-manifest.json'],ci.report_sha(out/'fallback-manifest.json'))
            self.assertFalse(data['deployed'])
            self.assertFalse(data['live_payment_verified'])

    def test_invalid_json_is_failure_not_fabricated_success(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)/'repo';root.mkdir()
            (root/'bad.json').write_text('{not json')
            out = Path(tmp)/'artifacts'
            rc=ci.main(['--root',str(root),'--output',str(out),'--actions','validate-all'])
            self.assertEqual(rc,1)
            manifest=json.loads((out/'fallback-manifest.json').read_text())
            self.assertEqual(manifest['status'],'failed')

    def test_token_is_not_passed_to_offline_checks(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo';root.mkdir()
            (root/'SYSTEMS-INVENTORY.json').write_text(json.dumps({'categories':{'x':{'p':{'repo_url':'https://github.com/Garrettc123/systems-master-hub'}}}}))
            out=Path(tmp)/'artifacts'
            with patch.dict(os.environ,{'GH_TOKEN':'fake_secret_probe'}):
                rc=ci.main(['--root',str(root),'--output',str(out),'--actions','check-external-repos'])
            self.assertEqual(rc,0)
            self.assertNotIn('fake_secret_probe',(out/'fallback-manifest.json').read_text())
            self.assertEqual(json.loads((out/'fallback-manifest.json').read_text())['status'],'warning')

    def test_publish_status_not_unintentionally_activated(self):
        with patch.object(ci, 'publish_status',side_effect=AssertionError('should not be called')):
            with TemporaryDirectory() as tmp:
                root=Path(tmp)/'repo';root.mkdir()
                out=Path(tmp)/'artifacts'
                self.assertEqual(ci.main(['--root',str(root),'--output',str(out),'--actions','security-scan']),0)

    def test_publish_status_fails_without_token(self):
        with patch.dict(os.environ,{},clear=True):
            self.assertEqual(ci.publish_status('Garrettc123/systems-master-hub','a'*40,{'status':'passed'})['sent'],False)

if __name__=='__main__':
    unittest.main()