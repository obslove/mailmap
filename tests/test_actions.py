from mailmap.actions import default_target_services, parse_service_selection, recommend_action
from mailmap.models import ServiceEvidence, ServiceRecord


def _record(name: str, status: str) -> ServiceRecord:
    return ServiceRecord(
        canonical_name=name,
        associated_domains=[],
        confidence=50,
        status=status,
        categories=["unknown"],
        total_related_emails=1,
        first_seen=None,
        last_seen=None,
        evidence_summary="",
        representative_senders=[],
        representative_subject_lines=[],
        reasoning=[],
        ambiguity_notes=[],
    )


def test_default_target_services_prefers_low_priority_statuses() -> None:
    records = [_record("A", "account-confirmed"), _record("B", "newsletter-only"), _record("C", "weak-signal")]
    assert default_target_services(records) == ["B", "C"]


def test_parse_service_selection_matches_by_name() -> None:
    records = [_record("Pinterest", "likely-account"), _record("Spotify", "likely-account")]
    assert parse_service_selection("spotify", records) == ["Spotify"]


def test_recommend_action_marks_marketing_heavy_streams() -> None:
    record = _record("Pinterest", "likely-account")
    evidence = ServiceEvidence(canonical_name="Pinterest")
    evidence.internal_flags.add("marketing-heavy")
    action, reason = recommend_action(record, evidence)
    assert action == "keep-but-mute"
    assert "marketing" in reason.lower()
