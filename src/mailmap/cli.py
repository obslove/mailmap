from __future__ import annotations

from pathlib import Path

import typer

from mailmap.actions import (
    build_hygiene_plan,
    export_clean_results,
    export_hygiene_plan,
    export_unsubscribe_actions,
    parse_service_selection,
    run_clean,
    run_unsubscribe,
)
from mailmap.app import run_scan
from mailmap.config import load_settings, microsoft_preflight_notes, validate_settings
from mailmap.imap_client import MailmapIMAPError
from mailmap.ui import console, print_config_error, print_header, print_preflight_notes, print_summary

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.command()
def entrypoint(
    since: str | None = typer.Option(None, "--since", help="Only scan messages since YYYY-MM-DD."),
    quick: bool = typer.Option(False, "--quick", help="Run a faster, lower-depth scan."),
    output: Path | None = typer.Option(None, "--output", help="Write results into this directory."),
    clean: bool = typer.Option(False, "-c", "--clean", help="Archive low-priority inbox traffic."),
    unsub: bool = typer.Option(False, "-u", "--unsub", help="Generate or execute unsubscribe actions when possible."),
    hygiene: bool = typer.Option(False, "-y", "--hygiene", help="Generate inbox hygiene recommendations."),
    services: str | None = typer.Option(None, "-s", "--services", help="Comma-separated service names to target."),
) -> None:
    settings = load_settings(since=since, quick=quick, output_dir=str(output) if output else None)
    issues = validate_settings(settings)
    if issues:
        print_config_error(issues)
        raise typer.Exit(code=2)
    print_header(settings)
    print_preflight_notes(microsoft_preflight_notes(settings))
    try:
        stats, records, messages_by_ref, parsed_messages, evidence_map = run_scan(settings)
    except MailmapIMAPError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    hygiene_items = build_hygiene_plan(records, evidence_map)
    recommendation_map = {item.service: item.recommended_action for item in hygiene_items}
    for record in records:
        record.recommended_action = recommendation_map.get(record.canonical_name, "review")
    if hygiene:
        hygiene_json, hygiene_md = export_hygiene_plan(hygiene_items, settings.output_dir)
        console.print(f"Wrote [bold]{hygiene_json}[/bold] and [bold]{hygiene_md}[/bold]")
    targets = parse_service_selection(services, records) if (clean or unsub) else []
    if unsub:
        actions = run_unsubscribe(settings, records, evidence_map, messages_by_ref, targets)
        unsub_json, unsub_md = export_unsubscribe_actions(actions, settings.output_dir)
        console.print(f"Wrote [bold]{unsub_json}[/bold] and [bold]{unsub_md}[/bold]")
    if clean:
        clean_results = run_clean(settings, evidence_map, targets)
        clean_json, clean_csv = export_clean_results(clean_results, settings.output_dir)
        console.print(f"Wrote [bold]{clean_json}[/bold] and [bold]{clean_csv}[/bold]")
    print_summary(stats, records, settings)


def main() -> None:
    app()


if __name__ == "__main__":
    app()
