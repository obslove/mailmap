from __future__ import annotations

import csv
import json
import smtplib
from collections import defaultdict
from dataclasses import asdict, dataclass
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from mailmap.config import Settings
from mailmap.imap_client import IMAPSession, MailmapIMAPError
from mailmap.models import MailboxMessage, ServiceEvidence, ServiceRecord


@dataclass(slots=True)
class HygieneItem:
    service: str
    status: str
    confidence: int
    recommended_action: str
    reason: str
    representative_senders: list[str]


@dataclass(slots=True)
class UnsubscribeAction:
    service: str
    method: str
    target: str
    executed: bool
    note: str


@dataclass(slots=True)
class CleanResult:
    service: str
    mailbox: str
    moved_count: int
    archive_folder: str | None
    note: str


def default_target_services(records: list[ServiceRecord]) -> list[str]:
    return [
        record.canonical_name
        for record in records
        if record.status in {"newsletter-only", "weak-signal"}
    ]


def parse_service_selection(value: str | None, records: list[ServiceRecord]) -> list[str]:
    if not value:
        return default_target_services(records)
    requested = {part.strip().lower() for part in value.split(",") if part.strip()}
    return [record.canonical_name for record in records if record.canonical_name.lower() in requested]


def recommend_action(record: ServiceRecord, evidence: ServiceEvidence) -> tuple[str, str]:
    newsletter_count = len(evidence.newsletter_messages)
    strong_count = len(evidence.security_messages | evidence.billing_messages | evidence.account_messages)
    if record.status == "newsletter-only":
        return "unsubscribe-and-archive", "Newsletter-dominant stream with low account confidence"
    if record.status == "weak-signal":
        return "archive-or-delete", "Low-confidence presence; good candidate for cleanup"
    if "marketing-heavy" in evidence.internal_flags:
        return "keep-but-mute", "Likely linked account, but inbox traffic is marketing-heavy"
    if newsletter_count > strong_count * 3:
        return "mute-or-filter", "Notifications are dominated by newsletter-style traffic"
    return "keep", "Service has meaningful account evidence"


def build_hygiene_plan(records: list[ServiceRecord], evidence_map: dict[str, ServiceEvidence]) -> list[HygieneItem]:
    plan: list[HygieneItem] = []
    for record in records:
        evidence = evidence_map.get(record.canonical_name)
        if evidence is None:
            continue
        action, reason = recommend_action(record, evidence)
        plan.append(
            HygieneItem(
                service=record.canonical_name,
                status=record.status,
                confidence=record.confidence,
                recommended_action=action,
                reason=reason,
                representative_senders=record.representative_senders,
            )
        )
    return plan


def export_hygiene_plan(items: list[HygieneItem], output_dir: Path) -> tuple[Path, Path]:
    json_path = output_dir / "hygiene.json"
    md_path = output_dir / "hygiene.md"
    json_path.write_text(
        json.dumps([asdict(item) for item in items], indent=2),
        encoding="utf-8",
    )
    lines = ["# Hygiene Plan", ""]
    for item in items:
        lines.extend(
            [
                f"## {item.service}",
                f"- Status: `{item.status}`",
                f"- Confidence: `{item.confidence}`",
                f"- Recommended action: `{item.recommended_action}`",
                f"- Reason: {item.reason}",
                f"- Representative senders: `{', '.join(item.representative_senders) or 'n/a'}`",
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def _list_unsubscribe_targets(message: MailboxMessage) -> list[tuple[str, str]]:
    raw = message.list_unsubscribe or ""
    targets: list[tuple[str, str]] = []
    for part in [segment.strip(" <>") for segment in raw.split(",") if segment.strip()]:
        if part.startswith("mailto:"):
            targets.append(("mailto", part))
        elif part.startswith("http://") or part.startswith("https://"):
            targets.append(("http", part))
    return targets


def _send_mailto_unsubscribe(settings: Settings, mailto_url: str) -> str:
    if not settings.smtp_host or not settings.smtp_port:
        return "SMTP not configured; generated plan only"
    parsed = urlparse(mailto_url)
    params = parse_qs(parsed.query)
    msg = EmailMessage()
    msg["From"] = settings.email
    msg["To"] = parsed.path
    msg["Subject"] = unquote(params.get("subject", ["unsubscribe"])[0])
    msg.set_content(unquote(params.get("body", ["unsubscribe"])[0]))
    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.login(settings.email, settings.password)
        smtp.send_message(msg)
    return "Sent unsubscribe email"


def run_unsubscribe(
    settings: Settings,
    records: list[ServiceRecord],
    evidence_map: dict[str, ServiceEvidence],
    messages_by_ref: dict[tuple[str, int], MailboxMessage],
    target_services: list[str],
) -> list[UnsubscribeAction]:
    actions: list[UnsubscribeAction] = []
    for service in target_services:
        evidence = evidence_map.get(service)
        if evidence is None:
            continue
        seen_targets: set[tuple[str, str]] = set()
        for ref in evidence.message_uids:
            message = messages_by_ref.get(ref)
            if message is None:
                continue
            for method, target in _list_unsubscribe_targets(message):
                key = (method, target)
                if key in seen_targets:
                    continue
                seen_targets.add(key)
                executed = False
                note = "Manual unsubscribe link"
                if method == "mailto":
                    note = _send_mailto_unsubscribe(settings, target)
                    executed = note == "Sent unsubscribe email"
                actions.append(
                    UnsubscribeAction(
                        service=service,
                        method=method,
                        target=target,
                        executed=executed,
                        note=note,
                    )
                )
    return actions


def export_unsubscribe_actions(actions: list[UnsubscribeAction], output_dir: Path) -> tuple[Path, Path]:
    json_path = output_dir / "unsubscribe_actions.json"
    md_path = output_dir / "unsubscribe_actions.md"
    json_path.write_text(json.dumps([asdict(action) for action in actions], indent=2), encoding="utf-8")
    lines = ["# Unsubscribe Actions", ""]
    for action in actions:
        lines.extend(
            [
                f"## {action.service}",
                f"- Method: `{action.method}`",
                f"- Target: `{action.target}`",
                f"- Executed: `{action.executed}`",
                f"- Note: {action.note}",
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def _choose_archive_folder(folders: list[str]) -> str | None:
    for marker in ("all mail", "archive"):
        for folder in folders:
            if marker in folder.lower():
                return folder
    return None


def run_clean(
    settings: Settings,
    evidence_map: dict[str, ServiceEvidence],
    target_services: list[str],
) -> list[CleanResult]:
    grouped: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for service in target_services:
        evidence = evidence_map.get(service)
        if evidence is None:
            continue
        for mailbox, uid in evidence.message_uids:
            grouped[service][mailbox].append(uid)

    results: list[CleanResult] = []
    with IMAPSession(settings) as session:
        folders = session.list_folders()
        archive_folder = _choose_archive_folder(folders)
        for service, mailbox_map in grouped.items():
            if not archive_folder:
                results.append(
                    CleanResult(service=service, mailbox="*", moved_count=0, archive_folder=None, note="No archive folder found")
                )
                continue
            for mailbox, uids in mailbox_map.items():
                if mailbox == archive_folder or not uids:
                    continue
                try:
                    moved = session.move_uids(mailbox, archive_folder, sorted(set(uids)))
                    results.append(
                        CleanResult(
                            service=service,
                            mailbox=mailbox,
                            moved_count=moved,
                            archive_folder=archive_folder,
                            note="Archived matching messages",
                        )
                    )
                except MailmapIMAPError as exc:
                    results.append(
                        CleanResult(
                            service=service,
                            mailbox=mailbox,
                            moved_count=0,
                            archive_folder=archive_folder,
                            note=str(exc),
                        )
                    )
    return results


def export_clean_results(results: list[CleanResult], output_dir: Path) -> tuple[Path, Path]:
    json_path = output_dir / "clean_results.json"
    csv_path = output_dir / "clean_results.csv"
    json_path.write_text(json.dumps([asdict(result) for result in results], indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["service", "mailbox", "moved_count", "archive_folder", "note"])
        for result in results:
            writer.writerow([result.service, result.mailbox, result.moved_count, result.archive_folder, result.note])
    return json_path, csv_path
