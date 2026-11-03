from __future__ import annotations
import argparse, hashlib, hmac, json, os, secrets, sqlite3, subprocess, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

DB_PATH = Path(os.environ.get("GARCAR_ACTIONS_DB", "data/actions.db"))
WORKSPACE = Path(os.environ.get("GARCAR_WORKSPACE", ".")).resolve()
MAX_BODY, MAX_RUNTIME, POLL_SECONDS = 16384, 600, 2
ACTIONS = {
    "python_tests": [sys.executable, "-m", "unittest", "discover", "-v"],
    "python_compile": [sys.executable, "-m", "compileall", "-q", "."],
    "node_tests": ["npm", "test"],
    "git_status": ["git", "status", "--short"],
}

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
      CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, action TEXT NOT NULL, repo_path TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('queued','running','succeeded','failed')),
        created_at REAL NOT NULL, started_at REAL, finished_at REAL,
        exit_code INTEGER, output TEXT NOT NULL DEFAULT '', requested_by TEXT NOT NULL
      );
      CREATE TABLE IF NOT EXISTS audit (
        seq INTEGER PRIMARY KEY AUTOINCREMENT, at REAL NOT NULL,
        event TEXT NOT NULL, payload TEXT NOT NULL, prev_hash TEXT NOT NULL,
        entry_hash TEXT NOT NULL UNIQUE
      );
    """)
    return db

def audit(db, event, payload):
    prev = db.execute("SELECT entry_hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
    prev_hash = prev["entry_hash"] if prev else "0" * 64
    at = time.time()
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(f"{prev_hash}|{at:.6f}|{event}|{body}".encode()).hexdigest()
    db.execute("INSERT INTO audit(at,event,payload,prev_hash,entry_hash) VALUES(?,?,?,?,?)",
               (at, event, body, prev_hash, digest))

def verify_audit(db):
    previous = "0" * 64
    rows = db.execute("SELECT * FROM audit ORDER BY seq").fetchall()
    for row in rows:
        expected = hashlib.sha256(
            f"{previous}|{row['at']:.6f}|{row['event']}|{row['payload']}".encode()
        ).hexdigest()
        if row["prev_hash"] != previous or not hmac.compare_digest(row["entry_hash"], expected):
            return False, row["seq"]
        previous = row["entry_hash"]
    return True, len(rows)

def enqueue(action, repo_path=".", requested_by="operator"):
    if action not in ACTIONS:
        raise ValueError(f"Action not allowed: {action}")
    target = Path(repo_path).resolve()
    if target != WORKSPACE and WORKSPACE not in target.parents:
        raise ValueError("Workspace path must remain inside GARCAR_WORKSPACE")
    if not target.is_dir():
        raise ValueError("Workspace directory does not exist")
    job_id = secrets.token_hex(12)
    with connect() as db:
        db.execute("INSERT INTO jobs(id,action,repo_path,status,created_at,requested_by) VALUES(?,?,?,'queued',?,?)",
                   (job_id, action, str(target), time.time(), requested_by[:80]))
        audit(db, "job.queued", {"id": job_id, "action": action, "repo_path": str(target)})
    return job_id

def run_one():
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
        if row is None:
            db.commit()
            return False
        changed = db.execute("UPDATE jobs SET status='running',started_at=? WHERE id=? AND status='queued'",
                             (time.time(), row["id"])).rowcount
        if changed != 1:
            db.rollback()
            return False
        audit(db, "job.started", {"id": row["id"], "action": row["action"]})
        db.commit()
    try:
        result = subprocess.run(ACTIONS[row["action"]], cwd=row["repo_path"], text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=MAX_RUNTIME, check=False, shell=False,
                                env={**os.environ, "CI": "1", "GIT_TERMINAL_PROMPT": "0"})
        code, output = result.returncode, result.stdout[-12000:]
    except subprocess.TimeoutExpired as exc:
        code, output = 124, str(exc.stdout or "")[-12000:] + "\nTIMEOUT: exceeded 600 seconds"
    except OSError as exc:
        code, output = 127, f"EXECUTION ERROR: {type(exc).__name__}: {exc}"
    status = "succeeded" if code == 0 else "failed"
    with connect() as db:
        db.execute("UPDATE jobs SET status=?,finished_at=?,exit_code=?,output=? WHERE id=? AND status='running'",
                   (status, time.time(), code, output, row["id"]))
        audit(db, "job.finished", {"id": row["id"], "status": status, "exit_code": code})
    return True

def worker(once=False):
    while True:
        did_work = run_one()
        if once: return
        if not did_work: time.sleep(POLL_SECONDS)

def authorized(handler):
    expected = os.environ.get("GARCAR_ACTIONS_TOKEN", "")
    supplied = handler.headers.get("Authorization", "")
    return bool(expected and supplied.startswith("Bearer ") and hmac.compare_digest(supplied[7:], expected))

class Handler(BaseHTTPRequestHandler):
    server_version = "GarcarActions/0.1"
    def reply(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        if self.path == "/health":
            self.reply(200, {"ok": True, "service": "garcar-actions", "version": "0.1.0"})
            return
        if not authorized(self):
            self.reply(401, {"error": "unauthorized"})
            return
        if self.path == "/v1/audit/verify":
            with connect() as db: ok, count = verify_audit(db)
            self.reply(200 if ok else 409, {"valid": ok, "entries_checked": count})
            return
        if self.path.startswith("/v1/jobs/"):
            job_id = self.path.rsplit("/", 1)[-1]
            with connect() as db:
                row = db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            self.reply(200, dict(row)) if row else self.reply(404, {"error": "not_found"})
            return
        self.reply(404, {"error": "not_found"})
    def do_POST(self):
        if not authorized(self):
            self.reply(401, {"error": "unauthorized"})
            return
        if self.path != "/v1/jobs":
            self.reply(404, {"error": "not_found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > MAX_BODY: raise ValueError("Invalid request size")
            body = json.loads(self.rfile.read(length))
            job_id = enqueue(str(body.get("action", "")), str(body.get("repo_path", ".")),
                             str(body.get("requested_by", "api")))
            self.reply(202, {"id": job_id, "status": "queued"})
        except (ValueError, json.JSONDecodeError) as exc:
            self.reply(400, {"error": str(exc)})
    def log_message(self, fmt, *args):
        sys.stderr.write("garcar-actions: " + (fmt % args) + "\n")

def serve(host="127.0.0.1", port=8788):
    if host not in ("127.0.0.1", "::1", "localhost") and not os.environ.get("GARCAR_ACTIONS_ALLOW_REMOTE"):
        raise SystemExit("Remote binding blocked; use TLS/reverse-proxy controls first.")
    if not os.environ.get("GARCAR_ACTIONS_TOKEN"):
        raise SystemExit("GARCAR_ACTIONS_TOKEN is required.")
    with ThreadingHTTPServer((host, port), Handler) as server:
        print(f"Garcar Actions listening on {host}:{port}")
        server.serve_forever()

def main():
    parser = argparse.ArgumentParser(description="Independent allow-listed Garcar automation runner")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    p = sub.add_parser("submit"); p.add_argument("action", choices=sorted(ACTIONS)); p.add_argument("--repo", default=".")
    p = sub.add_parser("serve"); p.add_argument("--host", default="127.0.0.1"); p.add_argument("--port", type=int, default=8788)
    p = sub.add_parser("worker"); p.add_argument("--once", action="store_true")
    sub.add_parser("audit-verify")
    p = sub.add_parser("status"); p.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if args.command == "init":
        with connect(): pass
        print(f"Initialized {DB_PATH}")
    elif args.command == "submit": print(enqueue(args.action, args.repo))
    elif args.command == "serve": serve(args.host, args.port)
    elif args.command == "worker": worker(args.once)
    elif args.command == "audit-verify":
        with connect() as db: ok, count = verify_audit(db)
        print(json.dumps({"valid": ok, "entries_checked": count}))
        raise SystemExit(0 if ok else 2)
    elif args.command == "status":
        with connect() as db:
            rows = db.execute("SELECT id,action,status,created_at,finished_at,exit_code FROM jobs ORDER BY created_at DESC LIMIT ?",
                              (max(1, min(args.limit, 100)),)).fetchall()
        print(json.dumps([dict(x) for x in rows], indent=2))

if __name__ == "__main__":
    main()
