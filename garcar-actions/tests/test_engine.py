import tempfile
import unittest
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from pathlib import Path
from garcar_actions import engine

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db, self.old_ws = engine.DB_PATH, engine.WORKSPACE
        engine.DB_PATH = Path(self.tmp.name) / "actions.db"
        engine.WORKSPACE = Path(self.tmp.name).resolve()
    def tearDown(self):
        engine.DB_PATH, engine.WORKSPACE = self.old_db, self.old_ws
        self.tmp.cleanup()
    def test_allowlist_rejects_arbitrary_commands(self):
        with self.assertRaises(ValueError):
            engine.enqueue("shell", str(engine.WORKSPACE))
    def test_path_escape_is_rejected(self):
        with self.assertRaises(ValueError):
            engine.enqueue("python_tests", str(Path(self.tmp.name).parent))
    def test_enqueue_and_audit_verify(self):
        job_id = engine.enqueue("python_tests", str(engine.WORKSPACE))
        with engine.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            valid, count = engine.verify_audit(db)
        self.assertEqual(row["status"], "queued")
        self.assertTrue(valid)
        self.assertEqual(count, 1)
    def test_audit_tamper_is_detected(self):
        engine.enqueue("git_status", str(engine.WORKSPACE))
        with engine.connect() as db:
            db.execute("UPDATE audit SET payload='{}' WHERE seq=1")
            valid, _ = engine.verify_audit(db)
        self.assertFalse(valid)

    def test_relative_path_uses_configured_workspace(self):
        job_id = engine.enqueue("python_tests")
        with engine.connect() as db:
            row = db.execute("SELECT repo_path FROM jobs WHERE id=?", (job_id,)).fetchone()
        self.assertEqual(row["repo_path"], str(engine.WORKSPACE))

    def test_real_worker_does_not_inherit_credentials_or_home(self):
        source = '''import os, unittest
class ChildTest(unittest.TestCase):
    def test_environment(self):
        for key in ("GARCAR_ACTIONS_TOKEN", "AWS_SECRET_ACCESS_KEY", "PYTHONPATH"):
            self.assertNotIn(key, os.environ)
        self.assertTrue(os.path.basename(os.environ["HOME"]).startswith("garcar-job-"))
        self.assertEqual(os.environ["CI"], "1")
'''
        (engine.WORKSPACE / "test_child.py").write_text(source)
        job_id = engine.enqueue("python_tests")
        with patch.dict(os.environ, {"GARCAR_ACTIONS_TOKEN": "test-only-sentinel",
                                   "AWS_SECRET_ACCESS_KEY": "test-only-sentinel",
                                   "PYTHONPATH": "/untrusted"}):
            self.assertTrue(engine.run_one())
        with engine.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            self.assertEqual(row["status"], "succeeded", row["output"])
            self.assertIn("Ran 1 test", row["output"])
            self.assertEqual(engine.verify_audit(db), (True, 3))
        self.assertFalse(engine.run_one())

    def test_replaced_workspace_is_rejected_before_execution(self):
        target = engine.WORKSPACE / "checkout"
        target.mkdir()
        job_id = engine.enqueue("python_tests", "checkout")
        target.rmdir()
        target.symlink_to(engine.WORKSPACE.parent, target_is_directory=True)
        with patch.object(engine, "execute") as run:
            engine.run_one()
            run.assert_not_called()
        with engine.connect() as db:
            row = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()
            self.assertEqual(row["status"], "failed")
            self.assertEqual(engine.verify_audit(db), (True, 3))

    def test_worker_records_actual_test_failure(self):
        (engine.WORKSPACE / "test_child.py").write_text(
            "import unittest\nclass Failure(unittest.TestCase):\n    def test_failure(self): self.fail('expected failure')\n")
        job_id = engine.enqueue("python_tests")
        engine.run_one()
        with engine.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        self.assertEqual(row["status"], "failed")
        self.assertNotEqual(row["exit_code"], 0)

    def test_empty_test_suite_fails(self):
        job_id = engine.enqueue("python_tests")
        engine.run_one()
        with engine.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["exit_code"], 5)
        self.assertIn("NO_TESTS", row["output"])

    def test_tests_directory_is_discovered(self):
        directory = engine.WORKSPACE / "tests"
        directory.mkdir()
        (directory / "test_sample.py").write_text(
            "import unittest\nclass Sample(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n")
        job_id = engine.enqueue("python_tests")
        engine.run_one()
        with engine.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        self.assertEqual(row["status"], "succeeded", row["output"])
        self.assertIn("Ran 1 test", row["output"])

    def test_idempotency_reuses_job_and_rejects_conflict(self):
        first = engine.enqueue("python_tests", idempotency_key="test-request-1")
        self.assertEqual(first, engine.enqueue("python_tests", idempotency_key="test-request-1"))
        with self.assertRaises(ValueError):
            engine.enqueue("python_compile", idempotency_key="test-request-1")
        with engine.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 1)
            self.assertEqual(engine.verify_audit(db), (True, 1))

    def test_pending_quota_preserves_existing_queue(self):
        with patch.object(engine, "MAX_PENDING", 1):
            engine.enqueue("python_tests")
            with self.assertRaises(engine.QueueFull):
                engine.enqueue("python_tests")
        with engine.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 1)

    def test_audit_tampering_blocks_submit_and_execution(self):
        engine.enqueue("python_tests")
        with engine.connect() as db:
            db.execute("UPDATE audit SET payload='{}' WHERE seq=1")
        with self.assertRaises(engine.AuditCorrupt):
            engine.enqueue("python_tests")
        with patch.object(engine, "execute") as run:
            with self.assertRaises(engine.AuditCorrupt):
                engine.run_one()
            run.assert_not_called()

    def test_interrupted_job_requires_recovery_and_is_never_replayed(self):
        job_id = engine.enqueue("python_tests")
        with engine.connect() as db:
            db.execute("UPDATE jobs SET status='running' WHERE id=?", (job_id,))
        with self.assertRaises(engine.RecoveryRequired):
            engine.run_one()
        self.assertEqual(engine.recover_interrupted(), 1)
        self.assertFalse(engine.run_one())
        with engine.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            self.assertEqual(row["status"], "failed")
            self.assertEqual(row["exit_code"], 130)
            self.assertEqual(engine.verify_audit(db), (True, 2))

    def test_concurrent_worker_cannot_claim_job(self):
        engine.enqueue("python_tests")
        with engine.worker_lock():
            with self.assertRaises(engine.WorkerBusy):
                engine.run_one()
        with engine.connect() as db:
            self.assertEqual(db.execute("SELECT status FROM jobs").fetchone()[0], "queued")

    def test_concurrent_retries_create_only_one_job_and_audit_event(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            ids = list(pool.map(lambda _: engine.enqueue("python_tests", idempotency_key="concurrent-retry"), range(12)))
        self.assertEqual(len(set(ids)), 1)
        with engine.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 1)
            self.assertEqual(engine.verify_audit(db), (True, 1))

    def test_v01_upgrade_preserves_existing_job_and_audit(self):
        # Build an old schema by removing only the newly introduced empty columns.
        job_id = engine.enqueue("python_tests")
        with sqlite3.connect(engine.DB_PATH) as db:
            before = db.execute("SELECT * FROM audit").fetchall()
            db.execute("DROP INDEX jobs_idempotency")
            for column in ("idempotency_key", "source_path", "source_sha256"):
                db.execute(f"ALTER TABLE jobs DROP COLUMN {column}")
        with engine.connect() as db:
            self.assertEqual([tuple(row) for row in db.execute("SELECT * FROM audit")], before)
            self.assertEqual(db.execute("SELECT id FROM jobs").fetchone()[0], job_id)
            columns = {row["name"] for row in db.execute("PRAGMA table_info(jobs)")}
            self.assertTrue({"idempotency_key", "source_path", "source_sha256"} <= columns)
            self.assertEqual(engine.verify_audit(db), (True, 1))

if __name__ == "__main__":
    unittest.main()
