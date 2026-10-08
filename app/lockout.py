from datetime import datetime, timedelta, timezone

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 10
KEEP_HOURS = 24
USERNAME_KEY_LENGTH = 64
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _now():
    return datetime.now(timezone.utc)


def _key(username):
    # Cap the length so junk usernames cannot bloat the table.
    return username[:USERNAME_KEY_LENGTH]


def is_locked_out(db, username, now=None):
    """True if the username has had too many failures in the last 10 minutes.

    Unknown usernames are tracked the same way as real ones, so the lockout
    does not reveal which accounts exist.
    """
    now = now or _now()
    window_start = (now - timedelta(minutes=LOCKOUT_MINUTES)).strftime(TIME_FORMAT)
    row = db.execute(
        "SELECT COUNT(*) AS n FROM login_attempts "
        "WHERE username = ? AND attempted_at > ?",
        (_key(username), window_start),
    ).fetchone()
    return row["n"] >= MAX_FAILED_ATTEMPTS


def record_failed_login(db, username, ip=None, now=None):
    now = now or _now()
    db.execute(
        "INSERT INTO login_attempts (username, ip, attempted_at) VALUES (?, ?, ?)",
        (_key(username), ip, now.strftime(TIME_FORMAT)),
    )
    cutoff = (now - timedelta(hours=KEEP_HOURS)).strftime(TIME_FORMAT)
    db.execute("DELETE FROM login_attempts WHERE attempted_at < ?", (cutoff,))
    db.commit()


def clear_failed_logins(db, username):
    db.execute("DELETE FROM login_attempts WHERE username = ?", (_key(username),))
    db.commit()