from __future__ import annotations

import csv
import json
from pathlib import Path

from mailmap.models import ServiceRecord


def export_json(records: list[ServiceRecord], output_dir: Path) -> Path:
    path = output_dir / "services.json"
    payload = [
        {
            "canonical_name": record.canonical_name,
            "associated_domains": record.associated_domains,
            "confidence": record.confidence,
            "status": record.status,
            "categories": record.categories,
            "total_related_emails": record.total_related_emails,
            "first_seen": record.first_seen,
            "last_seen": record.last_seen,
            "evidence_summary": record.evidence_summary,
            "representative_senders": record.representative_senders,
            "representative_subject_lines": record.representative_subject_lines,
            "reasoning": record.reasoning,
            "ambiguity_notes": record.ambiguity_notes,
            "recommended_action": record.recommended_action,
        }
        for record in records
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def export_csv(records: list[ServiceRecord], output_dir: Path) -> Path:
    path = output_dir / "services.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "service",
                "confidence",
                "status",
                "categories",
                "total_related_emails",
                "first_seen",
                "last_seen",
                "associated_domains",
                "evidence_summary",
                "recommended_action",
            ]
        )
        for record in records:
            writer.writerow(
                [
                    record.canonical_name,
                    record.confidence,
                    record.status,
                    ", ".join(record.categories),
                    record.total_related_emails,
                    record.first_seen,
                    record.last_seen,
                    ", ".join(record.associated_domains),
                    record.evidence_summary,
                    record.recommended_action,
                ]
            )
    return path


def export_markdown(records: list[ServiceRecord], output_dir: Path, *, email: str, quick: bool) -> Path:
    path = output_dir / "report.md"
    lines = [
        "# Mailmap Report",
        "",
        f"- Target email: `{email}`",
        f"- Scan mode: `{'quick' if quick else 'full'}`",
        f"- Detected services: `{len(records)}`",
        "",
        "## Services",
        "",
    ]
    for record in records:
        lines.extend(
            [
                f"### {record.canonical_name}",
                "",
                f"- Confidence: `{record.confidence}`",
                f"- Status: `{record.status}`",
                f"- Categories: `{', '.join(record.categories)}`",
                f"- Related emails: `{record.total_related_emails}`",
                f"- First seen: `{record.first_seen or 'unknown'}`",
                f"- Last seen: `{record.last_seen or 'unknown'}`",
                f"- Associated domains: `{', '.join(record.associated_domains) or 'unknown'}`",
                f"- Evidence summary: {record.evidence_summary}",
                f"- Recommended action: `{record.recommended_action}`",
                f"- Representative senders: `{', '.join(record.representative_senders) or 'n/a'}`",
                f"- Representative subjects: `{'; '.join(record.representative_subject_lines) or 'n/a'}`",
            ]
        )
        if record.ambiguity_notes:
            lines.append(f"- Ambiguity notes: `{'; '.join(record.ambiguity_notes)}`")
        if record.reasoning:
            lines.append(f"- Reasoning: `{'; '.join(record.reasoning)}`")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
