from datetime import datetime, timedelta, timezone

from app.db import get_db
from app.lockout import MAX_FAILED_ATTEMPTS, is_locked_out


def fail_logins(auth, username, times):
    for _ in range(times):
        auth.login(username, "wrong-password-1")


def attempt_count(app, username):
    with app.app_context():
        return get_db().execute(
            "SELECT COUNT(*) AS n FROM login_attempts WHERE username = ?",
            (username,),
        ).fetchone()["n"]


def test_failures_below_the_limit_do_not_lock(client, auth):
    auth.register()
    fail_logins(auth, "alice", MAX_FAILED_ATTEMPTS - 1)
    assert auth.login().status_code == 302


def test_account_locks_after_repeated_failures(client, auth):
    auth.register()
    fail_logins(auth, "alice", MAX_FAILED_ATTEMPTS)
    resp = auth.login()  # correct password, but the account is locked
    assert resp.status_code == 429
    assert b"Too many failed login attempts" in resp.data
    assert client.get("/cases/").status_code == 302  # still logged out


def test_unknown_username_is_throttled_the_same_way(client, auth):
    fail_logins(auth, "ghost", MAX_FAILED_ATTEMPTS)
    assert auth.login("ghost", "another-password-1").status_code == 429


def test_lockout_is_per_username(client, auth):
    auth.register("alice")
    auth.register("bob")
    fail_logins(auth, "alice", MAX_FAILED_ATTEMPTS)
    assert auth.login("alice").status_code == 429
    assert auth.login("bob").status_code == 302


def test_attempts_during_lockout_are_not_recorded(client, auth, app):
    auth.register()
    fail_logins(auth, "alice", MAX_FAILED_ATTEMPTS)
    fail_logins(auth, "alice", 3)
    assert attempt_count(app, "alice") == MAX_FAILED_ATTEMPTS


def test_lock_expires(client, auth, app):
    auth.register()
    fail_logins(auth, "alice", MAX_FAILED_ATTEMPTS)
    with app.app_context():
        db = get_db()
        assert is_locked_out(db, "alice") is True
        later = datetime.now(timezone.utc) + timedelta(minutes=11)
        assert is_locked_out(db, "alice", now=later) is False


def test_successful_login_clears_earlier_failures(client, auth, app):
    auth.register()
    fail_logins(auth, "alice", MAX_FAILED_ATTEMPTS - 1)
    assert auth.login().status_code == 302
    assert attempt_count(app, "alice") == 0
    auth.logout()
    fail_logins(auth, "alice", MAX_FAILED_ATTEMPTS - 1)
    assert auth.login().status_code == 302


def test_old_attempts_are_purged(client, auth, app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO login_attempts (username, attempted_at) "
            "VALUES ('old', '2020-01-01 00:00:00')"
        )
        db.commit()
    auth.login("ghost", "wrong-password-1")
    assert attempt_count(app, "old") == 0