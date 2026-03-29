from __future__ import annotations

from collections import defaultdict

from mailmap.domains import canonical_service_for_domain, category_for_service, meaningful_domain
from mailmap.evidence import infer_message_candidates
from mailmap.models import MailboxMessage, ServiceEvidence
from mailmap.scoring import score_service


def build_service_evidence(messages: list[MailboxMessage], *, quick: bool) -> dict[str, ServiceEvidence]:
    by_service: dict[str, ServiceEvidence] = defaultdict(lambda: ServiceEvidence(canonical_name=""))
    for message in messages:
        candidate_scores, signals, categories = infer_message_candidates(message, quick=quick)
        candidates = list(candidate_scores)
        if not candidates:
            continue
        ranked = sorted(candidate_scores.items(), key=lambda item: (-item[1], item[0]))
        chosen = ranked[0][0]
        unique_candidates = set(candidates)
        evidence = by_service[chosen]
        evidence.canonical_name = chosen
        evidence.signals.extend(signals)
        evidence.categories.update(categories or {category_for_service(chosen)})
        message_ref = (message.mailbox, message.uid)
        evidence.message_uids.add(message_ref)
        signal_kinds = {signal.kind for signal in signals}
        if "security" in signal_kinds:
            evidence.security_messages.add(message_ref)
        if "billing" in signal_kinds:
            evidence.billing_messages.add(message_ref)
        if "account" in signal_kinds:
            evidence.account_messages.add(message_ref)
        if "newsletter" in signal_kinds or "mailing-list" in signal_kinds:
            evidence.newsletter_messages.add(message_ref)
        if message.list_unsubscribe or message.list_id:
            evidence.internal_flags.add("marketing-stream")
        if message.sent_at:
            evidence.first_seen = min(filter(None, [evidence.first_seen, message.sent_at]), default=message.sent_at)
            evidence.last_seen = max(filter(None, [evidence.last_seen, message.sent_at]), default=message.sent_at)
        if message.from_address:
            evidence.representative_senders.add(message.from_address)
            domain = meaningful_domain(message.from_address)
            if domain:
                evidence.domains.add(domain)
        if message.subject:
            evidence.representative_subjects.add(message.subject)
        for domain in message.linked_domains:
            service = canonical_service_for_domain(domain)
            if service == chosen:
                evidence.domains.add(domain)
        if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
            evidence.ambiguous_reasons.add(
                f"Message attribution tied across service candidates: {', '.join(sorted(unique_candidates)[:3])}"
            )

    return dict(by_service)


def aggregate_messages(messages: list[MailboxMessage], *, quick: bool) -> tuple[list, dict[str, ServiceEvidence]]:
    by_service = build_service_evidence(messages, quick=quick)
    records = [score_service(name, evidence) for name, evidence in by_service.items()]
    records.sort(key=lambda item: (-item.confidence, -item.total_related_emails, item.canonical_name.lower()))
    return records, by_service
