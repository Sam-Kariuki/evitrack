# Threat model

| # | Threat | Asset | Mitigation | Status |
|---|--------|-------|------------|--------|
| 1 | SQL injection | Database | Parameterised queries on every database call | Done |
| 2 | Weak password storage | User accounts | Salted password hashing; plain-text passwords are never stored | Done |
| 3 | Unauthorised privilege escalation | Administrative functions | Role-based access control (investigator and admin roles) enforced on admin routes | Done |
| 4 | Viewing or editing another investigator's case by changing the URL | Cases | Ownership check on every case route; returns 404 instead of 403 so the case's existence is not revealed | Done |
| 5 | Reaching another case's evidence by changing the URL | Evidence | Case ownership check plus a check that the evidence belongs to the case in the URL; returns 404 | Done |
| 6 | Altering a closed case | Case integrity | Server-side status check on edit and on evidence upload; only admins can reopen a case | Done |
| 7 | Stored XSS through a case title, description or file name | Users' browsers | Jinja autoescaping with no use of `\|safe`; covered by tests | Done |
| 8 | Path traversal through a file name | Server filesystem | `secure_filename`, random stored names, and paths built on the server only | Done |
| 9 | Executable or script upload | Server, other users | Extension allowlist; files stored under random names without an extension; never served inline or executed | Done (no content inspection) |
| 10 | Oversized upload or disk exhaustion | Availability | `MAX_CONTENT_LENGTH` with a custom 413 page; files are streamed to disk in chunks | Done (no per-user quota) |
| 11 | Evidence file altered after upload | Evidence files | SHA-256 recorded at upload; the file is rehashed on every download and manual verify; a mismatch is logged as `HASH_VERIFIED` (FAIL) | Done (no scheduled background check) |
| 12 | Evidence file deleted or missing from storage | Evidence files | The integrity check reports "stored file is missing", logs a FAIL and blocks the download | Done (no backup or recovery) |
| 13 | Serving a modified file as evidence | Evidence integrity | The integrity check runs before every download; the file is sent only if the hash matches; a blocked attempt is logged | Done |
| 14 | Unlogged access to evidence | Evidence, custody log | `UPLOADED`, `VIEWED`, `DOWNLOADED` and `HASH_VERIFIED` entries are written automatically, in the same transaction as the action where one applies | Done |
| 15 | Editing or deleting custody entries through SQL | Custody log | Append-only triggers abort any UPDATE or DELETE; the application only ever inserts | Done |
| 16 | Edited or removed custody entries going unnoticed | Custody log | Each entry's hash covers the previous entry's hash; `verify_chain()` rechecks every link and hash, and the evidence page shows "Chain intact" or "CHAIN BROKEN"; tested by tampering with rows | Done (cannot detect deletion of the newest entries) |
| 17 | Direct edit of the database file or dropping the triggers | Custody log | The hash chain detects edited rows and rows removed from the middle of the log | Partial (latest entry hash is not yet stored outside the database) |
| 18 | Concurrent writes forking the chain | Custody log | `BEGIN IMMEDIATE` takes the write lock before the last hash is read; the evidence row and its log entry commit together | Done |
| 19 | Cross-site request forgery on state-changing actions | Evidence, cases, accounts | CSRF token on POST forms; a request without one is rejected with a 400; a regression test checks the verify form includes its token | Done (all forms to be re-reviewed in #9) |
| 20 | Brute-force login attempts | User accounts | Rate limiting or lockout on repeated failed logins | Planned (#9) |
| 21 | Session hijacking or cookie theft | User sessions | Secure session cookie settings (`HttpOnly`, `SameSite`, `Secure` when deployed) and security headers | Planned (#9) |