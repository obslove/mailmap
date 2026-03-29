# mailmap

`mailmap` is a mailbox intelligence CLI that scans your email account over IMAP and produces a conservative inventory of services likely linked to that address.

Provider support is not equally simple:

- Gmail, Fastmail, Proton Bridge, and many classic IMAP providers are the easiest path.
- Outlook and Hotmail are experimental because Microsoft often blocks classic IMAP login and may require your own Azure or Entra app registration for OAuth.

The normal flow is intentionally simple:

1. Copy `.env.example` to `.env`
2. Fill in your IMAP host, email, and password
3. Run `mailmap`

The default run performs a resumable full scan, reuses cached messages from SQLite, scores services with explainable evidence, and writes:

- `services.json`
- `services.csv`
- `report.md`
- optional action plans when requested:
  - `hygiene.json` / `hygiene.md`
  - `unsubscribe_actions.json` / `unsubscribe_actions.md`
  - `clean_results.json` / `clean_results.csv`

## Install

```bash
cd /home/ven/Projects/mailmap
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For development and tests:

```bash
pip install -e .[dev]
```

## Configure

```bash
cp .env.example .env
```

Required variables:

- `MAILMAP_IMAP_HOST`
- `MAILMAP_EMAIL`
- `MAILMAP_PASSWORD` for normal IMAP login

Optional variables:

- `MAILMAP_IMAP_PORT` default `993`
- `MAILMAP_AUTH_MODE` one of `auto`, `basic`, `microsoft-oauth`
- `MAILMAP_MICROSOFT_CLIENT_ID` required for Microsoft OAuth
- `MAILMAP_MICROSOFT_TENANT` default `consumers`
- `MAILMAP_SMTP_HOST` optional, used for `mailto:` unsubscribe execution
- `MAILMAP_SMTP_PORT` optional, used for `mailto:` unsubscribe execution
- `MAILMAP_DEFAULT_FOLDERS` comma-separated override for folder autodiscovery
- `MAILMAP_OUTPUT_DIR` default `results`

App passwords work well for providers that block normal mailbox passwords over IMAP.

### Outlook and Hotmail

Some Microsoft accounts reject classic IMAP username/password login with `BasicAuthBlocked`.

This is not a dead-simple provider in practice. For many personal Microsoft accounts, working OAuth requires creating your own app registration in Azure or Microsoft Entra first.

`mailmap` supports Microsoft OAuth device-code login for those accounts. Set:

```env
MAILMAP_IMAP_HOST=imap-mail.outlook.com
MAILMAP_IMAP_PORT=993
MAILMAP_EMAIL=you@hotmail.com
MAILMAP_AUTH_MODE=microsoft-oauth
MAILMAP_MICROSOFT_CLIENT_ID=your-azure-app-client-id
MAILMAP_MICROSOFT_TENANT=consumers
MAILMAP_OUTPUT_DIR=results
```

Then run `mailmap`. On the first run, it will show a verification URL and code. After sign-in, the token is cached locally in the output directory and reused on later runs.

If you do not already have an Azure or Entra app registration, Outlook and Hotmail will usually not be plug-and-play with `mailmap`.

## Usage

Full default scan:

```bash
mailmap
```

Scan recent history only:

```bash
mailmap --since 2024-01-01
```

Run a shallower scan:

```bash
mailmap --quick
```

Write results somewhere else:

```bash
mailmap --output results/
```

Generate inbox hygiene recommendations:

```bash
mailmap -y
```

Generate unsubscribe actions for low-priority services:

```bash
mailmap -u
```

Archive low-priority traffic:

```bash
mailmap -c
```

Target specific services for cleanup or unsubscribe:

```bash
mailmap -c -u -s "Pinterest,Spotify,Twitch"
```

## What It Does

- loads configuration from CLI flags, environment variables, and `.env`
- connects over IMAP SSL
- auto-selects useful folders like Inbox, All Mail, Archive, and Sent
- skips obvious junk folders by default
- uses UID-based batched fetching
- caches parsed messages in SQLite for resume and incremental reruns
- extracts evidence from headers, text, HTML, URLs, and linked domains
- suppresses infrastructure and tracking domains where possible
- canonicalizes services conservatively
- scores findings into `account-confirmed`, `likely-account`, `weak-signal`, `newsletter-only`, or `ambiguous`
- can generate inbox hygiene plans, unsubscribe actions, and archive cleanups by service

## Outputs

`services.json`
- full machine-readable records

`services.csv`
- flat export for spreadsheets

`report.md`
- readable report for a human review

`mailmap_cache.sqlite3`
- local cache and run history

## Project Layout

```text
src/mailmap/
  cli.py
  app.py
  config.py
  imap_client.py
  message_parser.py
  content.py
  domains.py
  evidence.py
  scoring.py
  aggregation.py
  database.py
  exporters.py
  ui.py
tests/
examples/
```

## Reliability Notes

- malformed messages are skipped instead of crashing the run
- folder-level failures are counted and the scan continues where possible
- logs stay compact in normal mode and do not dump message bodies
- attribution stays conservative and falls back to `ambiguous` when evidence conflicts

## Example Outputs

See:

- `examples/services.json`
- `examples/services.csv`
- `examples/report.md`
