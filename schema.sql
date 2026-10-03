CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'investigator'
        CHECK (role IN ('investigator', 'admin')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'closed')),
    created_by INTEGER NOT NULL REFERENCES users (id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id INTEGER NOT NULL REFERENCES cases (id),
    original_name TEXT NOT NULL,
    stored_name TEXT UNIQUE NOT NULL,
    sha256 TEXT NOT NULL,
    uploaded_by INTEGER NOT NULL REFERENCES users (id),
    uploaded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS custody_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    evidence_id INTEGER NOT NULL REFERENCES evidence (id),
    user_id INTEGER NOT NULL REFERENCES users (id),
    action TEXT NOT NULL,
    notes TEXT,
    timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    prev_hash TEXT,
    entry_hash TEXT
);
CREATE TRIGGER IF NOT EXISTS custody_log_no_update
BEFORE UPDATE ON custody_log
BEGIN
    SELECT RAISE(ABORT, 'custody_log is append-only');
END;

CREATE TRIGGER IF NOT EXISTS custody_log_no_delete
BEFORE DELETE ON custody_log
BEGIN
    SELECT RAISE(ABORT, 'custody_log is append-only');
END;