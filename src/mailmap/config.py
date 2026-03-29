from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

MICROSOFT_CLIENT_ID_PLACEHOLDERS = {
    "",
    "seu_client_id",
    "your-client-id",
    "your_client_id",
    "client_id",
}


@dataclass(slots=True)
class Settings:
    imap_host: str
    imap_port: int
    email: str
    password: str
    auth_mode: str
    microsoft_client_id: str
    microsoft_tenant: str
    smtp_host: str
    smtp_port: int
    output_dir: Path
    default_folders: list[str]
    since: str | None
    quick: bool
    batch_size: int = 100
    connection_timeout: int = 30
    cache_db_name: str = "mailmap_cache.sqlite3"
    verbose: bool = False

    @property
    def cache_db_path(self) -> Path:
        return self.output_dir / self.cache_db_name

    @property
    def microsoft_token_cache_path(self) -> Path:
        return self.output_dir / "microsoft_token_cache.json"


def _split_csv(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def load_settings(*, since: str | None, quick: bool, output_dir: str | None) -> Settings:
    load_dotenv(override=False)
    host = os.getenv("MAILMAP_IMAP_HOST", "").strip()
    port = int(os.getenv("MAILMAP_IMAP_PORT", "993"))
    email = os.getenv("MAILMAP_EMAIL", "").strip()
    password = os.getenv("MAILMAP_PASSWORD", "").strip()
    auth_mode = os.getenv("MAILMAP_AUTH_MODE", "auto").strip().lower() or "auto"
    microsoft_client_id = os.getenv("MAILMAP_MICROSOFT_CLIENT_ID", "").strip()
    microsoft_tenant = os.getenv("MAILMAP_MICROSOFT_TENANT", "consumers").strip() or "consumers"
    smtp_host = os.getenv("MAILMAP_SMTP_HOST", "").strip()
    smtp_port = int(os.getenv("MAILMAP_SMTP_PORT", "0") or "0")
    env_output = os.getenv("MAILMAP_OUTPUT_DIR", "results").strip() or "results"
    folders = _split_csv(os.getenv("MAILMAP_DEFAULT_FOLDERS"))

    resolved_output = Path(output_dir or env_output).expanduser().resolve()
    return Settings(
        imap_host=host,
        imap_port=port,
        email=email,
        password=password,
        auth_mode=auth_mode,
        microsoft_client_id=microsoft_client_id,
        microsoft_tenant=microsoft_tenant,
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        output_dir=resolved_output,
        default_folders=folders,
        since=since,
        quick=quick,
    )


def validate_settings(settings: Settings) -> list[str]:
    issues: list[str] = []
    if not settings.imap_host:
        issues.append("Missing `MAILMAP_IMAP_HOST`.")
    if not settings.email:
        issues.append("Missing `MAILMAP_EMAIL`.")
    if settings.auth_mode not in {"auto", "basic", "microsoft-oauth"}:
        issues.append("`MAILMAP_AUTH_MODE` must be `auto`, `basic`, or `microsoft-oauth`.")
    if settings.auth_mode == "basic" and not settings.password:
        issues.append("Missing `MAILMAP_PASSWORD`.")
    if settings.auth_mode == "microsoft-oauth" and settings.microsoft_client_id.lower() in MICROSOFT_CLIENT_ID_PLACEHOLDERS:
        issues.append(
            "Microsoft OAuth needs a real `MAILMAP_MICROSOFT_CLIENT_ID`. "
            "The current value is missing or still a placeholder."
        )
    if settings.auth_mode == "auto" and not settings.password and not settings.microsoft_client_id:
        issues.append("Set `MAILMAP_PASSWORD` or `MAILMAP_MICROSOFT_CLIENT_ID`.")
    if settings.imap_port <= 0:
        issues.append("`MAILMAP_IMAP_PORT` must be a positive integer.")
    return issues


def microsoft_preflight_notes(settings: Settings) -> list[str]:
    host = settings.imap_host.lower()
    if "outlook" not in host and "office365" not in host:
        return []

    notes = [
        "Microsoft personal mailboxes are experimental in `mailmap`.",
        "Many Outlook/Hotmail accounts block normal IMAP password login entirely.",
        "Working OAuth usually requires your own Azure or Entra app registration.",
    ]
    if settings.auth_mode != "microsoft-oauth":
        notes.append(
            "For Outlook/Hotmail, prefer `MAILMAP_AUTH_MODE=microsoft-oauth` instead of password-based login."
        )
    if settings.auth_mode == "microsoft-oauth" and settings.microsoft_client_id.lower() in MICROSOFT_CLIENT_ID_PLACEHOLDERS:
        notes.append("`MAILMAP_MICROSOFT_CLIENT_ID` is still a placeholder, so OAuth cannot start.")
    return notes
