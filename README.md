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