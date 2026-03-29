from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from mailmap.models import MailboxMessage


SCHEMA = """
CREATE TABLE IF NOT EXISTS run_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    quick_mode INTEGER NOT NULL,
    since_date TEXT,
    total_seen INTEGER DEFAULT 0,
    processed_count INTEGER DEFAULT 0,
    cached_count INTEGER DEFAULT 0,
    service_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS processed_messages (
    mailbox TEXT NOT NULL,
    uid INTEGER NOT NULL,
    message_id TEXT,
    sent_at TEXT,
    sender TEXT,
    subject TEXT,
    parsed_payload TEXT NOT NULL,
    PRIMARY KEY (mailbox, uid)
);

CREATE TABLE IF NOT EXISTS extracted_signals (
    mailbox TEXT NOT NULL,
    uid INTEGER NOT NULL,
    signal_kind TEXT NOT NULL,
    signal_reason TEXT NOT NULL,
    signal_value TEXT
);

CREATE TABLE IF NOT EXISTS urls (
    mailbox TEXT NOT NULL,
    uid INTEGER NOT NULL,
    url TEXT NOT NULL,
    domain TEXT
);

CREATE TABLE IF NOT EXISTS domains (
    mailbox TEXT NOT NULL,
    uid INTEGER NOT NULL,
    domain TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS service_candidates (
    mailbox TEXT NOT NULL,
    uid INTEGER NOT NULL,
    candidate TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS canonical_services (
    canonical_name TEXT PRIMARY KEY,
    last_score INTEGER,
    last_status TEXT,
    updated_at TEXT NOT NULL
);
"""


class CacheDB:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def has_processed(self, mailbox: str, uid: int) -> bool:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM processed_messages WHERE mailbox = ? AND uid = ?",
                (mailbox, uid),
            ).fetchone()
        return row is not None

    def load_message(self, mailbox: str, uid: int) -> MailboxMessage | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT parsed_payload FROM processed_messages WHERE mailbox = ? AND uid = ?",
                (mailbox, uid),
            ).fetchone()
        if not row:
            return None
        payload = json.loads(row[0])
        if payload.get("sent_at"):
            payload["sent_at"] = datetime.fromisoformat(payload["sent_at"])
        return MailboxMessage(**payload)

    def store_message(self, message: MailboxMessage) -> None:
        payload = json.dumps(
            {
                "uid": message.uid,
                "mailbox": message.mailbox,
                "message_id": message.message_id,
                "subject": message.subject,
                "sent_at": message.sent_at.isoformat() if message.sent_at else None,
                "from_name": message.from_name,
                "from_address": message.from_address,
                "reply_to": message.reply_to,
                "return_path": message.return_path,
                "authentication_results": message.authentication_results,
                "list_id": message.list_id,
                "list_unsubscribe": message.list_unsubscribe,
                "precedence": message.precedence,
                "headers": message.headers,
                "text_body": message.text_body,
                "html_body": message.html_body,
                "urls": message.urls,
                "linked_domains": message.linked_domains,
            }
        )
        with self.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO processed_messages
                (mailbox, uid, message_id, sent_at, sender, subject, parsed_payload)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.mailbox,
                    message.uid,
                    message.message_id,
                    message.sent_at.isoformat() if message.sent_at else None,
                    message.from_address,
                    message.subject,
                    payload,
                ),
            )

    def begin_run(self, *, started_at: str, quick_mode: bool, since_date: str | None) -> int:
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO run_history (started_at, quick_mode, since_date)
                VALUES (?, ?, ?)
                """,
                (started_at, int(quick_mode), since_date),
            )
            return int(cursor.lastrowid)

    def finish_run(
        self,
        run_id: int,
        *,
        finished_at: str,
        total_seen: int,
        processed_count: int,
        cached_count: int,
        service_count: int,
    ) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE run_history
                SET finished_at = ?, total_seen = ?, processed_count = ?, cached_count = ?, service_count = ?
                WHERE id = ?
                """,
                (finished_at, total_seen, processed_count, cached_count, service_count, run_id),
            )
