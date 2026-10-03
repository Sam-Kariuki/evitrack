# Threat Model

| # | Threat | Asset | Mitigation | Status |
|---|--------|--------|------------|--------|
| 1 | SQL injection | Database | Parameterised queries | Planned |
| 2 | Weak password storage | User accounts | Salted hashing | Planned |
| 3 | Malicious file upload | Server | Validation, safe filenames, storage outside web root | Planned |
| 4 | Evidence tampering | Evidence files | SHA-256 verification | Planned |
| 5 | Partial: append-only triggers and hash chain written, chain verification in Step 9 | Custody log | Hash-chained entries | Planned |
| # | Threat | Asset | Mitigation | Status |
|---|--------|--------|------------|--------|
| 1 | SQL injection | Database | Parameterised queries | Implemented |
| 2 | Weak password storage | User accounts | Salted password hashing | Implemented |
| 3 | Malicious file upload | Server | Validation and secure storage | Planned |
| 4 | Evidence tampering | Evidence files | SHA-256 verification | Planned |
| 5 | Log tampering | Custody log | Hash chaining | Planned |
| 6 | Unauthorized privilege escalation | Administrative functions | Role-based access control | Implemented |
| 12 | Insecure direct object reference (viewing or editing another user's case) | Cases | Ownership check on every route; 404 instead of 403 | Done |
| 13 | Stored XSS via case title or description | Users' browsers | Jinja autoescaping, no `|safe`; tested | Done |
| 14 | Altering a closed case | Case integrity | Server-side status check on edit; only admins can reopen | Done |
| 15 | Path traversal via file name | Server filesystem | secure_filename, random stored names, paths built server-side | Done |
| 16 | Oversized upload / disk exhaustion | Availability | MAX_CONTENT_LENGTH with 413 handler | Done (no per-user quota) |
| 17 | Executable or script upload | Server, other users | Extension allowlist; stored without extension; never served or executed | Done (no content inspection) |
| 18 | Editing or deleting custody entries through SQL | Custody log | Append-only triggers; hash chain makes direct edits detectable | Partial (verification in Step 9) |
| 19 | Concurrent writes forking the chain | Custody log | BEGIN IMMEDIATE; evidence row and log entry commit together | Done |
| 20 | Reaching another case's evidence by changing the URL | Evidence | Case ownership check plus evidence-belongs-to-case check; 404 | Done |
| 21 | Unlogged access to evidence | Evidence | VIEWED entry written before the page is shown | Done (no download route yet) |