from __future__ import annotations

import logging
import os
import socket
import time

from app.ledger import EventLedger

logging.basicConfig(level=os.getenv("GARCAR_LOG_LEVEL", "INFO"))
LOG = logging.getLogger("garcar-forge.worker")


def process_one(ledger: EventLedger, worker_id: str, lease_seconds: int = 300) -> bool:
    job = ledger.claim_job(worker_id, lease_seconds=lease_seconds)
    if job is None:
        return False
    job_id = job["job_id"]
    try:
        if job["task_name"] != "ledger.verify":
            raise ValueError("task_not_allowlisted")
        result = ledger.verify()
        if not result["valid"]:
            ledger.fail_job(job_id, worker_id, "ledger_integrity_check_failed")
        elif not ledger.finish_job(job_id, worker_id, result):
            raise RuntimeError("job_ownership_lost")
    except Exception as exc:
        ledger.fail_job(job_id, worker_id, "worker_task_failed")
        LOG.exception("job processing failed: %s (%s)", job_id, type(exc).__name__)
    return True


def main() -> None:
    path = os.getenv("GARCAR_LEDGER_PATH", "./data/garcar-forge.sqlite3")
    poll_seconds = max(1.0, float(os.getenv("GARCAR_WORKER_POLL_SECONDS", "3")))
    lease_seconds = max(30, int(os.getenv("GARCAR_WORKER_LEASE_SECONDS", "300")))
    worker_id = os.getenv("GARCAR_WORKER_ID", socket.gethostname())[:128]
    ledger = EventLedger(path)
    LOG.info("worker online: %s; allowlisted task=ledger.verify only", worker_id)
    while True:
        if not process_one(ledger, worker_id, lease_seconds):
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
