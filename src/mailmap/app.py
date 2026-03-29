from __future__ import annotations

from datetime import UTC, datetime

from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from mailmap.aggregation import aggregate_messages
from mailmap.config import Settings
from mailmap.database import CacheDB
from mailmap.exporters import export_csv, export_json, export_markdown
from mailmap.imap_client import IMAPSession, MailmapIMAPError, choose_folders
from mailmap.message_parser import parse_message
from mailmap.models import MailboxMessage, RunStats


def batched(items: list[int], size: int) -> list[list[int]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def run_scan(settings: Settings) -> tuple[RunStats, list, dict[str, MailboxMessage], list[MailboxMessage], dict]:
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    cache = CacheDB(settings.cache_db_path)
    stats = RunStats()
    run_id = cache.begin_run(
        started_at=datetime.now(UTC).isoformat(),
        quick_mode=settings.quick,
        since_date=settings.since,
    )
    parsed_messages: list[MailboxMessage] = []
    try:
        with IMAPSession(settings) as session:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn(),
                transient=True,
            ) as progress:
                discovery = progress.add_task("Discovering folders", total=1)
                all_folders = session.list_folders()
                selected_folders = choose_folders(all_folders, settings.default_folders, quick=settings.quick)
                stats.folders_considered = len(all_folders)
                progress.update(discovery, completed=1)

                folder_task = progress.add_task("Scanning folders", total=len(selected_folders))
                for folder in selected_folders:
                    try:
                        uids = session.search_uids(folder, settings.since)
                    except MailmapIMAPError:
                        stats.fetch_failures += 1
                        progress.advance(folder_task)
                        continue
                    stats.folders_scanned += 1
                    stats.total_uids_seen += len(uids)
                    fetch_task = progress.add_task(f"Fetching {folder}", total=len(uids) or 1)
                    for batch in batched(uids, settings.batch_size):
                        to_fetch = [uid for uid in batch if not cache.has_processed(folder, uid)]
                        cached = len(batch) - len(to_fetch)
                        stats.reused_from_cache += cached
                        for uid in batch:
                            if uid not in to_fetch:
                                cached_message = cache.load_message(folder, uid)
                                if cached_message:
                                    if isinstance(cached_message.sent_at, str):
                                        cached_message.sent_at = datetime.fromisoformat(cached_message.sent_at)
                                    parsed_messages.append(cached_message)
                        if to_fetch:
                            try:
                                fetched = session.fetch_messages(folder, to_fetch)
                            except MailmapIMAPError:
                                stats.fetch_failures += len(to_fetch)
                                progress.advance(fetch_task, advance=len(batch))
                                continue
                            for uid in to_fetch:
                                raw = fetched.get(uid)
                                if raw is None:
                                    stats.fetch_failures += 1
                                    continue
                                try:
                                    parsed = parse_message(raw, uid=uid, mailbox=folder)
                                    cache.store_message(parsed)
                                    parsed_messages.append(parsed)
                                    stats.processed_this_run += 1
                                except Exception:
                                    stats.parse_failures += 1
                        progress.advance(fetch_task, advance=len(batch))
                    progress.advance(folder_task)
        records, evidence_map = aggregate_messages(parsed_messages, quick=settings.quick)
        stats.detected_services = len(records)
        export_json(records, settings.output_dir)
        export_csv(records, settings.output_dir)
        export_markdown(records, settings.output_dir, email=settings.email, quick=settings.quick)
        cache.finish_run(
            run_id,
            finished_at=datetime.now(UTC).isoformat(),
            total_seen=stats.total_uids_seen,
            processed_count=stats.processed_this_run,
            cached_count=stats.reused_from_cache,
            service_count=len(records),
        )
        messages_by_ref = {(message.mailbox, message.uid): message for message in parsed_messages}
        return stats, records, messages_by_ref, parsed_messages, evidence_map
    except Exception:
        cache.finish_run(
            run_id,
            finished_at=datetime.now(UTC).isoformat(),
            total_seen=stats.total_uids_seen,
            processed_count=stats.processed_this_run,
            cached_count=stats.reused_from_cache,
            service_count=0,
        )
        raise
