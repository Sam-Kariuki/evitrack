import hashlib
import json
from datetime import datetime, timezone

GENESIS_HASH = "0" * 64


def compute_entry_hash(prev_hash, evidence_id, user_id, action, notes, timestamp):
    """SHA-256 over every field of an entry, in an unambiguous JSON form."""
    payload = json.dumps(
        [prev_hash, evidence_id, user_id, action, notes, timestamp],
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def log_action(db, evidence_id, user_id, action, notes=None):
    """Append one entry to the custody log. The caller must commit.

    If the caller has not already written something in this transaction,
    take the write lock first so two requests cannot both link to the same
    previous entry.
    """
    if not db.in_transaction:
        db.execute("BEGIN IMMEDIATE")

    last = db.execute(
        "SELECT entry_hash FROM custody_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    prev_hash = last["entry_hash"] if last else GENESIS_HASH
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    entry_hash = compute_entry_hash(
        prev_hash, evidence_id, user_id, action, notes, timestamp
    )
    db.execute(
        "INSERT INTO custody_log "
        "(evidence_id, user_id, action, notes, timestamp, prev_hash, entry_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (evidence_id, user_id, action, notes, timestamp, prev_hash, entry_hash),
    )
    return entry_hash