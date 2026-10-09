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

## Step 10: UI polish (PR #23)

**Built**
- Restyled the whole interface with a new stylesheet and updated templates for every page: base layout and navigation, start page, login, register, case list, case form, case detail, evidence upload, evidence detail, case report and admin users.
- The case page now shows the custody chain status. `cases.detail` calls `verify_chain()` and passes the result to the template, so a broken chain is visible from the case as well as from an evidence page.
- Screenshots of the finished pages and an exported case report PDF.

**Design decisions**
- No inline scripts or styles and no external fonts, icons or CDN files, so the Content-Security-Policy from Step 9 is unchanged. A search of the templates and stylesheet for `<script`, `<style`, `style=`, `onclick=`, `|safe`, `@import`, `url(` and `http(s)://` returned nothing.
- The wording the tests depend on was kept, and all 104 tests still pass after the redesign.
- `verify_chain()` reads the whole custody log, and it now runs on the case page, the evidence page and the report. This is fine at the current size; with a very large log it would need caching, or checking only on the evidence page and the report.

**Problems / lessons**
- A second UI branch with overlapping changes conflicted with this one in four files. It was closed unmerged instead of resolving about 750 lines of CSS by hand. Lesson: check `git branch -a` and the open pull requests before starting work on files that another branch may already be changing.

## Step 11: Deployment (issue #12)

**Built**
- Deployed to a free PythonAnywhere account at https://samkariuki.pythonanywhere.com, served over HTTPS.
- `ALLOW_REGISTRATION` setting: when it is `0` the register page returns 404 and the Register links are hidden. Accounts on the live site are created with new `create-user` and `create-admin` commands run on the server.
- `create_account()` helper shared by both commands; 5 new tests (109 in total).
- Production `.env` on the server with its own `SECRET_KEY`, `SESSION_COOKIE_SECURE=1` and `ALLOW_REGISTRATION=0`, mode 600 and git-ignored.
- WSGI file that imports `create_app`; no static-file mapping, so the CSS goes through Flask and gets the security headers.

**Verified on the live site**
- Response headers checked with `curl.exe -sI`: CSP, nosniff, frame denial, referrer policy, permissions policy and HSTS are present; the session cookie has `Secure`, `HttpOnly` and `SameSite=Lax`; the `Server` header shows the host's name, not the framework version.
- Registration is closed ([404 check result]); login lockout works; a case, an upload and a report were produced on the live site, and the same file gives the same SHA-256 as on the development machine.

**Design decisions**
- PythonAnywhere was chosen because the app keeps its SQLite database and evidence files on disk and the free plan provides a persistent disk with HTTPS and no card. A host with a temporary disk would lose the database and evidence on every redeploy.
- Registration is closed on the public site so strangers cannot create accounts and upload files.
- The production secret key is generated on the server and is different from the development key.

**Problems / lessons**
- `base.html` was corrupted while hiding the Register links (probably by a regex find-and-replace or a format-on-save tool): 64 tests failed with a template syntax error. Recovered with `git checkout main -- app/templates`, redid the edit by hand, and turned off format-on-save for HTML. Lesson: read `git diff` on templates before running the tests.

**Limits of the free plan**
One web worker, a 100 CPU-second daily allowance, a one-month expiry that must be extended by hand, no SSH and no backups of the database or evidence files. The site holds demo data only.

**Screenshots**
`Step11_CurlHeaders.png`, `Step11_LiveHome.png`, `Step11_LiveLockout.png`, `Step11_LiveCaseReport.pdf`