# Threat Model

| # | Threat | Asset | Mitigation | Status |
|---|--------|--------|------------|--------|
| 1 | SQL injection | Database | Parameterised queries | Planned |
| 2 | Weak password storage | User accounts | Salted hashing | Planned |
| 3 | Malicious file upload | Server | Validation, safe filenames, storage outside web root | Planned |
| 4 | Evidence tampering | Evidence files | SHA-256 verification | Planned |
| 5 | Log tampering | Custody log | Hash-chained entries | Planned |
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