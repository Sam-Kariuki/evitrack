# Development Log

## Day 1: Setup and planning

**Goal:** Prepare repository, environment and project plan.

**Done:**
- Created repo, virtual environment and folder structure
- Added .gitignore and .env.example (no secrets committed)
- Wrote proposal into docs/proposal.md
- Created 12 GitHub issues and a project board

**Decisions:**
- Flask app-factory pattern
- SQLite database
- Feature branch workflow

**Problems / lessons:**
- None

**Next:**
Day 2, application foundation.
**Security notes:**
- Passwords are stored using Werkzeug's secure password hashing.
- Role-based access control restricts administrative functions.
- Unauthorized access attempts return HTTP 403 responses.
- All timestamps are stored in UTC using SQLite CURRENT_TIMESTAMP and will be labelled as UTC in the interface and reports.

**Evidence collected:**
- Admin login screenshot
- Investigator login screenshot
- Admin users screenshot
- Forbidden access (403) screenshot
- Password hash verification screenshot

## Day 4: Case management
**Goal:** Create, view, edit and close cases with access control.
**Done:**
- Case routes: list, new, detail, edit, open/close
- Ownership check on every case route; admins can see all cases
- Closed cases are read-only (enforced server-side); only admins can reopen
- Input validation (title 3-120, description max 2000)
- 14 new tests (access control, validation, XSS escaping, SQL injection payload)
**Decisions:** return 404 (not 403) for other users' cases to prevent
case ID enumeration; all timestamps stored and shown in UTC.
**Limitations:** case-level actions are not yet in the custody log, which
is evidence-level; a separate audit log could be added as a stretch.
**Problems / lessons:** (note anything)
**Next:** Day 5, evidence upload and SHA-256 hashing.

## Day 5: Evidence upload and SHA-256 hashing
**Goal:** Accept evidence files and record an integrity hash.
**Done:**
- Streaming upload (64 KB chunks) hashed with SHA-256 in a single pass
- Files stored with random names, no extension, in instance/uploads
- Extension allowlist, size limit, 413 error page, empty-file check
- Evidence table on the case page; upload blocked on closed cases
- 16 new tests, including the published SHA-256 vector for "abc"
- Manual check: app hash matches PowerShell Get-FileHash
**Decisions:** hash computed server-side from the stored bytes; DB row written
only after the file is safely on disk; no edit or delete routes for evidence.
**Limitations:** allowlist checks extensions not content; file size not stored;
no download route; uploads before Step 6 have no custody entries.
**Problems / lessons:** (note anything)
**Next:** Day 6, custody logging.