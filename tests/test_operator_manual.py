from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import operator_manual as op

class ManualOperatorTests(unittest.TestCase):
    def test_manual_action_never_changes_repo(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            (root/'Makefile').write_text('run:\n\techo hello\n')
            (root/'docker-compose.yml').write_text('services:\n  web:\n    image: nginx\n')
            (root/'run-all-omni.sh').write_text('echo hi\n')
            before={p.name:p.read_bytes() for p in root.iterdir()}
            output=root/'out'
            op.main(['dry-run-deploy','--root',str(root),'--output',str(output)])
            self.assertEqual(before,{p.name:p.read_bytes() for p in root.iterdir() if p.is_file()})
    def test_json_validation_failure_is_nonzero(self):
        with TemporaryDirectory() as td:
            root=Path(td);(root/'bad.json').write_text('{bad')
            output=root/'out'
            self.assertEqual(op.main(['validate-all','--root',str(root),'--output',str(output)]),1)
            report=json.loads((output/'operator-report.json').read_text())
            self.assertEqual(report['status'],'failed')
            self.assertTrue(any('bad.json' in s for s in report['errors']))
    def test_inventory_claims_not_reported_verified(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            data = {'overview': {'total_repositories': 900, 'last_updated': '2025-01-01'}, 'categories': {'group': {'foo': {'repo_url': 'https://github.com/a/b'}}}}
            (root/'SYSTEMS-INVENTORY.json').write_text(json.dumps(data))
            output=root/'out'
            self.assertEqual(op.main(['inventory-report','--root',str(root),'--output',str(output)]),0)
            report=json.loads((output/'operator-report.json').read_text())
            self.assertEqual(report['totals']['distinct_linked_repos'],1)
            self.assertEqual(report['inventory_overview_claims']['declared_total_repositories'],900)
    def test_security_hides_secret_values(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            key='sk_live_'+'Z'*40
            (root/'file.py').write_text('secret='+key+'\n')
            output=root/'out'
            self.assertEqual(op.main(['security-scan','--root',str(root),'--output',str(output)]),0)
            self.assertNotIn(key,(output/'operator-report.json').read_text())
            self.assertEqual(json.loads((output/'operator-report.json').read_text())['totals']['possible_secret_matches'],1)
    def test_external_inaccessible_does_not_mean_repo_missing(self):
        with TemporaryDirectory() as td:
            root=Path(td)
            data = {'categories': {'group': {'foo': {'repo_url': 'https://github.com/Garrettc123/private-example'}}}}
            (root/'SYSTEMS-INVENTORY.json').write_text(json.dumps(data))
            out=root/'out'
            with patch.dict('os.environ',{'GH_TOKEN':'testing'}),patch.object(op.subprocess,'run',return_value=type('R',(),{'returncode':1})()):
                self.assertEqual(op.main(['check-external-repos','--root',str(root),'--output',str(out)]),0)
            report=json.loads((out/'operator-report.json').read_text())
            self.assertEqual(report['totals']['unverified_or_inaccessible'],1)
            self.assertEqual(report['status'],'warning')
            self.assertNotIn('non-existent',(out/'operator-report.md').read_text())

if __name__=='__main__':unittest.main()
