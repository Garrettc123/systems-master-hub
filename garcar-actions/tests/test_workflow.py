import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from garcar_actions import engine
from garcar_actions.hub_check import REQUIRED, validate
from garcar_actions.migration.workflow import plan


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db, self.old_ws = engine.DB_PATH, engine.WORKSPACE
        engine.WORKSPACE = Path(self.tmp.name).resolve()
        engine.DB_PATH = engine.WORKSPACE / "state/actions.db"

    def tearDown(self):
        engine.DB_PATH, engine.WORKSPACE = self.old_db, self.old_ws
        self.tmp.cleanup()

    def create_hub(self):
        for name in REQUIRED:
            path = engine.WORKSPACE / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}" if path.suffix == ".json" else "test fixture\n")

    def test_native_structure_check_rejects_malformed_json(self):
        self.create_hub()
        self.assertTrue(validate(engine.WORKSPACE)["valid"])
        (engine.WORKSPACE / "bad.json").write_text("{invalid")
        report = validate(engine.WORKSPACE)
        self.assertFalse(report["valid"])
        self.assertIn("bad.json", report["errors"][0])

    def test_native_structure_check_records_missing_files(self):
        report = validate(engine.WORKSPACE)
        self.assertFalse(report["valid"])
        self.assertEqual(len(report["errors"]), len(REQUIRED))

    def test_workflow_source_change_blocks_execution(self):
        source = engine.WORKSPACE / "workflow.yml"
        source.write_text("name: reviewed\n")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        job_id = engine.enqueue("hub_structure", source_path="workflow.yml", source_sha256=digest)
        source.write_text("name: changed\n")
        with patch.object(engine, "execute") as execute:
            engine.run_one()
            execute.assert_not_called()
        with engine.connect() as db:
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            self.assertEqual(row["status"], "failed")
            self.assertIn("Workflow source changed", row["output"])
            self.assertEqual(engine.verify_audit(db), (True, 3))

    def test_plan_is_read_only_and_checks_actual_pinned_source(self):
        repo = Path(__file__).resolve().parents[2]
        source = repo / ".github/workflows/ci.yml"
        target = engine.WORKSPACE / ".github/workflows/ci.yml"
        target.parent.mkdir(parents=True)
        target.write_bytes(source.read_bytes())
        report = plan()
        self.assertTrue(report["source_verified"])
        self.assertEqual(report["status"], "planned_not_executed")
        self.assertFalse(engine.DB_PATH.exists())
        target.write_text("changed")
        with self.assertRaises(ValueError):
            plan()

    def test_source_pin_cannot_escape_checkout(self):
        with self.assertRaises(ValueError):
            engine.enqueue("hub_structure", source_path="../outside.yml", source_sha256="0" * 64)
