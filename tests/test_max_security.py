import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
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
            provisioning_key=b"p" * 32,
            rate_limit=2,
            rate_window_seconds=60,
        ))

    def tearDown(self):
        self.temp.cleanup()

    def signed_args(self, nonce="n" * 32, timestamp=1000):
        body = b'{"operation":"read"}'
        return dict(
            token="b" * 32,
            signature=self.engine.sign_request("POST", "/safe", timestamp, nonce, body),
            method="POST", path="/safe", timestamp=timestamp,
            nonce=nonce, body=body, now=timestamp,
        )

    def test_authentication_uses_configured_token(self):
        self.assertTrue(self.engine.authenticate("b" * 32))
        self.assertFalse(self.engine.authenticate("wrong"))
        self.assertFalse(self.engine.authenticate(None))

    def test_signed_request_and_replay_rejection(self):
        args = self.signed_args()
        self.engine.verify_request(**args)
        with self.assertRaises(SecurityDenied):
            self.engine.verify_request(**args)

    def test_bad_signature_is_denied(self):
        args = self.signed_args()
        args["signature"] = "0" * 64
        with self.assertRaises(SecurityDenied):
            self.engine.verify_request(**args)

    def test_malformed_timestamp_types_and_ranges_are_denied(self):
        for invalid in (None, "1000", 1000.5, True, -1, 253402300800):
            with self.subTest(timestamp=invalid):
                args = self.signed_args()
                args["timestamp"] = invalid
                with self.assertRaises(SecurityDenied):
                    self.engine.verify_request(**args)

    def test_invalid_method_path_and_nonce_are_denied(self):
        for field, invalid in (
            ("method", "GET\nPOST"), ("method", "GÉT"),
            ("path", "/safe\r\nX-Evil: 1"), ("path", "relative"),
            ("nonce", "short"), ("nonce", "x" * 129),
        ):
            with self.subTest(field=field, invalid=invalid):
                args = self.signed_args()
                args[field] = invalid
                with self.assertRaises(SecurityDenied):
                    self.engine.verify_request(**args)

    def test_permission_provisioning_requires_separate_admin_key(self):
        with self.assertRaises(SecurityDenied):
            self.engine.grant_permission("operator", "read", admin_key=b"x" * 32)
        with self.assertRaises(SecurityDenied):
            self.engine.require_permission("operator", "read")
        self.engine.grant_permission("operator", "read", admin_key=b"p" * 32)
        self.engine.require_permission("operator", "read")

    def test_default_deny(self):
        with self.assertRaises(SecurityDenied):
            self.engine.require_permission("operator", "deploy")

    def test_rate_limit(self):
        self.engine.consume_rate_limit("client", now=120)
        self.engine.consume_rate_limit("client", now=121)
        with self.assertRaises(SecurityDenied):
            self.engine.consume_rate_limit("client", now=122)

    def test_concurrent_nonce_reuse_is_accepted_once(self):
        args = self.signed_args()
        def attempt(_):
            try:
                self.engine.verify_request(**args)
                return "accepted"
            except SecurityDenied:
                return "denied"
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(attempt, range(8)))
        self.assertEqual(outcomes.count("accepted"), 1)
        self.assertEqual(outcomes.count("denied"), 7)

    def test_concurrent_rate_limit_is_atomic(self):
        def attempt(_):
            try:
                self.engine.consume_rate_limit("parallel-client", now=180)
                return "accepted"
            except SecurityDenied:
                return "denied"
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(attempt, range(8)))
        self.assertEqual(outcomes.count("accepted"), 2)
        self.assertEqual(outcomes.count("denied"), 6)

    def test_authorize_operation_requires_every_gate(self):
        self.engine.grant_permission("operator", "read", admin_key=b"p" * 32)
        args = self.signed_args(nonce="z" * 32)
        receipt = self.engine.authorize_operation(
            **args, principal="operator", action="read",
            rate_subject="operator-client",
        )
        self.assertEqual(len(receipt), 64)
        self.assertTrue(self.engine.verify_audit_chain())

    def test_audit_chain_detects_tampering(self):
        self.engine.append_audit("test", {"ok": True})
        self.assertTrue(self.engine.verify_audit_chain())
        with self.engine._connect() as db:
            db.execute("UPDATE security_audit SET event='altered' WHERE sequence=1")
        self.assertFalse(self.engine.verify_audit_chain())


if __name__ == "__main__":
    unittest.main()
