from __future__ import annotations

import msal

from mailmap.config import Settings

OUTLOOK_SCOPE = "https://outlook.office.com/IMAP.AccessAsUser.All"


class MailmapOAuthError(RuntimeError):
    """Raised when OAuth configuration or token acquisition fails."""


def is_microsoft_host(host: str) -> bool:
    lowered = host.lower()
    return "outlook" in lowered or "office365" in lowered


def build_xoauth2_string(email: str, access_token: str) -> bytes:
    return f"user={email}\x01auth=Bearer {access_token}\x01\x01".encode()


class MicrosoftOAuthClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.cache = msal.SerializableTokenCache()
        if settings.microsoft_token_cache_path.exists():
            self.cache.deserialize(settings.microsoft_token_cache_path.read_text(encoding="utf-8"))
        authority = f"https://login.microsoftonline.com/{settings.microsoft_tenant}"
        self.app = msal.PublicClientApplication(
            client_id=settings.microsoft_client_id,
            authority=authority,
            token_cache=self.cache,
        )

    def get_access_token(self) -> str:
        scopes = [OUTLOOK_SCOPE]
        accounts = self.app.get_accounts(username=self.settings.email)
        if accounts:
            result = self.app.acquire_token_silent(scopes, account=accounts[0])
            if result and result.get("access_token"):
                self._persist_cache()
                return result["access_token"]

        flow = self.app.initiate_device_flow(scopes=scopes)
        if "user_code" not in flow:
            error = flow.get("error") if isinstance(flow, dict) else None
            description = flow.get("error_description") if isinstance(flow, dict) else None
            detail = description or error or "unknown error"
            raise MailmapOAuthError(f"Unable to start Microsoft device-code authentication flow: {detail}")

        print("")
        print("Microsoft OAuth required for this mailbox.")
        print(f"Open: {flow['verification_uri']}")
        print(f"Code: {flow['user_code']}")
        print("Complete sign-in in the browser, then return here.")
        print("")

        result = self.app.acquire_token_by_device_flow(flow)
        if not result or "access_token" not in result:
            detail = result.get("error_description") if isinstance(result, dict) else "unknown error"
            raise MailmapOAuthError(f"Microsoft OAuth failed: {detail}")
        self._persist_cache()
        return result["access_token"]

    def _persist_cache(self) -> None:
        if self.cache.has_state_changed:
            self.settings.microsoft_token_cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.settings.microsoft_token_cache_path.write_text(self.cache.serialize(), encoding="utf-8")
