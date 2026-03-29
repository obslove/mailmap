from pathlib import Path

from mailmap.config import Settings
from mailmap.oauth import build_xoauth2_string, is_microsoft_host


def test_is_microsoft_host_matches_outlook_and_o365() -> None:
    assert is_microsoft_host("imap-mail.outlook.com") is True
    assert is_microsoft_host("outlook.office365.com") is True
    assert is_microsoft_host("imap.gmail.com") is False


def test_build_xoauth2_string_format() -> None:
    raw = build_xoauth2_string("user@example.com", "token123")
    assert raw == b"user=user@example.com\x01auth=Bearer token123\x01\x01"


def test_settings_exposes_microsoft_token_cache_path() -> None:
    settings = Settings(
        imap_host="imap-mail.outlook.com",
        imap_port=993,
        email="user@example.com",
        password="",
        auth_mode="microsoft-oauth",
        microsoft_client_id="client-id",
        microsoft_tenant="consumers",
        smtp_host="",
        smtp_port=0,
        output_dir=Path("/tmp/mailmap-test"),
        default_folders=[],
        since=None,
        quick=False,
    )
    assert settings.microsoft_token_cache_path.name == "microsoft_token_cache.json"
