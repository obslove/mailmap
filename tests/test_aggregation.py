from datetime import UTC, datetime

from mailmap.aggregation import aggregate_messages
from mailmap.models import MailboxMessage


def _message(uid: int, subject: str, sender: str, text: str) -> MailboxMessage:
    return MailboxMessage(
        uid=uid,
        mailbox="INBOX",
        message_id=f"<{uid}@example>",
        subject=subject,
        sent_at=datetime(2025, 1, uid, tzinfo=UTC),
        from_name="Sender",
        from_address=sender,
        text_body=text,
        html_body="",
        linked_domains=[],
        urls=[],
    )


def test_aggregation_deduplicates_service_identity() -> None:
    records, _ = aggregate_messages(
        [
            _message(1, "Verify email", "noreply@mail.github.com", "Please verify email"),
            _message(2, "Password reset", "alerts@github.com", "password reset"),
        ],
        quick=False,
    )
    assert len(records) == 1
    assert records[0].canonical_name == "GitHub"
    assert records[0].total_related_emails == 2
