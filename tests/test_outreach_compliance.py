from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from governance.outreach_compliance import Contact, Message, check

CT = ZoneInfo("America/Chicago")
NOON_THU = datetime(2026, 11, 26, 12, 0, tzinfo=CT)


def ok_email():
    return Message("email", "hi", "1 Main St, Cleburne TX", "https://x/unsub", "garrett")


def test_email_allowed_with_footer_and_approval():
    assert check(Contact("c1"), ok_email(), NOON_THU).allowed


def test_suppressed_blocked():
    assert "contact_suppressed" in check(Contact("c1", suppressed=True), ok_email(), NOON_THU).reasons


def test_email_without_unsubscribe_blocked():
    m = ok_email(); m.unsubscribe_link = ""
    assert "email_missing_unsubscribe" in check(Contact("c1"), m, NOON_THU).reasons


def test_no_approval_blocked():
    m = ok_email(); m.approved_by = ""
    assert not check(Contact("c1"), m, NOON_THU).allowed


def test_sms_needs_consent_and_dnc():
    r = check(Contact("c1"), Message("sms", "hi", approved_by="g"), NOON_THU).reasons
    assert "sms_prior_written_consent_missing" in r and "dnc_scrub_stale_or_missing" in r


def test_sms_allowed_with_consent_and_fresh_scrub():
    c = Contact("c1", sms_consent_at=NOON_THU, sms_consent_text="I agree", dnc_scrubbed_at=NOON_THU - timedelta(days=5))
    assert check(c, Message("sms", "hi", approved_by="g"), NOON_THU).allowed


def test_night_blocked():
    c = Contact("c1", dnc_scrubbed_at=NOON_THU)
    late = datetime(2026, 11, 26, 21, 30, tzinfo=CT)
    assert "outside_calling_hours" in check(c, Message("call", approved_by="g"), late).reasons


def test_sunday_morning_blocked():
    c = Contact("c1", dnc_scrubbed_at=datetime(2026, 11, 29, 8, tzinfo=CT))
    sun = datetime(2026, 11, 29, 10, 0, tzinfo=CT)
    assert "outside_calling_hours" in check(c, Message("call", approved_by="g"), sun).reasons
