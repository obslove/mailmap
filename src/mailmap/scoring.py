from __future__ import annotations

from collections import Counter

from mailmap.models import ServiceEvidence, ServiceRecord

SIGNAL_CAPS = {
    "security": 42,
    "billing": 32,
    "account": 24,
    "newsletter": 8,
    "mailing-list": 4,
    "auth": 4,
    "sender-domain": 8,
    "link-domain": 6,
}


def _status_for_score(
    score: int,
    *,
    security_count: int,
    billing_count: int,
    account_count: int,
    weak_only: bool,
    ambiguous: bool,
    marketing_heavy: bool,
) -> str:
    if ambiguous:
        return "ambiguous"
    if marketing_heavy and score >= 60:
        return "likely-account"
    if score >= 78 and (
        (security_count >= 1 and account_count >= 1)
        or (billing_count >= 1 and account_count >= 1)
        or security_count >= 2
        or billing_count >= 2
    ):
        return "account-confirmed"
    if weak_only:
        return "newsletter-only"
    if score >= 60 and (security_count >= 1 or billing_count >= 1 or account_count >= 1):
        return "likely-account"
    return "weak-signal"


def score_service(name: str, evidence: ServiceEvidence) -> ServiceRecord:
    score = 0
    reasoning: list[str] = []
    signal_counter = Counter()
    signal_points = Counter()
    for signal in evidence.signals:
        signal_counter[signal.kind] += 1
        weight = signal.weight
        if signal.kind in {"security", "billing"} and signal_counter[signal.kind] > 2:
            weight = max(8, weight // 2)
        elif signal.kind in {"newsletter", "mailing-list", "link-domain", "auth", "sender-domain"} and signal_counter[signal.kind] > 3:
            weight = max(2, weight // 2)
        signal_points[signal.kind] += weight
        if len(reasoning) < 8:
            reasoning.append(signal.reason)

    for kind, points in signal_points.items():
        score += min(points, SIGNAL_CAPS.get(kind, points))

    if len(evidence.message_uids) >= 3:
        score += 6
        reasoning.append("Recurring presence across at least 3 messages")
    if len(evidence.message_uids) >= 10:
        score += 4
        reasoning.append("Long-running recurrence across at least 10 messages")
    if len(evidence.domains) >= 2:
        score += 5
        reasoning.append("Multiple corroborating domains attributed to the same service")
    elif len(evidence.domains) == 1 and signal_counter["sender-domain"] >= 1:
        score += 5
        reasoning.append("Sender domain aligns with the canonical service domain")

    security_count = len(evidence.security_messages) or signal_counter["security"]
    billing_count = len(evidence.billing_messages) or signal_counter["billing"]
    account_count = len(evidence.account_messages) or signal_counter["account"]
    newsletter_count = len(evidence.newsletter_messages) or (
        signal_counter["newsletter"] + signal_counter["mailing-list"]
    )
    total_messages = len(evidence.message_uids)
    strong_message_count = len(evidence.security_messages | evidence.billing_messages | evidence.account_messages)
    strong_ratio = (strong_message_count / total_messages) if total_messages else 0.0
    newsletter_ratio = (newsletter_count / total_messages) if total_messages else 0.0
    has_strong = security_count + billing_count + account_count
    if security_count >= 1 and account_count >= 1:
        score += 15
        reasoning.append("Security and account lifecycle evidence corroborate the same service")
    elif billing_count >= 1 and account_count >= 1:
        score += 12
        reasoning.append("Billing and account lifecycle evidence corroborate the same service")
    medium_signals = signal_counter["sender-domain"] + signal_counter["link-domain"] + signal_counter["auth"]
    mailing_bias = newsletter_count
    weak_only = has_strong == 0 and mailing_bias > 0
    ambiguous = bool(evidence.ambiguous_reasons)
    if has_strong == 0 and mailing_bias >= 2 and mailing_bias >= medium_signals:
        score = min(score, 42)
        reasoning.append("Mailing-list and newsletter evidence dominates without account-level confirmation")
    elif has_strong == 0:
        score = min(score, 55)
        reasoning.append("Only domain and recurrence evidence found without account-level confirmation")
    if weak_only:
        score = min(score, 45)
    if ambiguous:
        score = min(score, 58)
        reasoning.extend(sorted(evidence.ambiguous_reasons)[:3])
    marketing_heavy = (
        total_messages >= 12
        and newsletter_ratio >= 0.55
        and strong_ratio < 0.20
    )
    if marketing_heavy:
        evidence.internal_flags.add("marketing-heavy")
        score = min(score, 74)
        reasoning.append("Marketing-heavy stream dominates the evidence relative to strong account messages")
    if total_messages >= 25 and strong_ratio < 0.10:
        score = min(score, 69)
        reasoning.append("Very low ratio of strong account evidence compared with total message volume")
    elif total_messages >= 10 and strong_ratio < 0.20 and newsletter_ratio >= 0.40:
        score = min(score, 74)
        reasoning.append("Strong account evidence is present but sparse relative to marketing volume")
    if newsletter_count >= 10 and security_count == 0 and billing_count == 0:
        score = min(score, 55)
        reasoning.append("Large marketing/newsletter volume without security or billing evidence")
    elif newsletter_count >= 10 and (security_count + billing_count) <= 2:
        score = min(score, 74)
        reasoning.append("Marketing-heavy stream with limited strong account evidence")
    if security_count == 0 and billing_count == 0 and account_count >= 1:
        score = min(score, 82)
        reasoning.append("Only account-lifecycle language was found without security or billing confirmation")
    if has_strong < 2:
        score = min(score, 92)
    if has_strong == 0:
        score = min(score, 60)

    score = max(0, min(score, 100))
    status = _status_for_score(
        score,
        security_count=security_count,
        billing_count=billing_count,
        account_count=account_count,
        weak_only=weak_only,
        ambiguous=ambiguous,
        marketing_heavy=marketing_heavy,
    )
    summary_parts = []
    if has_strong:
        summary_parts.append(f"{has_strong} messages with strong transactional/security/account signals")
    if newsletter_count:
        summary_parts.append(f"{newsletter_count} newsletter-style messages")
    summary_parts.append(f"{len(evidence.message_uids)} related messages")
    evidence_summary = ", ".join(summary_parts)

    return ServiceRecord(
        canonical_name=name,
        associated_domains=sorted(evidence.domains),
        confidence=score,
        status=status,
        categories=sorted(evidence.categories) or ["unknown"],
        total_related_emails=len(evidence.message_uids),
        first_seen=evidence.first_seen.date().isoformat() if evidence.first_seen else None,
        last_seen=evidence.last_seen.date().isoformat() if evidence.last_seen else None,
        evidence_summary=evidence_summary,
        representative_senders=sorted(evidence.representative_senders)[:5],
        representative_subject_lines=sorted(evidence.representative_subjects)[:5],
        reasoning=reasoning,
        ambiguity_notes=sorted(evidence.ambiguous_reasons),
    )
