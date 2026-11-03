import tempfile
import unittest
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

if __name__ == "__main__":
    unittest.main()
