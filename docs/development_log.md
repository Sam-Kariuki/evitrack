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

## Step 8: Case report export (issue #8)

**Built**
- `GET /cases/<id>/report` (login required, same ownership check as the case page; other investigators get a 404).
- The report shows the case details and generation time, every evidence item with its recorded SHA-256 and a live integrity result (PASS or FAIL with the reason), the full custody log for the case, the chain status from `verify_chain()`, and the latest log entry number and hash.
- Print stylesheet (navigation hidden, landscape) so the browser's "Save as PDF" produces the report with no PDF library.
- 9 new tests (80 in total).

**Design decisions**
- Every file is rehashed when the report is generated, so the report states the files' current integrity rather than repeating the stored hash.
- Each integrity check made for a report is logged as `HASH_VERIFIED` with a "Case report:" prefix (entries 28 to 31 in the exported report), so producing a report leaves a trace in the custody chain.
- The latest entry hash is printed on the report. Deleting the newest log entries cannot be detected from inside the database, but it can be detected by comparing against a printed copy.
- A case-level "report generated" entry is not possible, because `custody_log.evidence_id` is required. The per-file entries record the event instead.
- The report route lives in `app/evidence.py` so it reuses `check_integrity()` without a circular import with `cases.py`.

**Problems / lessons**
- The first exported PDF was missing the Entry hash column. Unbreakable 64-character hashes inside the Notes cells forced the table wider than the page, and the last column was cut off. Fixed with `overflow-wrap: anywhere` and landscape printing. The tests could not catch this because it only appears in print output, so it was found by reading the exported PDF.
- `demo-notes.txt` was uploaded before custody logging existed, so its history has no UPLOADED entry. This is demo data; a fresh deployment starts with an empty database.

**Evidence**
`Step8_CaseReport.pdf` is the exported report for case 1. It shows PASS results for untouched files, a FAIL with the recorded and computed hashes for the deliberately tampered file, the full custody log, "Chain intact" and the latest entry hash. It replaces separate screenshots for this step.
## Step 9: Security hardening (issue #9)

**Built**
- Database-backed login lockout (`login_attempts` table, `app/lockout.py`): 5 failures per username in 10 minutes blocks further attempts with HTTP 429, including correct passwords; unknown usernames are throttled identically; success clears the count; records older than 24 hours are purged.
- Dummy password hash for unknown usernames so failed logins take similar time.
- Startup check: the app refuses to run with the default or an empty `SECRET_KEY` outside debug and testing mode.
- Session lifetime (8 hours), `Secure` cookie flag and HSTS controlled by `SESSION_COOKIE_SECURE`.
- Security headers on every response (CSP, nosniff, frame denial, referrer policy, permissions policy) and `Cache-Control: no-store` for logged-in pages and evidence downloads.
- Custom 500 page with no technical details.
- Case report generation changed from GET to POST.
- Tests: lockout, secret key, session cookie flags, headers, 500 handling, and a CSRF coverage test that checks every POST route rejects a request without a token.

**Design decisions**
- Lockout is stored in the database rather than in memory, so it survives restarts and needs no extra dependency.
- The lockout counts attempts per username, not per IP, so it works behind a proxy and cannot be dodged by rotating addresses. The cost is that someone can lock out a known username (threat 31).
- `Referrer-Policy: same-origin` rather than `no-referrer`, because Flask-WTF checks the Referer header on HTTPS form posts.
- The CSRF coverage test loops over the app's URL map, so any POST route added later is checked without anyone remembering to write a test. This closes the gap that let the verify form ship without a token.

**Problems / lessons**
- The startup key check also affects `flask init-db` and `flask create-admin`, so a real `SECRET_KEY` has to be in `.env`.
- Report generation was a GET that wrote to the custody log (threat 26), so it became a POST. A refresh now asks to resubmit and writes new log entries.
- DevTools showed a Content-Security-Policy with extra Kaspersky hosts on HTML pages. The antivirus on the development machine rewrites the header in the browser; the static file response and the app's own output (`Step9_HeadersRaw.png`) show the real policy. Lesson: verify security headers with a non-browser client as well as DevTools.

**Screenshots**
`Step9_Lockout.png`, `Step9_Headers.png`

## Step 10: UI polish (issue #[number])

**Built**
- New stylesheet with a consistent colour scheme (CSS variables), a sticky navigation bar that wraps on narrow screens, a content panel, and styled buttons, forms, tables and hash text.
- Status banners: the evidence page and the case report show "Chain intact" in a green banner and "CHAIN BROKEN" in a red one, instead of plain text.
- Flash messages are styled by outcome (success, error, information); errors use `role="alert"` so screen readers announce them.
- Failed integrity checks are highlighted: red rows in the custody tables for `HASH_VERIFIED` entries that failed, and red rows for failing files in the report.
- Case report summary line ("3 of 4 files passed the integrity check") above the evidence table.
- Download and Verify integrity on the evidence page are now buttons in a wrapping action row, so they no longer run off the edge on narrow windows.
- Accessibility basics: skip-to-content link, visible keyboard focus outline, labelled navigation, and a layout that works on phone-width screens.
- Print rules kept: the navigation bar is hidden and the report prints in landscape.
- 5 new tests in `tests/test_ui.py` (109 in total).

**Design decisions**
- No inline scripts or styles, so the strict Content-Security-Policy from Step 9 is unchanged and the pages still load with no CSP errors.
- Flash message styling is chosen in `base.html` from key words in the message, so no routes had to change. This is a shortcut. A cleaner version would pass a category to `flash()` in each route, and it is noted as possible future work.
- Failure is shown with words as well as colour (FAIL, CHAIN BROKEN), so the interface still works for colour-blind users and on black-and-white printouts.
- Every existing class name (`card`, `stack`, `badge`, `actions`, `upload-note`) was kept, so templates that were not redesigned still render correctly.
- Text that the tests and the report depend on ("Chain intact", "PASS", "FAIL", "hash mismatch") was left unchanged.

**Screenshots**
No new screenshots were taken for this step. The documentation step (#13) will retake the final screenshots of the finished interface.