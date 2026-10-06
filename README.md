# EviTrack

A secure digital evidence and chain-of-custody manager built with
Python, Flask and SQLite. Year 2 capstone project, BSc Cybersecurity
and Digital Forensics.

## Status
In development. See docs/development_log.md for progress.

## Features (planned)
- Role-based login (investigator, admin)
- Case management
- Evidence upload with SHA-256 integrity verification
- Tamper-evident chain-of-custody log
- Case report export

## Tech stack
Python 3, Flask, SQLite, pytest, GitHub Actions

## Ethical note
Only synthetic test data is used. No real casework or personal data.

## Setup
(to be completed in Step 2)
## Features Implemented

### Authentication and Roles
- User registration
- User login and logout
- Password hashing using Werkzeug
- Investigator role
- Administrator role
- Role-based access control
- Protected administrative pages

### Security Features
- Session-based authentication
- Passwords stored as hashes
- Authorization checks
- HTTP 403 protection against unauthorized access

### Time Handling
All timestamps are stored in UTC to ensure forensic consistency and auditability.
- Evidence upload with server-side SHA-256 hashing. Files are stored under random names outside the web root, with an extension allowlist and a size limit (default 10 MB, set via `MAX_UPLOAD_MB`).
- Chain of custody: every upload and every view of evidence is recorded automatically with user, UTC time and a hash linking each entry to the previous one. The log is append-only (enforced by database triggers).

## Day 6: Custody logging
**Goal:** Record every access to evidence in a tamper-evident chain of custody.
**Done:**
- app/custody.py: log_action and compute_entry_hash (SHA-256 over canonical JSON of all fields plus the previous hash)
- UPLOADED entry written in the same transaction as the evidence row
- Evidence page: shows hash at upload and full custody history; records a VIEWED entry on every open
- Append-only triggers on custody_log (UPDATE and DELETE rejected)
- 10 new tests (chaining, reproducible hashes, view logging, access control, append-only)
**Decisions:** one global chain written from the first entry (no backfill needed);
BEGIN IMMEDIATE so writers take turns and the chain cannot fork;
evidence must belong to the case named in the URL; timestamps in UTC.
**Limitations:** evidence uploaded before this step has no UPLOADED entry;
chain verification is added in Step 9; anyone with direct file access could drop
the triggers, which is why the hash chain exists; reloading the page adds entries.
**Problems / lessons:** (note anything)
**Next:** Day 7, integrity verification and first deployment.