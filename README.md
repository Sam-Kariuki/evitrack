[![CI](https://github.com/Sam-Kariuki/evitrack/actions/workflows/ci.yml/badge.svg)](https://github.com/Sam-Kariuki/evitrack/actions/workflows/ci.yml)

# EviTrack

A tamper-evident digital evidence and chain-of-custody manager built with Python, Flask and SQLite. Year 2 capstone project, BSc Cybersecurity and Digital Forensics.

**Live demo:** https://samkariuki.pythonanywhere.com (demo data only; registration is closed)

## What it does

EviTrack stores evidence files with a SHA-256 hash taken at upload and records every action on them in an append-only, hash-chained custody log. An investigator can verify a file at any time, and the system refuses to serve a file whose hash no longer matches.

## Features

**Accounts and access**
- Login and logout with salted password hashes (Werkzeug)
- Investigator and administrator roles with server-side access checks
- Investigators see only their own cases; other cases return a 404 page

**Cases and evidence**
- Create, edit, close and reopen cases; closed cases block edits and uploads
- Evidence upload with an extension allowlist, safe file names, random stored names outside the web root and a size limit (`MAX_UPLOAD_MB`, default 10)
- Server-side SHA-256 computed while the file is streamed to disk

**Chain of custody**
- `UPLOADED`, `VIEWED`, `DOWNLOADED` and `HASH_VERIFIED` entries are written automatically with user, UTC time and notes
- Each entry's hash covers its fields and the previous entry's hash; the evidence page shows "Chain intact" or "CHAIN BROKEN"
- Database triggers reject any UPDATE or DELETE on the log

**Integrity and reporting**
- On-demand verification and a check before every download; a modified or missing file logs a FAIL and blocks the download
- Printable case report with PASS or FAIL per file, the chain status and the latest log hash for offline comparison

**Security hardening**
- CSRF token on every POST route (a test checks all of them)
- Login lockout: 5 failures in 10 minutes gives HTTP 429
- Content-Security-Policy, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, `Permissions-Policy`, `no-store` caching and HSTS
- Refuses to start with a default `SECRET_KEY`; custom 404, 413 and 500 pages

All timestamps are stored in UTC.

## Tech stack

Python 3.13, Flask 3.1, Flask-WTF, Jinja2, SQLite, pytest and pytest-cov, GitHub Actions, PythonAnywhere.

## Quick start

```bash
git clone https://github.com/Sam-Kariuki/evitrack.git
cd evitrack
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then set SECRET_KEY (see below)
```

Generate a secret key and paste it into `.env`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Create the first accounts, then run the app:

```bash
flask create-admin
flask create-user
flask run
```

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Signs sessions and CSRF tokens. Required outside debug and testing. | none |
| `MAX_UPLOAD_MB` | Largest accepted upload | `10` |
| `ALLOW_REGISTRATION` | Set to `0` to close public registration | open |
| `SESSION_COOKIE_SECURE` | Set to `1` when served over HTTPS; also enables HSTS | off |

Never commit `.env`. CI fails if a tracked `.env`, database or 64-character hex string is found.

## Tests

```bash
pytest --cov=app --cov-report=term-missing
```

119 tests passed at the last full run, with 99% statement coverage. CI runs the suite and a secrets check on every push and pull request.

## Documentation

- [Project proposal](docs/proposal.md)
- [Threat model](docs/threat_model.md) (36 threats)
- [Development log](docs/development_log.md)

## Known limits

- Deleting the newest custody entries cannot be detected inside the database. The latest entry hash is printed on each report so it can be compared with a kept copy.
- File types are checked by extension, not by content.
- Lockout is per username, so a known user can be locked out for 10 minutes.
- Sessions are stateless; logout cannot revoke a copied cookie before it expires.
- The free host has one worker and no backups.

See the threat model for the full list.

## Ethical note

Only synthetic test data is used. No real casework or personal data. EviTrack is a learning project and is not certified forensic software.
