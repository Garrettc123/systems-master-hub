#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${GARCAR_SMOKE_PORT:-18080}"
TMP="$(mktemp -d)"
export GARCAR_OPERATOR_TOKEN="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export GARCAR_LEDGER_PATH="$TMP/ledger.sqlite3"
export PYTHONPATH="$PWD"
API_PID=""; WORKER_PID=""
cleanup() {
  [ -z "$WORKER_PID" ] || kill "$WORKER_PID" 2>/dev/null || true
  [ -z "$API_PID" ] || kill "$API_PID" 2>/dev/null || true
  rm -rf "$TMP"
}
trap cleanup EXIT
python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" >"$TMP/api.log" 2>&1 & API_PID=$!
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:$PORT/readyz" >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -fsS "http://127.0.0.1:$PORT/readyz" >/dev/null || { cat "$TMP/api.log"; exit 1; }
python - "$PORT" <<'PY'
import json, os, sys, urllib.request
port=sys.argv[1]
request=urllib.request.Request(
    f"http://127.0.0.1:{port}/v1/jobs",
    data=json.dumps({"task_name":"ledger.verify","idempotency_key":"e2e-smoke-job-00000001","dry_run":True}).encode(),
    method="POST",
    headers={"Authorization":"Bearer "+os.environ["GARCAR_OPERATOR_TOKEN"],"Content-Type":"application/json"},
)
with urllib.request.urlopen(request,timeout=5) as response:
    job=json.loads(response.read())["job"]
print(job["job_id"])
PY
python -m app.worker >"$TMP/worker.log" 2>&1 & WORKER_PID=$!
python - "$PORT" <<'PY'
import json, os, sqlite3, sys, time, urllib.request
port=sys.argv[1]; base=f"http://127.0.0.1:{port}"; token=os.environ["GARCAR_OPERATOR_TOKEN"]
conn=sqlite3.connect(os.environ["GARCAR_LEDGER_PATH"])
job_id=conn.execute("SELECT job_id FROM jobs ORDER BY seq DESC LIMIT 1").fetchone()[0]
conn.close()
for _ in range(30):
    req=urllib.request.Request(base+"/v1/jobs/"+job_id,headers={"Authorization":"Bearer "+token})
    with urllib.request.urlopen(req,timeout=5) as response:
        job=json.loads(response.read())["job"]
    if job["status"] == "succeeded":
        break
    time.sleep(0.5)
else:
    raise SystemExit("FAIL: separate worker did not complete job")
req=urllib.request.Request(base+"/v1/ledger/verify",headers={"Authorization":"Bearer "+token})
with urllib.request.urlopen(req,timeout=5) as response:
    verification=json.loads(response.read())
if not verification["valid"]:
    raise SystemExit("FAIL: ledger chain invalid")
print(json.dumps({"job_status":job["status"],"worker_id":job["worker_id"],"ledger":verification},indent=2))
PY
echo 'END-TO-END SMOKE PASSED.'
