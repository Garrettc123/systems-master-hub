from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ActionRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Disposition(str, Enum):
    AUTO = "auto"
    APPROVAL = "approval"
    REJECT = "reject"


@dataclass(frozen=True)
class GovernedDecision:
    disposition: Disposition
    reason: str


# External side effects are classified explicitly. Production adapters must not
# bypass this governor.
RISK: dict[str, ActionRisk] = {
    "qualify": ActionRisk.LOW,
    "notify": ActionRisk.LOW,
    "assign": ActionRisk.MEDIUM,
    "message": ActionRisk.MEDIUM,
    "follow_up": ActionRisk.MEDIUM,
    "book": ActionRisk.HIGH,
    "payment": ActionRisk.CRITICAL,
    "refund": ActionRisk.CRITICAL,
}


def govern(action_type: str, approved: bool = False) -> GovernedDecision:
    risk = RISK.get(action_type, ActionRisk.CRITICAL)
    if risk is ActionRisk.CRITICAL:
        return GovernedDecision(Disposition.APPROVAL, "critical or unknown action requires explicit approval")
    if risk is ActionRisk.HIGH and not approved:
        return GovernedDecision(Disposition.APPROVAL, "high-impact external action requires approval")
    if risk is ActionRisk.MEDIUM and not approved:
        return GovernedDecision(Disposition.APPROVAL, "external side effect requires approval")
    return GovernedDecision(Disposition.AUTO, "policy permits execution")