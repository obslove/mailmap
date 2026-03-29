from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class MailboxMessage:
    uid: int
    mailbox: str
    message_id: str | None
    subject: str
    sent_at: datetime | None
    from_name: str | None
    from_address: str | None
    reply_to: list[str] = field(default_factory=list)
    return_path: str | None = None
    authentication_results: str | None = None
    list_id: str | None = None
    list_unsubscribe: str | None = None
    precedence: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    text_body: str = ""
    html_body: str = ""
    urls: list[str] = field(default_factory=list)
    linked_domains: list[str] = field(default_factory=list)


@dataclass(slots=True)
class MessageSignal:
    kind: str
    weight: int
    reason: str
    value: str | None = None


@dataclass(slots=True)
class ServiceEvidence:
    canonical_name: str
    domains: set[str] = field(default_factory=set)
    categories: set[str] = field(default_factory=set)
    signals: list[MessageSignal] = field(default_factory=list)
    message_uids: set[tuple[str, int]] = field(default_factory=set)
    security_messages: set[tuple[str, int]] = field(default_factory=set)
    billing_messages: set[tuple[str, int]] = field(default_factory=set)
    account_messages: set[tuple[str, int]] = field(default_factory=set)
    newsletter_messages: set[tuple[str, int]] = field(default_factory=set)
    representative_senders: set[str] = field(default_factory=set)
    representative_subjects: set[str] = field(default_factory=set)
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    ambiguous_reasons: set[str] = field(default_factory=set)
    internal_flags: set[str] = field(default_factory=set)


@dataclass(slots=True)
class ServiceRecord:
    canonical_name: str
    associated_domains: list[str]
    confidence: int
    status: str
    categories: list[str]
    total_related_emails: int
    first_seen: str | None
    last_seen: str | None
    evidence_summary: str
    representative_senders: list[str]
    representative_subject_lines: list[str]
    reasoning: list[str]
    ambiguity_notes: list[str]
    recommended_action: str = "review"


@dataclass(slots=True)
class RunStats:
    folders_considered: int = 0
    folders_scanned: int = 0
    total_uids_seen: int = 0
    processed_this_run: int = 0
    reused_from_cache: int = 0
    parse_failures: int = 0
    fetch_failures: int = 0
    detected_services: int = 0
