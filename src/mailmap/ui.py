from __future__ import annotations

from collections import Counter

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mailmap.config import Settings
from mailmap.models import RunStats, ServiceRecord

console = Console()


def print_header(settings: Settings) -> None:
    panel = Panel.fit(
        "\n".join(
            [
                "[bold]mailmap[/bold]",
                f"Target: {settings.email}",
                f"IMAP host: {settings.imap_host}:{settings.imap_port}",
                f"Auth: {settings.auth_mode}",
                f"Mode: {'quick scan' if settings.quick else 'full scan'}",
                f"Output: {settings.output_dir}",
            ]
        ),
        title="Mailbox Intelligence",
    )
    console.print(panel)


def print_config_error(issues: list[str]) -> None:
    message = "\n".join(issues + ["Fix your `.env` values and run `mailmap` again."])
    console.print(Panel.fit(message, title="Configuration Error", border_style="red"))


def print_preflight_notes(notes: list[str]) -> None:
    if not notes:
        return
    console.print(Panel.fit("\n".join(notes), title="Provider Notes", border_style="yellow"))


def print_summary(stats: RunStats, records: list[ServiceRecord], settings: Settings) -> None:
    counts = Counter(record.status for record in records)
    panel = Panel.fit(
        "\n".join(
            [
                f"Total emails scanned: {stats.total_uids_seen}",
                f"Total processed this run: {stats.processed_this_run}",
                f"Total reused from cache: {stats.reused_from_cache}",
                f"Total detected services: {len(records)}",
                f"Confirmed services: {counts.get('account-confirmed', 0)}",
                f"Likely services: {counts.get('likely-account', 0)}",
                f"Weak-signal services: {counts.get('weak-signal', 0)}",
                f"Newsletter-only services: {counts.get('newsletter-only', 0)}",
                f"Ambiguous services: {counts.get('ambiguous', 0)}",
            ]
        ),
        title="Run Summary",
    )
    console.print(panel)
    table = Table(title="Top Services")
    table.add_column("Service")
    table.add_column("Confidence", justify="right")
    table.add_column("Emails", justify="right")
    table.add_column("Status")
    for record in records[:10]:
        table.add_row(
            record.canonical_name,
            str(record.confidence),
            str(record.total_related_emails),
            record.status,
        )
    if records:
        console.print(table)
    console.print(
        f"Wrote [bold]{settings.output_dir / 'services.json'}[/bold], "
        f"[bold]{settings.output_dir / 'services.csv'}[/bold], "
        f"[bold]{settings.output_dir / 'report.md'}[/bold], "
        f"cache DB [bold]{settings.cache_db_path}[/bold]"
    )
