from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.ledger import EventLedger


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def integrity_check(path: Path) -> None:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(f"SQLite integrity check failed: {result}")
    finally:
        conn.close()


def create_backup(source: Path, destination_dir: Path) -> tuple[Path, Path]:
    if not source.is_file():
        raise FileNotFoundError(f"Ledger database not found: {source}")
    source_check = EventLedger(str(source)).verify()
    if not source_check["valid"]:
        raise RuntimeError("Source ledger hash chain is invalid; refusing trusted backup")
    destination_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = destination_dir / f"garcar-forge-{stamp}.sqlite3"
    source_conn = sqlite3.connect(f"file:{source}?mode=rw", uri=True)
    target_conn = sqlite3.connect(backup_path)
    try:
        source_conn.backup(target_conn)
    finally:
        target_conn.close()
        source_conn.close()
    integrity_check(backup_path)
    result = EventLedger(str(backup_path)).verify()
    if not result["valid"]:
        backup_path.unlink(missing_ok=True)
        raise RuntimeError("Backup ledger verification failed")
    manifest_path = backup_path.with_suffix(backup_path.suffix + ".json")
    manifest = {
        "created_at": datetime.now(UTC).isoformat(),
        "database_file": backup_path.name,
        "sha256": sha256_file(backup_path),
        "ledger_event_count": result["checked"],
        "ledger_head": result["head"],
        "integrity_check": "ok",
        "restore_status": "not_restored",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return backup_path, manifest_path


def verify_backup(backup_path: Path, manifest_path: Path | None = None) -> dict[str, object]:
    manifest_path = manifest_path or backup_path.with_suffix(backup_path.suffix + ".json")
    if not backup_path.is_file() or not manifest_path.is_file():
        raise FileNotFoundError("Backup database and its JSON manifest are both required")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sha256_file(backup_path) != manifest.get("sha256"):
        raise RuntimeError("Backup SHA-256 does not match its manifest")
    integrity_check(backup_path)
    result = EventLedger(str(backup_path)).verify()
    if not result["valid"] or result["checked"] != manifest.get("ledger_event_count"):
        raise RuntimeError("Backup ledger verification does not match its manifest")
    if result["head"] != manifest.get("ledger_head"):
        raise RuntimeError("Backup chain head does not match its manifest")
    return {"valid": True, "sha256": manifest["sha256"], **result}


def restore_backup(backup_path: Path, target_path: Path, confirmed: bool) -> None:
    if not confirmed:
        raise PermissionError("Restore requires --confirm-restore")
    verify_backup(backup_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        raise FileExistsError("Restore target exists; move it to a safe backup path first")
    source_conn = sqlite3.connect(f"file:{backup_path}?mode=ro", uri=True)
    target_conn = sqlite3.connect(target_path)
    try:
        source_conn.backup(target_conn)
    finally:
        target_conn.close()
        source_conn.close()
    integrity_check(target_path)
    restored = EventLedger(str(target_path)).verify()
    if not restored["valid"]:
        target_path.unlink(missing_ok=True)
        raise RuntimeError("Restored ledger failed verification")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify or create a Garcar Forge SQLite backup")
    sub = parser.add_subparsers(dest="command", required=True)
    backup_parser = sub.add_parser("create")
    backup_parser.add_argument("--source", default="./data/garcar-forge.sqlite3")
    backup_parser.add_argument("--destination", default="./backups")
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("backup")
    restore_parser = sub.add_parser("restore")
    restore_parser.add_argument("backup")
    restore_parser.add_argument("--target", required=True)
    restore_parser.add_argument("--confirm-restore", action="store_true")
    args = parser.parse_args()
    if args.command == "create":
        paths = create_backup(Path(args.source), Path(args.destination))
        print(json.dumps({"backup": str(paths[0]), "manifest": str(paths[1])}, indent=2))
    elif args.command == "verify":
        print(json.dumps(verify_backup(Path(args.backup)), indent=2))
    else:
        restore_backup(Path(args.backup), Path(args.target), args.confirm_restore)
        print(json.dumps({"restored": str(args.target), "verified": True}, indent=2))


if __name__ == "__main__":
    main()
