from datetime import datetime, timezone

import pytest

from revenue.garcar_core.governor import Disposition, govern
from revenue.garcar_core.metrics import LeadMetrics, elapsed_seconds, metric_snapshot
from revenue.garcar_core.reliability import RetryPolicy, should_dead_letter
from revenue.garcar_core.state import LeadStatus, transition


def test_valid_state_transition_requires_reason() -> None:
    t = transition("lead_1", "tenant_1", LeadStatus.QUALIFYING, LeadStatus.ASSIGNED, "owner matched")
    assert t.after is LeadStatus.ASSIGNED
    with pytest.raises(ValueError):
        transition("lead_1", "tenant_1", LeadStatus.WON, LeadStatus.ASSIGNED, "bad")


def test_governor_blocks_unapproved_side_effects() -> None:
    assert govern("message").disposition is Disposition.APPROVAL
    assert govern("book").disposition is Disposition.APPROVAL
    assert govern("payment").disposition is Disposition.APPROVAL
    assert govern("message", approved=True).disposition is Disposition.AUTO


def test_retry_dead_letter_boundary() -> None:
    policy = RetryPolicy(max_attempts=3)
    assert not should_dead_letter(2, policy)
    assert should_dead_letter(3, policy)


def test_metrics_are_observable() -> None:
    start = datetime(2026, 9, 15, tzinfo=timezone.utc)
    end = datetime(2026, 9, 15, 0, 0, 30, tzinfo=timezone.utc)
    assert elapsed_seconds(start, end) == 30
    snapshot = metric_snapshot(LeadMetrics("t", "l", start, first_response_at=end))
    assert snapshot["first_response_seconds"] == 30
