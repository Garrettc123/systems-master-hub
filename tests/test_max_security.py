import tempfile
import unittest
from pathlib import Path

from security.max_security import (
    MaxSecurityEngine, SecurityConfig, SecurityDenied,
)


class MaxSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.engine = MaxSecurityEngine(SecurityConfig(
            database=str(Path(self.temp.name) / "security.sqlite3"),
            bearer_token=b"b" * 32,
            signing_key=b"s" * 32,
            rate_limit=2,
            rate_window_seconds=60,
        ))

    def tearDown(self):
        self.temp.cleanup()

    def test_authentication_uses_configured_token(self):
        self.assertTrue(self.engine.authenticate("b" * 32))
        self.assertFalse(self.engine.authenticate("wrong"))

    def test_signed_request_and_replay_rejection(self):
        body = b'{"operation":"read"}'
        nonce = "n" * 32
        signature = self.engine.sign_request("POST", "/safe", 1000, nonce, body)
        args = dict(token="b" * 32, signature=signature, method="POST",
                    path="/safe", timestamp=1000, nonce=nonce, body=body, now=1000)
        self.engine.verify_request(**args)
        with self.assertRaises(SecurityDenied):
            self.engine.verify_request(**args)

    def test_bad_signature_is_denied(self):
        with self.assertRaises(SecurityDenied):
            self.engine.verify_request(
                token="b" * 32, signature="0" * 64, method="GET",
                path="/", timestamp=1000, nonce="x" * 32, body=b"", now=1000,
            )

    def test_default_deny_and_explicit_grant(self):
        with self.assertRaises(SecurityDenied):
            self.engine.require_permission("operator", "deploy")
        self.engine.grant_permission("operator", "read")
        self.engine.require_permission("operator", "read")

    def test_rate_limit(self):
        self.engine.consume_rate_limit("client", now=120)
        self.engine.consume_rate_limit("client", now=121)
        with self.assertRaises(SecurityDenied):
            self.engine.consume_rate_limit("client", now=122)

    def test_audit_chain_detects_tampering(self):
        self.engine.append_audit("test", {"ok": True})
        self.assertTrue(self.engine.verify_audit_chain())
        with self.engine._connect() as db:
            db.execute("UPDATE security_audit SET event='altered' WHERE sequence=1")
        self.assertFalse(self.engine.verify_audit_chain())


if __name__ == "__main__":
    unittest.main()
