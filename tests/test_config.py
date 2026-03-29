from pathlib import Path

from mailmap.config import Settings, microsoft_preflight_notes, validate_settings


def test_validate_settings_rejects_placeholder_microsoft_client_id() -> None:
    settings = Settings(
        imap_host="imap-mail.outlook.com",
        imap_port=993,
        email="user@hotmail.com",
        password="",
        auth_mode="microsoft-oauth",
        microsoft_client_id="SEU_CLIENT_ID",
        microsoft_tenant="consumers",
        smtp_host="",
        smtp_port=0,
        output_dir=Path("/tmp/mailmap-test"),
        default_folders=[],
        since=None,
        quick=False,
    )
    issues = validate_settings(settings)
    assert any("MAILMAP_MICROSOFT_CLIENT_ID" in issue for issue in issues)


def test_microsoft_preflight_notes_warn_for_outlook() -> None:
    settings = Settings(
        imap_host="imap-mail.outlook.com",
        imap_port=993,
        email="user@hotmail.com",
        password="",
        auth_mode="basic",
        microsoft_client_id="",
        microsoft_tenant="consumers",
        smtp_host="",
        smtp_port=0,
        output_dir=Path("/tmp/mailmap-test"),
        default_folders=[],
        since=None,
        quick=False,
    )
    notes = microsoft_preflight_notes(settings)
    assert any("experimental" in note.lower() for note in notes)
    assert any("microsoft-oauth" in note for note in notes)
