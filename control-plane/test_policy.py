import base64
import hashlib
import hmac
import json
import sys
import tempfile
import time
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
    def test_real_estate_requires_human_approval(self):
        scope=resolve("Garrettc123/garcar-rhns-core",self.policy)
        self.assertTrue(scope["human_approval_required"])
        self.assertIn("realestate.offer.submit",scope["mcp_tools"])

class ApprovalTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0,str(ROOT/"mcp"))
        import approval
        self.approval=approval; self.approval.KEY=b"test-key"
        self.temp=tempfile.TemporaryDirectory(); self.approval.REPLAY_FILE=Path(self.temp.name)/"used.json"

    def tearDown(self): self.temp.cleanup()

    def token(self,claims):
        encode=lambda value: base64.urlsafe_b64encode(json.dumps(value,separators=(",",":")).encode()).rstrip(b"=").decode()
        header=encode({"alg":"HS256","typ":"JWT"}); payload=encode(claims); signed=f"{header}.{payload}"
        signature=base64.urlsafe_b64encode(hmac.new(self.approval.KEY,signed.encode(),hashlib.sha256).digest()).rstrip(b"=").decode()
        return f"{signed}.{signature}"

    def test_digest_mutation_and_replay_are_rejected(self):
        args={"listing_id":"123","amount":250000}; digest=self.approval.canonical_digest("Garrettc123/garcar-rhns-core","realestate","realestate.offer.submit",args)
        token=self.token({"iat":int(time.time()),"exp":int(time.time())+60,"actor":"broker@example.com","jti":"once","digest":digest})
        self.approval.verify_approval(token,"Garrettc123/garcar-rhns-core","realestate","realestate.offer.submit",args)
        with self.assertRaisesRegex(ValueError,"already used"): self.approval.verify_approval(token,"Garrettc123/garcar-rhns-core","realestate","realestate.offer.submit",args)
        changed=self.token({"iat":int(time.time()),"exp":int(time.time())+60,"actor":"broker@example.com","jti":"changed","digest":digest})
        with self.assertRaisesRegex(ValueError,"does not match"): self.approval.verify_approval(changed,"Garrettc123/garcar-rhns-core","realestate","realestate.offer.submit",{"listing_id":"123","amount":300000})

if __name__=="__main__": unittest.main()
