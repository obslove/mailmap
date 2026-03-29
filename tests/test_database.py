from datetime import UTC, datetime

from mailmap.database import CacheDB
from mailmap.models import MailboxMessage


def test_cache_roundtrip(tmp_path) -> None:
    db = CacheDB(tmp_path / "cache.sqlite3")
    message = MailboxMessage(
        uid=1,
        mailbox="INBOX",
        message_id="<1@example>",
        subject="Subject",
        sent_at=datetime(2025, 1, 1, tzinfo=UTC),
        from_name="Sender",
        from_address="sender@example.com",
        text_body="body",
        html_body="",
        urls=["https://example.com"],
        linked_domains=["example.com"],
    )
    db.store_message(message)
    loaded = db.load_message("INBOX", 1)
    assert loaded is not None
    assert loaded.subject == "Subject"
    assert db.has_processed("INBOX", 1) is True
