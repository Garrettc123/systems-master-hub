import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT))
from resolve_policy import load_policy, resolve

class PolicyTests(unittest.TestCase):
    def setUp(self): self.policy=load_policy()
    def test_unknown_repo_is_denied(self):
        scope=resolve("Garrettc123/new-repository",self.policy)
        self.assertFalse(scope["managed"]); self.assertEqual(scope["secrets"],[]); self.assertEqual(scope["mcp_tools"],[])
    def test_public_static_has_no_access(self):
        policy=json.loads(json.dumps(self.policy)); policy["repositories"]["website"]="public-static"
        scope=resolve("Garrettc123/website",policy)
        self.assertEqual(scope["secrets"],[]); self.assertEqual(scope["mcp_servers"],[])
    def test_control_credentials_stay_in_hub(self):
        for name,class_name in self.policy["repositories"].items():
            if name=="systems-master-hub": continue
            secrets=self.policy["classes"][class_name]["secrets"]
            self.assertNotIn("GHPAT",secrets); self.assertNotIn("VAULT_SECRET_ID",secrets)
    def test_revenue_is_read_only_by_default(self):
        scope=resolve("Garrettc123/garcar-rhns-core",self.policy)
        self.assertIn("stripe.payments.read",scope["mcp_tools"])
        self.assertNotIn("stripe.checkout.create",scope["mcp_tools"])

if __name__=="__main__": unittest.main()
