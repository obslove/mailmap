from datetime import UTC, datetime

from mailmap.evidence import infer_message_candidates
from mailmap.models import MailboxMessage


def test_evidence_finds_candidates_and_signals() -> None:
    message = MailboxMessage(
        uid=1,
        mailbox="INBOX",
        message_id="<1@example>",
        subject="Please verify email",
        sent_at=datetime(2025, 1, 1, tzinfo=UTC),
        from_name="GitHub",
        from_address="noreply@github.com",
        text_body="Please verify email and manage your account.",
        html_body="",
        urls=["https://github.com/settings/security"],
        linked_domains=["github.com"],
        list_id="notifications.github.com",
    )
    candidates, signals, categories = infer_message_candidates(message, quick=False)
    assert candidates["GitHub"] >= 1
    assert any(signal.kind == "security" for signal in signals)
    assert "developer" in categories
