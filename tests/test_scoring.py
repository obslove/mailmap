from mailmap.models import MessageSignal, ServiceEvidence
from mailmap.scoring import score_service


def test_confirmed_service_scores_high() -> None:
    evidence = ServiceEvidence(
        canonical_name="GitHub",
        domains={"github.com"},
        categories={"developer"},
        signals=[
            MessageSignal("security", 28, "verify email"),
            MessageSignal("account", 18, "account created"),
            MessageSignal("sender-domain", 10, "github.com"),
        ],
        message_uids={("INBOX", 1), ("INBOX", 2), ("INBOX", 3)},
    )
    record = score_service("GitHub", evidence)
    assert record.status == "account-confirmed"
    assert record.confidence >= 80


def test_ambiguous_service_is_capped() -> None:
    evidence = ServiceEvidence(
        canonical_name="Example",
        domains={"example.com"},
        categories={"unknown"},
        signals=[MessageSignal("newsletter", 8, "newsletter")],
        message_uids={("INBOX", 1)},
        ambiguous_reasons={"Multiple candidates"},
    )
    record = score_service("Example", evidence)
    assert record.status == "ambiguous"
    assert record.confidence <= 58


def test_newsletter_heavy_service_is_downgraded() -> None:
    evidence = ServiceEvidence(
        canonical_name="SHEIN",
        domains={"sheinemail.com"},
        categories={"shopping"},
        signals=[
            MessageSignal("mailing-list", 2, "list unsubscribe"),
            MessageSignal("mailing-list", 2, "list id"),
            MessageSignal("auth", 2, "dkim"),
            MessageSignal("sender-domain", 6, "sender domain"),
        ],
        message_uids={("INBOX", 1), ("INBOX", 2), ("INBOX", 3), ("INBOX", 4)},
    )
    record = score_service("SHEIN", evidence)
    assert record.status in {"newsletter-only", "weak-signal"}
    assert record.confidence <= 45


def test_marketing_heavy_stream_with_sparse_strong_evidence_is_not_confirmed() -> None:
    evidence = ServiceEvidence(
        canonical_name="Pinterest",
        domains={"pinterest.com"},
        categories={"social"},
        signals=[
            MessageSignal("security", 28, "verification code"),
            MessageSignal("account", 18, "your account"),
            MessageSignal("sender-domain", 6, "sender domain"),
            MessageSignal("newsletter", 8, "unsubscribe"),
            MessageSignal("mailing-list", 2, "list unsubscribe"),
        ],
        message_uids={( "INBOX", index) for index in range(1, 51)},
        security_messages={( "INBOX", 1), ("INBOX", 2)},
        account_messages={( "INBOX", 1), ("INBOX", 2), ("INBOX", 3)},
        newsletter_messages={( "INBOX", index) for index in range(1, 41)},
    )
    record = score_service("Pinterest", evidence)
    assert record.status == "likely-account"
    assert record.confidence <= 74
