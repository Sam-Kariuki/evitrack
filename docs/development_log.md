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