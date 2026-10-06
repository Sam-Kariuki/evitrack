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

## Step 7: Integrity verification and chain verification (issues #7, #10)

**Built**
- Download route that rehashes the stored file before serving it and logs `DOWNLOADED`.
- "Verify integrity" action that rehashes the stored file, compares it with the SHA-256 recorded at upload, and logs `HASH_VERIFIED` with PASS or FAIL.
- `verify_chain()` walks the whole custody log, rechecks every link and every entry hash, and the evidence page shows "Chain intact" or "CHAIN BROKEN".
- 13 new tests (71 in total).

**Design decisions**
- A download is blocked if the stored file no longer matches its recorded hash. Serving a modified file as evidence would be worse than refusing. The blocked attempt is logged.
- A failed check does not alter the log. The log records the failure, so the chain stays intact while the file is flagged.
- Each action is followed by a `VIEWED` row because the redirect back to the evidence page counts as a view.

**Problems / lessons**
- The first test run had 5 failures because `stored_name` was missing from the SELECT in `get_evidence_or_404`.
- The chain status test failed because the new template content had been placed after `{% endblock %}`, where child templates ignore it.
- The verify form returned a 400 "CSRF token is missing" in the browser (`Step7_Verify400.png`). The unit tests didn't catch it because CSRF is disabled in the test config. It was found by manual testing, fixed by adding the token to the form, and a regression test now checks that the form includes it.
- A regression test was accidentally pasted into `app/custody.py` instead of the test file. It was spotted in `git diff` before committing and reverted.

**Screenshots**
`Step7_HashPass.png`, `Step7_Downloaded.png`, `Step7_ChainIntact.png`, `Step7_CheckFail.png`, `Step7_DownloadBlocked.png`, `Step7_FailedLog.png`, `Step7_Verify400.png`