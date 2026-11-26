"""Fail-closed outreach compliance gate. Pure logic: no network, no sends.

Conservative defaults; have counsel confirm before enabling any live channel.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DNC_MAX_AGE = timedelta(days=31)


@dataclass
class Contact:
    contact_id: str
    timezone: str = "America/Chicago"
    suppressed: bool = False
    sms_consent_at: datetime | None = None
    sms_consent_text: str = ""
    dnc_scrubbed_at: datetime | None = None
    is_cell: bool = False


@dataclass
class Message:
    channel: str  # "email" | "sms" | "call"
    body: str = ""
    sender_postal_address: str = ""
    unsubscribe_link: str = ""
    approved_by: str = ""


@dataclass
class Decision:
    allowed: bool
    reasons: list = field(default_factory=list)


def check(contact: Contact, msg: Message, now: datetime) -> Decision:
    reasons = []
    if msg.channel not in {"email", "sms", "call"}:
        return Decision(False, ["unknown_channel"])
    if contact.suppressed:
        reasons.append("contact_suppressed")
    if not msg.approved_by:
        reasons.append("human_approval_missing")
    if msg.channel == "email":
        if not msg.sender_postal_address:
            reasons.append("email_missing_postal_address")
        if not msg.unsubscribe_link:
            reasons.append("email_missing_unsubscribe")
    else:
        local = now.astimezone(ZoneInfo(contact.timezone))
        earliest = 12 if local.weekday() == 6 else 9
        if not (earliest <= local.hour < 21):
            reasons.append("outside_calling_hours")
        if contact.dnc_scrubbed_at is None or now - contact.dnc_scrubbed_at > DNC_MAX_AGE:
            reasons.append("dnc_scrub_stale_or_missing")
    if msg.channel == "sms" and (contact.sms_consent_at is None or not contact.sms_consent_text):
        reasons.append("sms_prior_written_consent_missing")
    if msg.channel == "call" and contact.is_cell:
        reasons.append("cell_call_requires_manual_review")
    return Decision(not reasons, reasons)
