from __future__ import annotations

import imaplib
import socket
import ssl
from contextlib import AbstractContextManager
from datetime import datetime

from mailmap.config import Settings
from mailmap.oauth import MailmapOAuthError, MicrosoftOAuthClient, build_xoauth2_string, is_microsoft_host


class MailmapIMAPError(RuntimeError):
    """Raised when IMAP interactions fail."""


class IMAPSession(AbstractContextManager):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client: imaplib.IMAP4_SSL | None = None

    def __enter__(self) -> "IMAPSession":
        context = ssl.create_default_context()
        socket.setdefaulttimeout(self.settings.connection_timeout)
        try:
            self.client = imaplib.IMAP4_SSL(
                self.settings.imap_host,
                self.settings.imap_port,
                ssl_context=context,
            )
            self._authenticate()
        except imaplib.IMAP4.error as exc:
            raise self._map_auth_error(exc) from exc
        except MailmapOAuthError as exc:
            raise MailmapIMAPError(str(exc)) from exc
        except (socket.timeout, OSError) as exc:
            raise MailmapIMAPError(f"Unable to connect to IMAP server: {exc}") from exc
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.client is not None:
            try:
                self.client.logout()
            except Exception:
                pass

    def _authenticate(self) -> None:
        assert self.client is not None
        if self.settings.auth_mode == "microsoft-oauth":
            self._login_with_microsoft_oauth()
            return
        if self.settings.auth_mode == "basic":
            self.client.login(self.settings.email, self.settings.password)
            return
        try:
            if self.settings.password:
                self.client.login(self.settings.email, self.settings.password)
                return
        except imaplib.IMAP4.error as exc:
            if self._looks_like_basic_auth_blocked(exc) and self._can_use_microsoft_oauth():
                self._login_with_microsoft_oauth()
                return
            raise
        if self._can_use_microsoft_oauth():
            self._login_with_microsoft_oauth()
            return
        raise MailmapIMAPError("Authentication failed. Set MAILMAP_PASSWORD or configure Microsoft OAuth.")

    def _login_with_microsoft_oauth(self) -> None:
        assert self.client is not None
        if not self._can_use_microsoft_oauth():
            raise MailmapOAuthError(
                "Microsoft OAuth requires `MAILMAP_MICROSOFT_CLIENT_ID` and an Outlook or Office365 IMAP host."
            )
        access_token = MicrosoftOAuthClient(self.settings).get_access_token()
        xoauth2 = build_xoauth2_string(self.settings.email, access_token)
        self.client.authenticate("XOAUTH2", lambda _: xoauth2)

    def _can_use_microsoft_oauth(self) -> bool:
        return bool(self.settings.microsoft_client_id and is_microsoft_host(self.settings.imap_host))

    @staticmethod
    def _looks_like_basic_auth_blocked(exc: imaplib.IMAP4.error) -> bool:
        message = str(exc).lower()
        return "basicauthblocked" in message or "logondenied-basicauthblocked" in message

    def _map_auth_error(self, exc: imaplib.IMAP4.error) -> MailmapIMAPError:
        if self._looks_like_basic_auth_blocked(exc) and is_microsoft_host(self.settings.imap_host):
            return MailmapIMAPError(
                "Microsoft blocked basic IMAP authentication for this account. "
                "Set `MAILMAP_AUTH_MODE=microsoft-oauth` and configure `MAILMAP_MICROSOFT_CLIENT_ID`."
            )
        return MailmapIMAPError("Authentication failed. Check MAILMAP_EMAIL and MAILMAP_PASSWORD.")

    def list_folders(self) -> list[str]:
        assert self.client is not None
        typ, data = self.client.list()
        if typ != "OK":
            raise MailmapIMAPError("Unable to list mailbox folders.")
        folders: list[str] = []
        for item in data or []:
            if not item:
                continue
            decoded = item.decode(errors="replace")
            folder = decoded.split(' "/" ')[-1].strip('"')
            folders.append(folder)
        return folders

    def select_folder(self, mailbox: str) -> int:
        assert self.client is not None
        typ, data = self.client.select(f'"{mailbox}"', readonly=True)
        if typ != "OK":
            raise MailmapIMAPError(f"Unable to select folder: {mailbox}")
        return int(data[0])

    def select_folder_writeable(self, mailbox: str) -> int:
        assert self.client is not None
        typ, data = self.client.select(f'"{mailbox}"', readonly=False)
        if typ != "OK":
            raise MailmapIMAPError(f"Unable to open folder for changes: {mailbox}")
        return int(data[0])

    def search_uids(self, mailbox: str, since: str | None) -> list[int]:
        assert self.client is not None
        self.select_folder(mailbox)
        criteria = ["ALL"]
        if since:
            parsed = datetime.fromisoformat(since).strftime("%d-%b-%Y")
            criteria = ["SINCE", parsed]
        typ, data = self.client.uid("SEARCH", None, *criteria)
        if typ != "OK":
            raise MailmapIMAPError(f"Unable to search folder: {mailbox}")
        raw = (data[0] or b"").decode()
        return [int(part) for part in raw.split() if part.isdigit()]

    def fetch_messages(self, mailbox: str, uids: list[int]) -> dict[int, bytes]:
        assert self.client is not None
        self.select_folder(mailbox)
        joined = ",".join(str(uid) for uid in uids)
        typ, data = self.client.uid("FETCH", joined, "(UID RFC822)")
        if typ != "OK":
            raise MailmapIMAPError(f"Unable to fetch messages from folder: {mailbox}")
        messages: dict[int, bytes] = {}
        for item in data or []:
            if not isinstance(item, tuple):
                continue
            header, payload = item
            header_text = header.decode(errors="replace")
            current_uid: int | None = None
            parts = header_text.replace("(", " ").replace(")", " ").split()
            for index, token in enumerate(parts):
                if token.upper() == "UID" and index + 1 < len(parts) and parts[index + 1].isdigit():
                    current_uid = int(parts[index + 1])
                    break
            if current_uid is not None and isinstance(payload, bytes):
                messages[current_uid] = payload
        return messages

    def move_uids(self, mailbox: str, destination: str, uids: list[int]) -> int:
        assert self.client is not None
        self.select_folder_writeable(mailbox)
        joined = ",".join(str(uid) for uid in uids)
        copy_typ, _ = self.client.uid("COPY", joined, f'"{destination}"')
        if copy_typ != "OK":
            raise MailmapIMAPError(f"Unable to copy messages from {mailbox} to {destination}")
        store_typ, _ = self.client.uid("STORE", joined, "+FLAGS.SILENT", r"(\Deleted)")
        if store_typ != "OK":
            raise MailmapIMAPError(f"Unable to mark messages for deletion in {mailbox}")
        expunge_typ, _ = self.client.expunge()
        if expunge_typ != "OK":
            raise MailmapIMAPError(f"Unable to expunge folder after move: {mailbox}")
        return len(uids)


def choose_folders(all_folders: list[str], preferred: list[str], *, quick: bool) -> list[str]:
    if preferred:
        return preferred
    lowered = {folder.lower(): folder for folder in all_folders}
    choices: list[str] = []
    include_markers = ["inbox", "all mail", "archive", "sent"]
    exclude_markers = ["spam", "junk", "trash", "bin", "deleted", "draft"]
    for folder in all_folders:
        low = folder.lower()
        if any(marker in low for marker in exclude_markers):
            continue
        if any(marker in low for marker in include_markers):
            choices.append(folder)
    if not choices and "inbox" in lowered:
        choices.append(lowered["inbox"])
    if quick:
        return choices[:2] if choices else all_folders[:1]
    return list(dict.fromkeys(choices or all_folders[:4]))
