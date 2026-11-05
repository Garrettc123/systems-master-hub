from __future__ import annotations
import argparse, fcntl, hashlib, hmac, json, os, re, secrets, sqlite3, sys, time, tempfile
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from garcar_actions.execution import execute

DB_PATH = Path(os.environ.get("GARCAR_ACTIONS_DB", "data/actions.db")).resolve()
WORKSPACE = Path(os.environ.get("GARCAR_WORKSPACE", ".")).resolve()
MAX_BODY, MAX_RUNTIME, POLL_SECONDS = 16384, 600, 2
MAX_PENDING, MAX_OUTPUT = 100, 1_048_576
ACTIONS = {
    "python_tests": [sys.executable, str(Path(__file__).with_name("test_job.py"))],
    "python_compile": [sys.executable, "-m", "compileall", "-q", "."],
    "node_tests": ["npm", "test"],
    "git_status": ["git", "status", "--short"],
    "hub_structure": [sys.executable, str(Path(__file__).with_name("hub_check.py"))],
}

class QueueFull(ValueError):
    pass

class WorkerBusy(RuntimeError):
    pass

class RecoveryRequired(RuntimeError):
    pass

class AuditCorrupt(RuntimeError):
    pass

@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA foreign_keys=ON")
    try:
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
        columns = {row["name"] for row in db.execute("PRAGMA table_info(jobs)")}
        additions = {"idempotency_key": "TEXT", "source_path": "TEXT", "source_sha256": "TEXT"}
        if set(additions) - columns:
            # Serialize upgrade with another API/worker starting at the same time.
            db.execute("BEGIN IMMEDIATE")
            columns = {row["name"] for row in db.execute("PRAGMA table_info(jobs)")}
            for name, sql_type in additions.items():
                if name not in columns:
                    db.execute(f"ALTER TABLE jobs ADD COLUMN {name} {sql_type}")
            db.commit()
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS jobs_idempotency ON jobs(idempotency_key)")
        with db:
            yield db
    finally:
        db.close()

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
    count = 0
    for row in db.execute("SELECT * FROM audit ORDER BY seq"):
        expected = hashlib.sha256(
            f"{previous}|{row['at']:.6f}|{row['event']}|{row['payload']}".encode()
        ).hexdigest()
        if row["prev_hash"] != previous or not hmac.compare_digest(row["entry_hash"], expected):
            return False, row["seq"]
        previous = row["entry_hash"]
        count += 1
    return True, count

def require_valid_audit(db):
    if not verify_audit(db)[0]:
        raise AuditCorrupt("Audit integrity failed; job mutation is blocked")

def workspace_target(repo_path):
    if not isinstance(repo_path, str) or not repo_path or len(repo_path) > 4096:
        raise ValueError("repo_path must be a nonempty path string")
    path = Path(repo_path)
    target = (path if path.is_absolute() else WORKSPACE / path).resolve()
    if target != WORKSPACE and WORKSPACE not in target.parents:
        raise ValueError("Workspace path must remain inside GARCAR_WORKSPACE")
    if not target.is_dir():
        raise ValueError("Workspace directory does not exist")
    return target

def job_environment(home):
    # Do not inherit API tokens, cloud credentials, PYTHONPATH or loader hooks.
    # Executable locations belong to the trusted host, never the checkout.
    return {"PATH": os.pathsep.join(dict.fromkeys([str(Path(sys.executable).parent), os.defpath])),
            "HOME": home, "TMPDIR": home, "CI": "1", "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
            "PYTHONNOUSERSITE": "1", "LANG": "C.UTF-8"}

def verify_source_pin(target, source_path, source_sha256):
    if (not isinstance(source_path, str) or not source_path or Path(source_path).is_absolute() or
            ".." in Path(source_path).parts or not isinstance(source_sha256, str) or
            not re.fullmatch(r"[0-9a-f]{64}", source_sha256)):
        raise ValueError("Invalid workflow source pin")
    path = (target / source_path).resolve()
    if not path.is_relative_to(target) or not path.is_file() or path.stat().st_size > 1_048_576:
        raise ValueError("Workflow source must be a bounded file inside the checkout")
    if not hmac.compare_digest(hashlib.sha256(path.read_bytes()).hexdigest(), source_sha256):
        raise ValueError("Workflow source changed; review and repin before execution")

def enqueue(action, repo_path=".", requested_by="operator", idempotency_key=None, *, source_path=None, source_sha256=None):
    if not isinstance(action, str) or action not in ACTIONS:
        raise ValueError(f"Action not allowed: {action}")
    if not isinstance(requested_by, str) or not 1 <= len(requested_by) <= 80:
        raise ValueError("requested_by must contain 1 to 80 characters")
    if idempotency_key is not None and (not isinstance(idempotency_key, str) or
            not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", idempotency_key)):
        raise ValueError("Invalid idempotency key")
    target = workspace_target(repo_path)
    if source_path is not None or source_sha256 is not None:
        verify_source_pin(target, source_path, source_sha256)
    job_id = secrets.token_hex(12)
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        require_valid_audit(db)
        if idempotency_key is not None:
            existing = db.execute("SELECT * FROM jobs WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing:
                if (existing["action"] != action or existing["repo_path"] != str(target) or
                        existing["source_path"] != source_path or existing["source_sha256"] != source_sha256):
                    raise ValueError("Idempotency key belongs to a different request")
                return existing["id"]
        pending = db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','running')").fetchone()[0]
        if pending >= MAX_PENDING:
            raise QueueFull("Pending job quota reached")
        db.execute("INSERT INTO jobs(id,action,repo_path,status,created_at,requested_by,idempotency_key,source_path,source_sha256) VALUES(?,?,?,'queued',?,?,?,?,?)",
                   (job_id, action, str(target), time.time(), requested_by, idempotency_key, source_path, source_sha256))
        audit(db, "job.queued", {"id": job_id, "action": action, "repo_path": str(target),
                                 "source_path": source_path, "source_sha256": source_sha256})
    return job_id

@contextmanager
def worker_lock():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(DB_PATH) + ".worker.lock", os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise WorkerBusy("Another worker owns this queue") from exc
        yield
    finally:
        os.close(fd)

def run_one():
    with worker_lock():
        return _run_one()

def _run_one():
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        require_valid_audit(db)
        if db.execute("SELECT 1 FROM jobs WHERE status='running' LIMIT 1").fetchone():
            raise RecoveryRequired("Interrupted job found; stop its processes and run recover --confirm-stopped")
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
        target = workspace_target(row["repo_path"])
        if row["source_path"] is not None or row["source_sha256"] is not None:
            verify_source_pin(target, row["source_path"], row["source_sha256"])
        if row["action"] not in ACTIONS:
            raise ValueError("Queued action is no longer allowed")
        with tempfile.TemporaryDirectory(prefix="garcar-job-") as home:
            result = execute(ACTIONS[row["action"]], cwd=target,
                             timeout=MAX_RUNTIME, output_limit=MAX_OUTPUT,
                             env=job_environment(home))
        code, output = result.returncode, result.output
    except (OSError, ValueError) as exc:
        code, output = 127, f"EXECUTION ERROR: {type(exc).__name__}: {exc}"
    status = "succeeded" if code == 0 else "failed"
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        require_valid_audit(db)
        db.execute("UPDATE jobs SET status=?,finished_at=?,exit_code=?,output=? WHERE id=? AND status='running'",
                   (status, time.time(), code, output, row["id"]))
        audit(db, "job.finished", {"id": row["id"], "status": status, "exit_code": code})
    return True

def recover_interrupted():
    # Never replay work whose side effects are unknown. The caller must first
    # terminate the previous job host/processes; a dead worker alone is insufficient.
    with worker_lock(), connect() as db:
        db.execute("BEGIN IMMEDIATE")
        require_valid_audit(db)
        rows = db.execute("SELECT id FROM jobs WHERE status='running'").fetchall()
        for row in rows:
            db.execute("UPDATE jobs SET status='failed',finished_at=?,exit_code=130,output=? WHERE id=?",
                       (time.time(), "Interrupted job closed after operator confirmed processes stopped; not replayed", row["id"]))
            audit(db, "job.interrupted", {"id": row["id"], "status": "failed", "exit_code": 130})
        return len(rows)

def worker(once=False):
    while True:
        try:
            did_work = run_one()
        except WorkerBusy:
            did_work = False
        if once: return
        if not did_work: time.sleep(POLL_SECONDS)

def authorized(handler):
    expected = os.environ.get("GARCAR_ACTIONS_TOKEN", "")
    supplied = handler.headers.get("Authorization", "")
    return bool(32 <= len(expected) <= 512 and supplied.startswith("Bearer ") and
                hmac.compare_digest(supplied[7:].encode(), expected.encode()))

class Handler(BaseHTTPRequestHandler):
    server_version = "GarcarActions/0.2"
    def setup(self):
        super().setup()
        self.connection.settimeout(10)
    def reply(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)
    def do_GET(self):
        try:
            self.get_request()
        except sqlite3.Error:
            self.reply(503, {"error": "queue_unavailable"})
    def get_request(self):
        if self.path == "/health":
            self.reply(200, {"ok": True, "service": "garcar-actions", "version": "0.2.0"})
            return
        if not authorized(self):
            self.reply(401, {"error": "unauthorized"})
            return
        if self.path == "/v1/status":
            with connect() as db:
                ok, count = verify_audit(db)
                queue = {state: 0 for state in ("queued", "running", "succeeded", "failed")}
                queue.update({row["status"]: row["total"] for row in
                              db.execute("SELECT status,count(*) AS total FROM jobs GROUP BY status")})
            self.reply(200 if ok else 503, {"service": "garcar-actions", "version": "0.2.0",
                       "mode": "reviewed_code_canary", "audit": {"valid": ok, "entries_checked": count},
                       "queue": queue, "allowed_actions": sorted(ACTIONS)})
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
            if self.headers.get("Transfer-Encoding") or len(self.headers.get_all("Content-Length", [])) != 1:
                raise ValueError("Exactly one Content-Length and no Transfer-Encoding are required")
            length = int(self.headers.get("Content-Length", "0"))
            if length < 2 or length > MAX_BODY: raise ValueError("Invalid request size")
            data = self.rfile.read(length)
            if len(data) != length: raise ValueError("Truncated request body")
            body = json.loads(data)
            if not isinstance(body, dict): raise ValueError("Request must be a JSON object")
            if set(body) - {"action", "repo_path", "requested_by"}: raise ValueError("Unknown request fields")
            job_id = enqueue(body.get("action", ""), body.get("repo_path", "."),
                             body.get("requested_by", "api"), self.headers.get("Idempotency-Key"))
            with connect() as db:
                status = db.execute("SELECT status FROM jobs WHERE id=?", (job_id,)).fetchone()[0]
            self.reply(202, {"id": job_id, "status": status})
        except QueueFull as exc:
            self.reply(429, {"error": str(exc)})
        except ValueError as exc:
            self.reply(400, {"error": str(exc)})
        except (sqlite3.Error, AuditCorrupt):
            self.reply(503, {"error": "queue_unavailable"})
    def log_message(self, fmt, *args):
        sys.stderr.write("garcar-actions: " + (fmt % args) + "\n")

def serve(host="127.0.0.1", port=8788):
    if host not in ("127.0.0.1", "localhost") and os.environ.get("GARCAR_ACTIONS_ALLOW_REMOTE") != "1":
        raise SystemExit("Remote binding blocked; use TLS/reverse-proxy controls first.")
    if not 32 <= len(os.environ.get("GARCAR_ACTIONS_TOKEN", "")) <= 512:
        raise SystemExit("GARCAR_ACTIONS_TOKEN must contain 32 to 512 characters.")
    with ThreadingHTTPServer((host, port), Handler) as server:
        print(json.dumps({"service": "garcar-actions", "host": host, "port": server.server_address[1]}), flush=True)
        server.serve_forever()

def main():
    parser = argparse.ArgumentParser(description="Independent allow-listed Garcar automation runner")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    p = sub.add_parser("submit"); p.add_argument("action", choices=sorted(ACTIONS)); p.add_argument("--repo", default="."); p.add_argument("--idempotency-key")
    p = sub.add_parser("serve"); p.add_argument("--host", default="127.0.0.1"); p.add_argument("--port", type=int, default=8788)
    p = sub.add_parser("worker"); p.add_argument("--once", action="store_true")
    p = sub.add_parser("recover"); p.add_argument("--confirm-stopped", action="store_true", required=True)
    sub.add_parser("audit-verify")
    p = sub.add_parser("status"); p.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    if args.command == "init":
        with connect(): pass
        print(f"Initialized {DB_PATH}")
    elif args.command == "submit": print(enqueue(args.action, args.repo, idempotency_key=args.idempotency_key))
    elif args.command == "serve": serve(args.host, args.port)
    elif args.command == "worker": worker(args.once)
    elif args.command == "recover": print(json.dumps({"interrupted_jobs_closed": recover_interrupted()}))
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
