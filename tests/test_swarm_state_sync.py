"""Offline tests for redacted public telemetry; no GitHub or external requests."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import sync_to_master_hub as sync

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=timezone.utc)


def fixture(path: Path, *, omit_dlq=False, bad_schema=False):
    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        if bad_schema:
            conn.execute("CREATE TABLE task_queue (irrelevant TEXT)")
        else:
            conn.execute("CREATE TABLE task_queue (status TEXT)")
            conn.executemany("INSERT INTO task_queue(status) VALUES (?)", [
                ("pending",), ("running",), ("pending",),
                ("person@example.com",), (None,),
            ])
        conn.execute(
            "CREATE TABLE event_ledger "
            "(event_id TEXT, event_type TEXT, status TEXT, timestamp TEXT)"
        )
        conn.executemany(
            "INSERT INTO event_ledger VALUES (?, ?, ?, ?)", [
                ("sensitive-event-1234", "private-customer-record", "failed",
                 "2026-11-17T11:00:00Z"),
                ("private-wallet-reference", "onchain-secret", "completed",
                 "2026-11-17T11:01:00Z"),
            ]
        )
        if not omit_dlq:
            conn.execute("CREATE TABLE dead_letter_quarantine (id INTEGER)")
            conn.executemany(
                "INSERT INTO dead_letter_quarantine VALUES (?)", [(1,), (2,)]
            )


class TestPublicSnapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.db = self.base / "garcar_forge_operational.db"
        self.repo = self.base / "systems-master-hub"
        self.repo.mkdir()
        (self.repo / ".git").mkdir()

    def test_minimized_output_is_complete_and_no_raw_event_data(self):
        fixture(self.db)
        result = sync.snapshot(self.db, today=NOW)
        self.assertTrue(result["complete"])
        self.assertEqual(result["integrity"], "ok")
        self.assertEqual(result["schema"], sync.SCHEMA)
        self.assertEqual(
            result["coverage"]["task_queue"]["status_counts"],
            {"other": 2, "pending": 2, "running": 1},
        )
        self.assertEqual(
            result["coverage"]["event_ledger"]["latest_ten_status_counts"],
            {"completed": 1, "failed": 1},
        )
        self.assertEqual(result["coverage"]["dead_letter_quarantine"]["count"], 2)
        encoded = json.dumps(result)
        for sensitive in ("sensitive-event-1234", "private-wallet-reference",
                          "private-customer-record", "person@example.com",
                          "onchain-secret", "node_environment", "event_id"):
            self.assertNotIn(sensitive, encoded)
        self.assertFalse(result["claims"]["bounty_payouts_verified"])
        self.assertFalse(result["claims"]["investor_valuation_established"])

    def test_missing_database_fail_closed(self):
        with self.assertRaises(FileNotFoundError):
            sync.snapshot(self.db, today=NOW)

    def test_missing_table_not_described_as_empty_clean(self):
        fixture(self.db, omit_dlq=True)
        result = sync.snapshot(self.db, today=NOW)
        self.assertFalse(result["complete"])
        self.assertEqual(result["coverage"]["dead_letter_quarantine"],
                         {"state": "missing"})
        self.assertIn("missing_table:dead_letter_quarantine", result["warnings"])
        self.assertNotIn("count", result["coverage"]["dead_letter_quarantine"])

    def test_missing_column_is_schema_mismatch_not_healthy(self):
        fixture(self.db, bad_schema=True)
        result = sync.snapshot(self.db, today=NOW)
        self.assertFalse(result["complete"])
        self.assertEqual(result["coverage"]["task_queue"]["state"],
                         "schema_mismatch")

    def test_read_only_snapshot_does_not_change_database(self):
        fixture(self.db)
        before = self.db.stat().st_size
        sync.snapshot(self.db, today=NOW)
        after = self.db.stat().st_size
        self.assertEqual(before, after)
        with sqlite3.connect(self.db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM task_queue").fetchone()[0]
        self.assertEqual(count, 5)

    def test_snapshot_content_digest_deterministic_per_day(self):
        fixture(self.db)
        first = sync.snapshot(self.db, today=NOW)
        second = sync.snapshot(self.db, today=NOW)
        self.assertEqual(first, second)
        self.assertEqual(len(first["content_sha256"]), 64)

    def test_atomic_export_is_allowlisted_and_private_file_mode(self):
        fixture(self.db)
        result = sync.snapshot(self.db, today=NOW)
        path = sync.atomic_export(self.repo, result)
        self.assertEqual(path.relative_to(self.repo), sync.EXPORT_RELATIVE)
        self.assertEqual(json.loads(path.read_text()), result)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertFalse(list(path.parent.glob(".snapshot-*")))

    def test_dont_write_symlink_export_target(self):
        fixture(self.db)
        target = self.repo / sync.EXPORT_RELATIVE
        target.parent.mkdir(parents=True)
        target.symlink_to(self.base / "other.json")
        with self.assertRaises(sync.SyncError):
            sync.atomic_export(self.repo, sync.snapshot(self.db, today=NOW))

    def test_public_push_requires_explicit_ack(self):
        fixture(self.db)
        data = sync.snapshot(self.db, today=NOW)
        with self.assertRaisesRegex(sync.SyncError, "allow-public"):
            sync.publish_review_branch(self.repo, data, public_ack=False)

    def test_push_refuses_partial_snapshot(self):
        fixture(self.db, omit_dlq=True)
        with self.assertRaisesRegex(sync.SyncError, "incomplete"):
            sync.publish_review_branch(
                self.repo, sync.snapshot(self.db, today=NOW), public_ack=True
            )

    def test_push_refuses_unapproved_remote(self):
        fixture(self.db)
        data = sync.snapshot(self.db, today=NOW)
        with patch.object(sync, "_git", return_value="https://evil.example/repo"):
            with self.assertRaisesRegex(sync.SyncError, "unexpected Git remote"):
                sync.publish_review_branch(self.repo, data, public_ack=True)

    def test_push_never_to_main(self):
        fixture(self.db)
        data = sync.snapshot(self.db, today=NOW)
        with patch.object(sync, "_git", side_effect=[
            "git@github.com:Garrettc123/systems-master-hub.git", "main",
        ]):
            with self.assertRaisesRegex(sync.SyncError, "review branch"):
                sync.publish_review_branch(self.repo, data, public_ack=True)

    def test_idempotent_no_diffs_does_not_commit_or_push(self):
        fixture(self.db)
        data = sync.snapshot(self.db, today=NOW)
        branch = "telemetry/swarm-2026-11-17"
        calls = []
        def fake_git(_repo, *args):
            calls.append(args)
            if args[:2] == ("remote", "get-url"):
                return "https://github.com/Garrettc123/systems-master-hub.git"
            if args[:2] == ("branch", "--show-current"):
                return branch
            return ""
        with patch.object(sync, "_git", side_effect=fake_git):
            actual = sync.publish_review_branch(self.repo, data, public_ack=True)
        self.assertEqual(actual, branch)
        self.assertFalse(any(cmd and cmd[0] in ("commit", "push") for cmd in calls))

    def test_auto_discovery_finds_only_exact_database_name(self):
        fixture(self.db)
        (self.base / "node_modules").mkdir()
        (self.base / "node_modules" / "garcar_forge_operational.db").write_bytes(b"x")
        (self.base / "other.db").write_bytes(b"x")
        paths = sync.discover_databases(roots=[self.base])
        self.assertEqual(paths, [self.db.resolve()])
        self.assertEqual(sync.resolve_database(Path("auto"), roots=[self.base]),
                         self.db.resolve())

    def test_auto_discovery_refuses_ambiguity(self):
        fixture(self.db)
        other = self.base / "second"
        other.mkdir()
        (other / self.db.name).write_bytes(b"same filename")
        with self.assertRaisesRegex(sync.SyncError, "Multiple matching"):
            sync.resolve_database(Path("auto"), roots=[self.base])

    def test_auto_discovery_missing_never_creates_database(self):
        with self.assertRaisesRegex(sync.SyncError, "No garcar"):
            sync.resolve_database(Path("auto"), roots=[self.base])
        self.assertFalse(self.db.exists())

    def test_diagnostic_no_repository_required(self):
        fixture(self.db)
        self.assertEqual(sync.main(["--db", str(self.db), "--diagnose"]), 0)

    def test_export_requires_explicit_master_hub_checkout(self):
        fixture(self.db)
        self.assertEqual(sync.main(["--db", str(self.db)]), 1)
        # A non-hub repository is rejected before writing the telemetry.
        with patch.object(sync, "_git", return_value="https://github.com/other/repo.git"):
            self.assertEqual(sync.main(["--db", str(self.db), "--repo", str(self.repo)]), 1)
        self.assertFalse((self.repo / sync.EXPORT_RELATIVE).exists())

    def test_local_db_lookup_does_not_follow_symlink(self):
        fixture(self.db)
        alias = self.base / "nested"
        alias.mkdir()
        (alias / sync.DB_FILENAME).symlink_to(self.db)
        self.assertEqual(sync.discover_databases(roots=[alias]), [])

    def test_cli_diagnostic_on_missing_db_is_error(self):
        self.assertEqual(sync.main(["--db", str(self.db), "--diagnose"]), 1)


if __name__ == "__main__":
    unittest.main()
