from __future__ import annotations

from datetime import datetime
from email import policy
from email.header import decode_header, make_header
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime

from mailmap.content import clean_text, extract_from_html, extract_urls_from_text, meaningful_link_domains
from mailmap.models import MailboxMessage

HEADER_NAMES = [
    "Authentication-Results",
    "List-ID",
    "List-Unsubscribe",
    "Precedence",
    "X-Mailgun-Variables",
    "X-SES-Outgoing",
    "X-SG-EID",
]


def decode_mime_header(value: str | None) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return value


def _addresses(message: EmailMessage, header: str) -> list[tuple[str, str]]:
    values = message.get_all(header, [])
    return [(decode_mime_header(name), address.lower()) for name, address in getaddresses(values)]


def _extract_bodies(message: EmailMessage) -> tuple[str, str]:
    text_parts: list[str] = []
    html_parts: list[str] = []
    for part in message.walk():
        if part.is_multipart():
            continue
        content_type = part.get_content_type()
        disposition = (part.get_content_disposition() or "").lower()
        if disposition == "attachment":
            continue
        try:
            payload = part.get_payload(decode=True) or b""
            charset = part.get_content_charset() or "utf-8"
            decoded = payload.decode(charset, errors="replace")
        except Exception:
            decoded = (part.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
        if content_type == "text/plain":
            text_parts.append(decoded)
        elif content_type == "text/html":
            html_parts.append(decoded)
    return "\n".join(text_parts), "\n".join(html_parts)


def parse_message(raw_bytes: bytes, *, uid: int, mailbox: str) -> MailboxMessage:
    parsed = BytesParser(policy=policy.default).parsebytes(raw_bytes)
    from_addrs = _addresses(parsed, "From")
    reply_to = [addr for _, addr in _addresses(parsed, "Reply-To")]
    sender_name, sender_addr = ("", "")
    if from_addrs:
        sender_name, sender_addr = from_addrs[0]
    text_body, html_body = _extract_bodies(parsed)
    html_text, html_urls = extract_from_html(html_body)
    text_urls = extract_urls_from_text(text_body)
    all_urls = list(dict.fromkeys(text_urls + html_urls))
    sent_at: datetime | None = None
    date_header = parsed.get("Date")
    if date_header:
        try:
            sent_at = parsedate_to_datetime(date_header)
        except Exception:
            sent_at = None
    message = MailboxMessage(
        uid=uid,
        mailbox=mailbox,
        message_id=decode_mime_header(parsed.get("Message-ID")),
        subject=decode_mime_header(parsed.get("Subject")),
        sent_at=sent_at,
        from_name=sender_name or None,
        from_address=sender_addr or None,
        reply_to=reply_to,
        return_path=decode_mime_header(parsed.get("Return-Path")) or None,
        authentication_results=decode_mime_header(parsed.get("Authentication-Results")) or None,
        list_id=decode_mime_header(parsed.get("List-ID")) or None,
        list_unsubscribe=decode_mime_header(parsed.get("List-Unsubscribe")) or None,
        precedence=decode_mime_header(parsed.get("Precedence")) or None,
        headers={name: decode_mime_header(parsed.get(name)) for name in HEADER_NAMES if parsed.get(name)},
        text_body=clean_text(text_body),
        html_body=clean_text(html_text),
        urls=all_urls,
        linked_domains=meaningful_link_domains(all_urls),
    )
    return message
