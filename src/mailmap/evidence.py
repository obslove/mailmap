from __future__ import annotations

from collections import Counter
import re
from email.utils import parseaddr

from mailmap.domains import (
    canonical_service_for_domain,
    category_for_service,
    is_infrastructure_domain,
    meaningful_domain,
    registrable_domain,
)
from mailmap.fingerprints import ACCOUNT_PATTERNS, BILLING_PATTERNS, NEWSLETTER_PATTERNS, SECURITY_PATTERNS
from mailmap.models import MailboxMessage, MessageSignal


def _contains_any(haystack: str, patterns: list[str]) -> list[str]:
    lower = haystack.lower()
    return [pattern for pattern in patterns if pattern in lower]


def _brand_from_list_id(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"([a-z0-9.-]+\.[a-z]{2,})", value.lower())
    if not match:
        return None
    return canonical_service_for_domain(match.group(1))


def infer_message_candidates(message: MailboxMessage, *, quick: bool) -> tuple[Counter[str], list[MessageSignal], set[str]]:
    candidates: Counter[str] = Counter()
    categories: set[str] = set()
    sender_domain = meaningful_domain(message.from_address)
    if sender_domain and not is_infrastructure_domain(sender_domain):
        sender_service = canonical_service_for_domain(sender_domain)
        if sender_service:
            candidates[sender_service] += 3
            categories.add(category_for_service(sender_service))

    for domain in message.linked_domains[: (4 if quick else 8)]:
        service = canonical_service_for_domain(domain)
        if service:
            candidates[service] += 1
            categories.add(category_for_service(service))

    list_service = _brand_from_list_id(message.list_id)
    if list_service:
        candidates[list_service] += 2
        categories.add(category_for_service(list_service))

    signals: list[MessageSignal] = []
    combined_text = " ".join(
        part for part in [message.subject, message.text_body[:4000], message.html_body[:4000]] if part
    )
    for pattern in _contains_any(combined_text, SECURITY_PATTERNS):
        signals.append(MessageSignal("security", 28, f"Security phrase matched: {pattern}", pattern))
    for pattern in _contains_any(combined_text, BILLING_PATTERNS):
        signals.append(MessageSignal("billing", 22, f"Billing phrase matched: {pattern}", pattern))
    for pattern in _contains_any(combined_text, ACCOUNT_PATTERNS):
        signals.append(MessageSignal("account", 18, f"Account phrase matched: {pattern}", pattern))
    for pattern in _contains_any(combined_text, NEWSLETTER_PATTERNS):
        signals.append(MessageSignal("newsletter", 8, f"Newsletter phrase matched: {pattern}", pattern))

    if message.list_unsubscribe:
        signals.append(MessageSignal("mailing-list", 2, "List-Unsubscribe header present"))
    if message.list_id:
        signals.append(MessageSignal("mailing-list", 2, "List-ID header present"))
    if message.authentication_results and "dkim=pass" in message.authentication_results.lower():
        signals.append(MessageSignal("auth", 2, "DKIM pass present in Authentication-Results"))
    if message.from_address:
        _, raw = parseaddr(message.from_address)
        if raw:
            domain = registrable_domain(raw.split("@")[-1])
            if domain and not is_infrastructure_domain(domain):
                signals.append(MessageSignal("sender-domain", 6, f"Sender domain observed: {domain}", domain))
    for domain in message.linked_domains[: (2 if quick else 5)]:
        signals.append(MessageSignal("link-domain", 2, f"Meaningful linked domain observed: {domain}", domain))
    return candidates, signals, categories
