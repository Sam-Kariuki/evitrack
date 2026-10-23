# EviTrack: Project proposal

Capstone project, BSc Cybersecurity and Digital Forensics (Year 2)
Author: Sam Kariuki

## 1. Summary

EviTrack is a web application that shows when digital evidence has been changed. It hashes every file with SHA-256 and records each action on it in an append-only, hash-chained custody log. The project is built in small tracked steps, guided by a threat model, tested automatically and deployed online.

## 2. Problem

- Evidence files can be altered or swapped without a visible trace.
- Handling notes kept in spreadsheets or ordinary logs can be edited later.
- Who opened, copied or checked an item, and when, is often unrecorded.

Without proof of integrity and proof of handling, evidence can be challenged.

## 3. Aim and objectives

**Aim:** design, build, test and deploy a web-based evidence tracker whose records can show when evidence has been tampered with.

| # | Objective |
|---|---|
| O1 | Store evidence with a SHA-256 hash taken at upload |
| O2 | Record every action in an append-only, hash-chained log |
| O3 | Verify integrity on demand and before every download |
| O4 | Produce a printable case report with PASS or FAIL results |
| O5 | Defend against common web attacks, guided by a threat model |
| O6 | Test automatically, deploy online and document it all |

## 4. Scope

**In scope:** accounts with investigator and admin roles; case management; evidence upload with validation and hashing; the custody log; integrity checks that block altered downloads; the case report; hardening, tests, CI and deployment.

**Out of scope:** forensic analysis of file contents; disk imaging; password reset by email or single sign-on; admin screens to disable accounts; scheduled background integrity checks; certification for real casework.

## 5. Users

- **Investigator:** creates and owns cases, uploads, verifies and downloads evidence, generates reports; sees only their own cases.
- **Administrator:** created from the command line; can see every case.
- **Report reader:** receives the printed report and compares its latest log hash with the system; has no account.

## 6. Requirements

**Functional**
1. Accounts with hashed passwords and two roles
2. Create, edit, close and reopen cases
3. Upload evidence; reject bad types, empty and oversized files
4. Hash every file with SHA-256 at upload
5. Log upload, view, download and verification automatically
6. Verify integrity on demand; block altered downloads
7. Detect tampering with the custody log itself
8. Generate a printable case report

**Non-functional:** security (common web threats handled and documented); integrity (log entries cannot be edited in the app); testability (automated tests, 90% or more coverage target); usability (clear PASS or FAIL and chain status); deployability (free host, HTTPS, secrets kept out of code).

## 7. Design

A Flask application with three blueprints (auth, cases, evidence) and modules for the custody log, login lockout and security headers. Data is held in SQLite (`users`, `cases`, `evidence`, `custody_log`, `login_attempts`); evidence files live in a folder that is never served directly.

Each custody entry's hash is SHA-256 over `[prev_hash, evidence_id, user_id, action, notes, timestamp]` as compact JSON. The first entry uses a previous hash of 64 zeros. Triggers abort any UPDATE or DELETE on the log, and `verify_chain()` rechecks every link.

## 8. Security approach

Threats are recorded in a living [threat model](threat_model.md) with asset, mitigation and status, and updated after every step. Headline controls: parameterised queries, ownership checks returning 404, Jinja autoescaping with a strict CSP, upload validation, CSRF tokens, login lockout, and the hash-chained log.

## 9. Method

Each step follows the same loop: GitHub issue, branch, build and test, manual check, pull request, merge and documentation. Nothing is committed straight to `main`. A development log, screenshots and threat-model updates are written after every step.

## 10. Technology

Python 3.13, Flask 3.1, Flask-WTF, Jinja2, SQLite, pytest and pytest-cov, GitHub Actions, PythonAnywhere.

## 11. Plan (14 days)

| Days | Work |
|---|---|
| 1 | Setup and planning |
| 2 to 3 | Foundation and authentication |
| 4 | Case management |
| 5 | Evidence upload and hashing |
| 6 | Chain-of-custody log |
| 7 | Integrity verification |
| 8 | Case report |
| 9 | Security hardening |
| 10 to 12 | UI, deployment and CI |
| 13 to 14 | Documentation and release |

## 12. Testing and quality

Unit and route tests, security tests (lockout, headers, secret key, CSRF on every POST route), tamper tests (alter a stored file or edit a log row and expect FAIL), manual testing with screenshots, and continuous integration with a secrets check. Target: 90% or more statement coverage.

## 13. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Fourteen days is tight for a solo build | High | High | Small vertical steps; optional work deferred |
| Claiming the system is tamper-proof | Medium | High | State limits openly; print the latest log hash |
| Secrets leaked into the repository | Medium | High | Git-ignored `.env`, placeholder example, CI check |
| Free hosting limits | High | Medium | Demo data only; document the limits |
| A new feature breaks an old one | Medium | Medium | Automated tests and CI; one branch per step |
| Windows development, Linux host | Low | Medium | CI runs on Linux; deploy early |

## 14. Deliverables and success criteria

**Deliverables:** source code and tests on GitHub; live deployment over HTTPS; threat model; development log with screenshots; case report PDF from the live system; final documentation; tagged `v1.0.0` release.

**Success criteria:** a modified file shows FAIL and its download is blocked; an edited log row shows CHAIN BROKEN; every POST route rejects a request without a CSRF token; five failed logins lock the account for ten minutes; coverage of 90% or more with CI passing; HTTPS with security headers present.

## 15. Ethics and limits

Demo data only; no real case material. Passwords are salted and hashed and no other personal data is kept. A hash shows a file is unchanged since upload, not that it was genuine when collected. EviTrack is a learning project, not certified forensic software.
