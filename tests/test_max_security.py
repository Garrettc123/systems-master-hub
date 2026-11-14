import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from security.max_security import (
    MaxSecurityEngine, SecurityConfig, SecurityDenied,
)
from security.operation_gateway import ActionPolicy, ProtectedOperationGateway
from security.audit_checkpoint import create_checkpoint, verify_checkpoint


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


    def test_newline_in_path_is_denied_even_when_correctly_signed(self):
        for malformed in ("/safe\\r", "/safe\\n", "/safe\\x00", "/safe\\t"):
            with self.subTest(path=repr(malformed)):
                args = self.signed_args(nonce="a" * 32)
                args["path"] = malformed
                args["signature"] = self.engine.sign_request(
                    "POST", malformed, args["timestamp"], args["nonce"], args["body"]
                )
                with self.assertRaises(SecurityDenied):
                    self.engine.verify_request(**args)

    def test_invalid_identity_and_audit_event_fail_closed(self):
        for principal, action in ((None, "read"), (7, "read"), ("a", None), ("a", 7)):
            with self.subTest(principal=principal, action=action):
                with self.assertRaises(SecurityDenied):
                    self.engine.require_permission(principal, action)
        with self.assertRaises(SecurityDenied):
            self.engine.append_audit("bad", {"unsupported": set((1, 2))})
        with self.assertRaises(SecurityDenied):
            self.engine.append_audit(5, {})

    def test_deleted_middle_audit_record_is_detected(self):
        for number in range(3):
            self.engine.append_audit("event", {"n": number})
        with self.engine._connect() as db:
            db.execute("DELETE FROM security_audit WHERE sequence=2")
        self.assertFalse(self.engine.verify_audit_chain())

    def test_gateway_blocks_unapproved_and_unknown_operations(self):
        self.engine.grant_permission("operator", "read", admin_key=b"p" * 32)
        called = []
        gateway = ProtectedOperationGateway(
            self.engine, {"read": ActionPolicy()},
        )
        args = self.signed_args(nonce="u" * 32)
        with self.assertRaises(SecurityDenied):
            gateway.execute(**args, action="read", principal="operator",
                            rate_subject="client", operation=lambda receipt: called.append(receipt))
        with self.assertRaises(SecurityDenied):
            gateway.execute(**args, action="deploy", principal="operator",
                            rate_subject="client", operation=lambda receipt: called.append(receipt))
        self.assertEqual(called, [])

    def test_gateway_runs_only_authorized_local_callback(self):
        self.engine.grant_permission("operator", "read", admin_key=b"p" * 32)
        called = []
        gateway = ProtectedOperationGateway(self.engine, {"read": ActionPolicy(requires_approval=False)})
        args = self.signed_args(nonce="v" * 32)
        result = gateway.execute(
            **args, action="read", principal="operator", rate_subject="client",
            operation=lambda receipt: called.append(receipt) or "local-only",
        )
        self.assertEqual(result, "local-only")
        self.assertEqual(len(called), 1)
        with self.assertRaises(SecurityDenied):
            gateway.execute(
                **args, action="read", principal="operator", rate_subject="client",
                operation=lambda receipt: called.append(receipt),
            )
        self.assertEqual(len(called), 1)

    def test_gateway_bad_signature_blocks_callback(self):
        self.engine.grant_permission("operator", "read", admin_key=b"p" * 32)
        called = []
        gateway = ProtectedOperationGateway(self.engine, {"read": ActionPolicy(False)})
        args = self.signed_args(nonce="w" * 32)
        args["signature"] = "f" * 64
        with self.assertRaises(SecurityDenied):
            gateway.execute(
                **args, action="read", principal="operator", rate_subject="client",
                operation=lambda receipt: called.append(receipt),
            )
        self.assertFalse(called)

    def test_gateway_db_audit_failure_blocks_callback(self):
        self.engine.grant_permission("operator", "read", admin_key=b"p" * 32)
        called = []
        gateway = ProtectedOperationGateway(self.engine, {"read": ActionPolicy(False)})
        with self.engine._connect() as db:
            db.execute("DROP TABLE security_audit")
        with self.assertRaises(SecurityDenied):
            gateway.execute(
                **self.signed_args(nonce="x" * 32),
                action="read", principal="operator", rate_subject="client",
                operation=lambda receipt: called.append(receipt),
            )
        self.assertEqual(called, [])

    def test_gateway_requires_successful_independent_approval(self):
        self.engine.grant_permission("operator", "read", admin_key=b"p" * 32)
        called = []
        gateway = ProtectedOperationGateway(
            self.engine, {"read": ActionPolicy(True)},
            approval_verifier=lambda principal, action, body, approval:
                principal == "operator" and action == "read" and approval == "isolated-approved",
        )
        args = self.signed_args(nonce="y" * 32)
        with self.assertRaises(SecurityDenied):
            gateway.execute(
                **args, action="read", principal="operator", rate_subject="client",
                approval="wrong", operation=lambda receipt: called.append(receipt),
            )
        self.assertEqual(called, [])
        result = gateway.execute(
            **args, action="read", principal="operator", rate_subject="client",
            approval="isolated-approved",
            operation=lambda receipt: called.append(receipt) or "ok",
        )
        self.assertEqual(result, "ok")
        self.assertEqual(len(called), 1)



    def test_checkpoint_survives_append_and_detects_record_changes(self):
        self.engine.append_audit("first", {"n": 1})
        self.engine.append_audit("second", {"n": 2})
        checkpoint = create_checkpoint(self.engine, b"k" * 32, now=1000)
        self.assertTrue(verify_checkpoint(self.engine, b"k" * 32, checkpoint))
        self.engine.append_audit("third", {"n": 3})
        self.assertTrue(verify_checkpoint(self.engine, b"k" * 32, checkpoint))
        with self.engine._connect() as db:
            db.execute("UPDATE security_audit SET event='tampered' WHERE sequence=1")
        self.assertFalse(verify_checkpoint(self.engine, b"k" * 32, checkpoint))

    def test_checkpoint_detects_truncation_and_invalid_signatures(self):
        self.engine.append_audit("first", {"n": 1})
        self.engine.append_audit("second", {"n": 2})
        checkpoint = create_checkpoint(self.engine, b"k" * 32, now=1000)
        self.assertFalse(verify_checkpoint(self.engine, b"d" * 32, checkpoint))
        corrupt = {"payload": dict(checkpoint["payload"]), "signature": "0" * 64}
        self.assertFalse(verify_checkpoint(self.engine, b"k" * 32, corrupt))
        with self.engine._connect() as db:
            db.execute("DELETE FROM security_audit WHERE sequence=2")
        self.assertFalse(verify_checkpoint(self.engine, b"k" * 32, checkpoint))

    def test_approval_callback_not_called_for_unauthenticated_requests(self):
        self.engine.grant_permission("operator", "read", admin_key=b"p" * 32)
        approval_calls = []
        gateway = ProtectedOperationGateway(
            self.engine,
            {"read": ActionPolicy(True)},
            approval_verifier=lambda *items: approval_calls.append(items) or True,
        )
        args = self.signed_args(nonce="q" * 32)
        args["token"] = "incorrect"
        with self.assertRaises(SecurityDenied):
            gateway.execute(
                **args, action="read", principal="operator",
                rate_subject="client", operation=lambda receipt: None,
            )
        self.assertEqual(approval_calls, [])



    def test_permission_revoke_and_audited_grant(self):
        self.engine.grant_permission("operator", "read", admin_key=b"p" * 32)
        self.engine.require_permission("operator", "read")
        with self.assertRaises(SecurityDenied):
            self.engine.revoke_permission("operator", "read", admin_key=b"invalid")
        self.engine.require_permission("operator", "read")
        self.engine.revoke_permission("operator", "read", admin_key=b"p" * 32)
        with self.assertRaises(SecurityDenied):
            self.engine.require_permission("operator", "read")
        self.assertTrue(self.engine.verify_audit_chain())

    def test_permission_grant_rolls_back_if_audit_write_fails(self):
        with self.engine._connect() as db:
            db.execute("DROP TABLE security_audit")
        with self.assertRaises(SecurityDenied):
            self.engine.grant_permission("operator", "deploy", admin_key=b"p" * 32)
        with self.engine._connect() as db:
            record = db.execute(
                "SELECT 1 FROM security_permissions WHERE principal=? AND action=?",
                ("operator", "deploy"),
            ).fetchone()
        self.assertIsNone(record)



    def test_config_requires_distinct_keys(self):
        with self.assertRaises(ValueError):
            MaxSecurityEngine(SecurityConfig(
                database=str(Path(self.temp.name) / "badkeys.sqlite3"),
                bearer_token=b"a" * 32, signing_key=b"a" * 32,
                provisioning_key=b"p" * 32,
            ))

    def test_bad_audit_chain_blocks_authorization_before_callback(self):
        self.engine.grant_permission("operator", "read", admin_key=b"p" * 32)
        self.engine.append_audit("baseline", {"ok": True})
        with self.engine._connect() as db:
            db.execute("UPDATE security_audit SET event='tampered' WHERE sequence=1")
        calls = []
        gateway = ProtectedOperationGateway(
            self.engine, {"read": ActionPolicy(requires_approval=False)})
        with self.assertRaises(SecurityDenied):
            gateway.execute(
                **self.signed_args(nonce="c" * 32), action="read",
                principal="operator", rate_subject="client",
                operation=lambda receipt: calls.append(receipt),
            )
        self.assertEqual(calls, [])

    def test_checkpoint_rejects_reused_runtime_key(self):
        with self.assertRaises(SecurityDenied):
            create_checkpoint(self.engine, self.engine.config.signing_key)
        with self.assertRaises(SecurityDenied):
            verify_checkpoint(self.engine, self.engine.config.provisioning_key, {})


if __name__ == "__main__":
    unittest.main()
