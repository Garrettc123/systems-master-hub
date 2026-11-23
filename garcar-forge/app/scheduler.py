from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone

from app.ledger import EventLedger

logging.basicConfig(level=os.getenv("GARCAR_LOG_LEVEL", "INFO"))
LOG = logging.getLogger("garcar-forge.scheduler")


def main() -> None:
    path = os.getenv("GARCAR_LEDGER_PATH", "./data/garcar-forge.sqlite3")
    enabled = os.getenv("GARCAR_SCHEDULER_ENABLED", "false").lower() == "true"
    interval = max(60, int(os.getenv("GARCAR_SCHEDULER_INTERVAL_SECONDS", "300")))
    ledger = EventLedger(path)
    LOG.info("scheduler online; enabled=%s; safe task=ledger.verify; interval=%ss", enabled, interval)
    if not enabled:
        while True:
            time.sleep(3600)
    while True:
        slot = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M")
        job, created, _ = ledger.enqueue("ledger.verify", f"scheduled-ledger-verify:{slot}", {})
        if created:
            LOG.info("queued scheduled ledger verification job %s", job["job_id"])
        time.sleep(interval)


if __name__ == "__main__":
    main()
