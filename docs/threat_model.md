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