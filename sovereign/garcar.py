#!/usr/bin/env python3
"""Garcar Sovereign Control Plane: local CI and loopback-only deployment MVP."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, signal, sqlite3, subprocess, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("GARCAR_ROOT", Path.home() / ".garcar-sovereign")).expanduser().resolve()
DB = ROOT / "state" / "control.sqlite3"
IGNORES = shutil.ignore_patterns(".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache")

def utcnow():
    return datetime.now(timezone.utc).isoformat()

def init():
    for p in (ROOT / "state", ROOT / "apps", ROOT / "logs", ROOT / "artifacts"):
        p.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("""CREATE TABLE IF NOT EXISTS deployments (
            app TEXT PRIMARY KEY, release TEXT NOT NULL, pid INTEGER NOT NULL,
            port INTEGER NOT NULL, status TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS audit (
            seq INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, action TEXT NOT NULL,
            app TEXT NOT NULL, detail TEXT NOT NULL, prev_hash TEXT NOT NULL, entry_hash TEXT NOT NULL
        )""")
    return ROOT

def audit(action, app, detail):
    with sqlite3.connect(DB) as db:
        row = db.execute("SELECT entry_hash FROM audit ORDER BY seq DESC LIMIT 1").fetchone()
        prev = row[0] if row else "GENESIS"
        ts = utcnow()
        payload = json.dumps({"ts":ts,"action":action,"app":app,"detail":detail,"prev":prev}, sort_keys=True)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        db.execute("INSERT INTO audit(ts,action,app,detail,prev_hash,entry_hash) VALUES(?,?,?,?,?,?)",
                   (ts,action,app,detail,prev,digest))

def verify_ledger():
    with sqlite3.connect(DB) as db:
        rows = db.execute("SELECT ts,action,app,detail,prev_hash,entry_hash FROM audit ORDER BY seq").fetchall()
    previous = "GENESIS"
    for ts, action, app, detail, prev, digest in rows:
        if prev != previous:
            return False, "previous-hash mismatch"
        payload = json.dumps({"ts":ts,"action":action,"app":app,"detail":detail,"prev":previous}, sort_keys=True)
        if hashlib.sha256(payload.encode()).hexdigest() != digest:
            return False, "entry hash mismatch"
        previous = digest
    return True, f"{len(rows)} audit records verified"

def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Cannot read JSON manifest {path}: {exc}") from exc

def validate_steps(value, field):
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list of argument arrays")
    for i, step in enumerate(value):
        if not isinstance(step, list) or not step or not all(isinstance(x, str) and x for x in step):
            raise ValueError(f"{field}[{i}] must be a non-empty array of strings; shell strings are forbidden")
    return value

def load_ci(source):
    path = Path(source) / "garcar.ci.json"
    cfg = read_json(path)
    steps = validate_steps(cfg.get("steps"), "steps")
    passthrough = cfg.get("env_passthrough", [])
    if not isinstance(passthrough, list) or not all(isinstance(x, str) and x.isidentifier() for x in passthrough):
        raise ValueError("env_passthrough must contain environment variable names only")
    return steps, passthrough

def ci_environment(passthrough):
    safe = ("PATH", "HOME", "PREFIX", "TMPDIR", "TEMP", "LANG", "LC_ALL")
    env = {key: os.environ[key] for key in safe if key in os.environ}
    env.update({key: os.environ[key] for key in passthrough if key in os.environ})
    return env

def run_steps(steps, cwd, env, logfile):
    for i, argv in enumerate(steps, 1):
        with open(logfile, "a", encoding="utf-8") as out:
            out.write(f"\n[$ step {i}] {json.dumps(argv)}\n")
            out.flush()
            result = subprocess.run(argv, cwd=cwd, env=env, stdout=out, stderr=subprocess.STDOUT,
                                    shell=False, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"step {i} failed with exit code {result.returncode}; log: {logfile}")

def ci(source):
    init()
    source = Path(source).expanduser().resolve()
    if not source.is_dir():
        raise ValueError("Repository directory does not exist")
    steps, passthrough = load_ci(source)
    log = ROOT / "logs" / f"ci-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.log"
    run_steps(steps, source, ci_environment(passthrough), log)
    print(f"CI PASSED: {source}\nLog: {log}")

def safe_name(name):
    if not name or name in (".", "..") or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_." for c in name):
        raise ValueError("Invalid app name")
    return name

def load_deploy(source):
    cfg = read_json(Path(source) / "garcar.deploy.json")
    if not isinstance(cfg.get("name"), str):
        raise ValueError("manifest requires name")
    safe_name(cfg["name"])
    validate_steps(cfg.get("build", []), "build")
    start = cfg.get("start")
    if not isinstance(start, list) or not start or not all(isinstance(x, str) and x for x in start):
        raise ValueError("start must be a non-empty argument array; shell strings are forbidden")
    for key in ("port", "canary_port"):
        port = cfg.get(key)
        if not isinstance(port, int) or not 1024 <= port <= 65535:
            raise ValueError(f"{key} must be an integer between 1024 and 65535")
    if cfg["port"] == cfg["canary_port"]:
        raise ValueError("port and canary_port must be different")
    health = cfg.get("health", {})
    path = health.get("path", "/health") if isinstance(health, dict) else None
    if not isinstance(path, str) or not path.startswith("/") or ".." in path or "://" in path:
        raise ValueError("health.path must be a safe absolute path")
    passthrough = cfg.get("env_passthrough", [])
    if not isinstance(passthrough, list) or not all(isinstance(x, str) and x.isidentifier() for x in passthrough):
        raise ValueError("env_passthrough must contain environment variable names only")
    return cfg

def make_env(cfg, port):
    env = {key: os.environ[key] for key in cfg.get("env_passthrough", []) if key in os.environ}
    env.update({"PORT":str(port), "HOST":"127.0.0.1", "BIND_HOST":"127.0.0.1", "GARCAR_BIND_HOST":"127.0.0.1"})
    return env

def start_process(cfg, release, port, logfile):
    env = make_env(cfg, port)
    with open(logfile, "a", encoding="utf-8") as out:
        proc = subprocess.Popen(cfg["start"], cwd=release, env=env, stdout=out, stderr=subprocess.STDOUT,
                                shell=False, start_new_session=True)
    return proc

def stop_pid(pid, timeout=5):
    try:
        os.killpg(int(pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, ValueError):
        return
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.killpg(int(pid), 0)
        except (ProcessLookupError, PermissionError, ValueError):
            return
        time.sleep(0.1)
    try:
        os.killpg(int(pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, ValueError):
        pass

def health(port, path, timeout=20):
    url = f"http://127.0.0.1:{port}{path}"
    deadline = time.monotonic() + timeout
    last = "no response"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 300:
                    return True, f"HTTP {response.status}"
                last = f"HTTP {response.status}"
        except Exception as exc:
            last = type(exc).__name__
        time.sleep(0.5)
    return False, last

def current_record(app):
    with sqlite3.connect(DB) as db:
        return db.execute("SELECT release,pid,port FROM deployments WHERE app=?", (app,)).fetchone()

def launch_and_check(cfg, release, port, logfile):
    proc = start_process(cfg, release, port, logfile)
    ok, detail = health(port, cfg.get("health", {}).get("path", "/health"))
    if not ok:
        stop_pid(proc.pid)
        raise RuntimeError(f"health check failed on port {port}: {detail}")
    return proc

def deploy(source):
    init()
    source = Path(source).expanduser().resolve()
    if not source.is_dir():
        raise ValueError("Source directory does not exist")
    cfg = load_deploy(source)
    app = cfg["name"]
    appdir = ROOT / "apps" / app
    releases = appdir / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    source_hash = hashlib.sha256(str(source).encode()).hexdigest()[:10]
    release = releases / f"{stamp}-{source_hash}"
    shutil.copytree(source, release, ignore=IGNORES)
    logfile = ROOT / "logs" / f"{app}-{stamp}.log"
    previous = current_record(app)
    candidate = None
    try:
        run_steps(cfg.get("build", []), release, make_env(cfg, cfg["canary_port"]), logfile)
        candidate = launch_and_check(cfg, release, cfg["canary_port"], logfile)
        stop_pid(candidate.pid)
        candidate = None
        if previous:
            stop_pid(previous[1])
            time.sleep(0.5)
        try:
            promoted = launch_and_check(cfg, release, cfg["port"], logfile)
        except Exception:
            if previous:
                old_release = Path(previous[0])
                old_cfg = load_deploy(old_release)
                restored = launch_and_check(old_cfg, old_release, previous[2], logfile)
                with sqlite3.connect(DB) as db:
                    db.execute("UPDATE deployments SET pid=?,status='healthy',updated_at=? WHERE app=?",
                               (restored.pid,utcnow(),app))
                audit("rollback_restored", app, str(old_release))
            raise
        active = appdir / "current"
        tmp = appdir / f".current-{promoted.pid}"
        tmp.symlink_to(release, target_is_directory=True)
        os.replace(tmp, active)
        with sqlite3.connect(DB) as db:
            db.execute("""INSERT INTO deployments(app,release,pid,port,status,updated_at)
                VALUES(?,?,?,?,?,?) ON CONFLICT(app) DO UPDATE SET
                release=excluded.release,pid=excluded.pid,port=excluded.port,status='healthy',updated_at=excluded.updated_at""",
                (app,str(release),promoted.pid,cfg["port"],"healthy",utcnow()))
        audit("deploy_healthy", app, json.dumps({"release":str(release),"port":cfg["port"]}))
        print(f"DEPLOYED {app}: healthy on 127.0.0.1:{cfg['port']}\nRelease: {release}\nLog: {logfile}")
    except Exception as exc:
        if candidate:
            stop_pid(candidate.pid)
        shutil.rmtree(release, ignore_errors=True)
        audit("deploy_failed", app, type(exc).__name__)
        raise

def status():
    init()
    with sqlite3.connect(DB) as db:
        rows = db.execute("SELECT app,release,pid,port,status,updated_at FROM deployments ORDER BY app").fetchall()
    for app, release, pid, port, state, updated in rows:
        try:
            os.kill(int(pid), 0); alive = True
        except (ProcessLookupError, PermissionError, ValueError):
            alive = False
        print(json.dumps({"app":app,"release":release,"pid":pid,"port":port,"process_alive":alive,"status":state,"updated_at":updated}))

def stop(app):
    init()
    row = current_record(safe_name(app))
    if not row:
        print("No deployment record")
        return
    stop_pid(row[1])
    with sqlite3.connect(DB) as db:
        db.execute("UPDATE deployments SET status='stopped',updated_at=? WHERE app=?", (utcnow(),app))
    audit("stop", app, "operator requested")
    print(f"STOPPED {app}")

def main():
    parser = argparse.ArgumentParser(description="Garcar Sovereign Control Plane — local CI and deploy")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    c = sub.add_parser("ci"); c.add_argument("source")
    d = sub.add_parser("deploy"); d.add_argument("source")
    sub.add_parser("status")
    s = sub.add_parser("stop"); s.add_argument("app")
    sub.add_parser("verify-ledger")
    args = parser.parse_args()
    try:
        if args.command == "init": print(f"Initialized: {init()}")
        elif args.command == "ci": ci(args.source)
        elif args.command == "deploy": deploy(args.source)
        elif args.command == "status": status()
        elif args.command == "stop": stop(args.app)
        elif args.command == "verify-ledger":
            init(); ok, message = verify_ledger(); print(("PASS: " if ok else "FAIL: ") + message); sys.exit(0 if ok else 2)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr); sys.exit(1)

if __name__ == "__main__":
    main()
