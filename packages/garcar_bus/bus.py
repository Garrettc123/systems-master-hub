"""
Garcar Event Mesh client.

Backend: Upstash Redis (REST) preferred for serverless / free tier.
Falls back to redis-py URL if UPSTASH_* not set.
Falls back to in-memory queue if no Redis at all (local/dev).

Env vars (any one set is enough):
  UPSTASH_REDIS_REST_URL + UPSTASH_REDIS_REST_TOKEN
  REDIS_URL  (redis://...)
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

Handler = Callable[[dict], None]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class _MemoryBackend:
    def __init__(self) -> None:
        self._streams: Dict[str, List[dict]] = defaultdict(list)
        self._lock = threading.Lock()

    def publish(self, stream: str, payload: dict) -> str:
        eid = f"{int(time.time()*1000)}-{uuid.uuid4().hex[:8]}"
        with self._lock:
            self._streams[stream].append({"id": eid, "data": payload})
            # keep last 5000
            if len(self._streams[stream]) > 5000:
                self._streams[stream] = self._streams[stream][-5000:]
        return eid

    def read(self, stream: str, last_id: str = "0", count: int = 50) -> List[dict]:
        with self._lock:
            items = self._streams.get(stream, [])
            out = []
            for item in items:
                if item["id"] > last_id:
                    out.append(item)
                    if len(out) >= count:
                        break
            return out


class _UpstashBackend:
    """Upstash Redis REST — works from any serverless / Actions runner."""

    def __init__(self, url: str, token: str) -> None:
        self.url = url.rstrip("/")
        self.token = token
        try:
            import requests
            self._requests = requests
        except ImportError as e:
            raise RuntimeError("pip install requests for Upstash backend") from e

    def _cmd(self, *args: str) -> Any:
        r = self._requests.post(
            self.url,
            headers={"Authorization": f"Bearer {self.token}"},
            json=list(args),
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("result")

    def publish(self, stream: str, payload: dict) -> str:
        # XADD stream * data <json>
        data = json.dumps(payload, default=str)
        eid = self._cmd("XADD", stream, "*", "data", data)
        return str(eid)

    def read(self, stream: str, last_id: str = "0", count: int = 50) -> List[dict]:
        # XREAD COUNT n STREAMS stream last_id
        raw = self._cmd("XREAD", "COUNT", str(count), "STREAMS", stream, last_id)
        if not raw:
            return []
        out = []
        for _stream_name, entries in raw:
            for eid, fields in entries:
                # fields is list [key, val, key, val...]
                d = dict(zip(fields[0::2], fields[1::2]))
                payload = json.loads(d.get("data", "{}"))
                out.append({"id": eid, "data": payload})
        return out


class _RedisUrlBackend:
    def __init__(self, url: str) -> None:
        try:
            import redis
            self.r = redis.from_url(url, decode_responses=True)
        except ImportError as e:
            raise RuntimeError("pip install redis for REDIS_URL backend") from e

    def publish(self, stream: str, payload: dict) -> str:
        eid = self.r.xadd(stream, {"data": json.dumps(payload, default=str)})
        return str(eid)

    def read(self, stream: str, last_id: str = "0", count: int = 50) -> List[dict]:
        raw = self.r.xread({stream: last_id}, count=count, block=0)
        out = []
        for _s, entries in raw or []:
            for eid, fields in entries:
                payload = json.loads(fields.get("data", "{}"))
                out.append({"id": eid, "data": payload})
        return out


class Bus:
    """Publish / subscribe across the Garcar organism."""

    STREAM_PREFIX = "garcar."

    def __init__(self) -> None:
        self._backend = self._resolve_backend()
        self._handlers: Dict[str, List[Handler]] = defaultdict(list)
        self._last_ids: Dict[str, str] = {}
        self._poll_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def _resolve_backend(self):
        upstash_url = os.environ.get("UPSTASH_REDIS_REST_URL")
        upstash_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
        if upstash_url and upstash_token:
            return _UpstashBackend(upstash_url, upstash_token)
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            return _RedisUrlBackend(redis_url)
        return _MemoryBackend()

    def publish(self, event_type: str, payload: Optional[dict] = None, **kwargs: Any) -> str:
        """Publish an event. event_type examples: revenue.captured, system.health, upgrade.started"""
        body = dict(payload or {})
        body.update(kwargs)
        body.setdefault("event_type", event_type)
        body.setdefault("ts", _now())
        body.setdefault("id", str(uuid.uuid4()))
        stream = f"{self.STREAM_PREFIX}{event_type}"
        return self._backend.publish(stream, body)

    def subscribe(self, event_type: str, handler: Handler) -> None:
        """Register a handler. Call start_polling() (or run in a long-lived process) to deliver."""
        self._handlers[event_type].append(handler)
        self._last_ids.setdefault(event_type, "0")

    def start_polling(self, interval_sec: float = 1.0) -> None:
        if self._poll_thread and self._poll_thread.is_alive():
            return
        self._stop.clear()

        def _loop() -> None:
            while not self._stop.is_set():
                for event_type, handlers in list(self._handlers.items()):
                    stream = f"{self.STREAM_PREFIX}{event_type}"
                    last = self._last_ids.get(event_type, "0")
                    try:
                        items = self._backend.read(stream, last_id=last, count=50)
                        for item in items:
                            self._last_ids[event_type] = item["id"]
                            for h in handlers:
                                try:
                                    h(item["data"])
                                except Exception as exc:  # never kill the bus
                                    print(f"[garcar_bus] handler error on {event_type}: {exc}")
                    except Exception as exc:
                        print(f"[garcar_bus] read error {event_type}: {exc}")
                self._stop.wait(interval_sec)

        self._poll_thread = threading.Thread(target=_loop, name="garcar-bus-poll", daemon=True)
        self._poll_thread.start()

    def stop_polling(self) -> None:
        self._stop.set()


# Singleton for simple import: from garcar_bus import bus
bus = Bus()
