from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum


class ActionState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    RETRY = "retry"
    DEAD_LETTER = "dead_letter"


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: int = 5
    max_delay_seconds: int = 300

    def delay(self, attempt: int) -> int:
        if attempt < 1:
            return 0
        return min(self.max_delay_seconds, self.base_delay_seconds * (2 ** (attempt - 1)))


def next_retry_at(now: datetime | None, attempt: int, policy: RetryPolicy) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now + timedelta(seconds=policy.delay(attempt))


def should_dead_letter(attempt: int, policy: RetryPolicy) -> bool:
    return attempt >= policy.max_attempts


@dataclass(frozen=True)
class SLOSnapshot:
    total_leads: int
    responded_within_target: int
    stale_leads: int
    failed_actions: int

    @property
    def response_target_rate(self) -> float:
        return self.responded_within_target / self.total_leads if self.total_leads else 0.0

    @property
    def action_failure_rate(self) -> float:
        return self.failed_actions / self.total_leads if self.total_leads else 0.0