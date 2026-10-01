import pytest
from flask import g, session
from werkzeug.security import generate_password_hash

from app.db import get_db


def get_user(app, username):
    with app.app_context():
        return get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()


def test_register_creates_investigator(auth, app):
    assert auth.register().status_code == 302
    assert get_user(app, "alice")["role"] == "investigator"


def test_password_is_hashed(auth, app):
    auth.register(password="correct-horse-1")
    assert "correct-horse-1" not in get_user(app, "alice")["password_hash"]


def test_role_cannot_be_chosen_in_form(client, app):
    client.post("/auth/register", data={
        "username": "mallory", "password": "correct-horse-1",
        "confirm": "correct-horse-1", "role": "admin"})
    assert get_user(app, "mallory")["role"] == "investigator"


@pytest.mark.parametrize(("username", "password", "confirm", "message"), [
    ("ab", "correct-horse-1", "correct-horse-1", b"Username must be"),
    ("alice", "short", "short", b"at least 10"),
    ("alice", "correct-horse-1", "different-pass-1", b"do not match"),
])
def test_register_validation(client, username, password, confirm, message):
    resp = client.post("/auth/register", data={
        "username": username, "password": password, "confirm": confirm})
    assert message in resp.data


def test_duplicate_username_rejected(auth):
    auth.register()
    resp = auth.register()
    assert b"already taken" in resp.data


def test_login_and_logout(client, auth):
    auth.register()
    with client:
        auth.login()
        client.get("/")
        assert session["user_id"] == 1
        assert g.user["username"] == "alice"
        auth.logout()
        assert "user_id" not in session


@pytest.mark.parametrize(("username", "password"), [
    ("alice", "wrong-password-1"),
    ("nobody", "correct-horse-1"),
])
def test_login_error_is_generic(auth, username, password):
    auth.register()
    resp = auth.login(username, password)
    assert b"Invalid username or password." in resp.data


def test_admin_page_requires_login(client):
    resp = client.get("/admin/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_investigator_forbidden_on_admin_page(client, auth):
    auth.register()
    auth.login()
    assert client.get("/admin/").status_code == 403


def test_admin_can_view_admin_page(client, auth, app):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
            ("boss", generate_password_hash("correct-horse-1")),
        )
        db.commit()
    auth.login("boss")
    assert client.get("/admin/").status_code == 200


def test_csrf_is_enforced(app):
    app.config["WTF_CSRF_ENABLED"] = True
    resp = app.test_client().post(
        "/auth/login", data={"username": "a", "password": "b"})
    assert resp.status_code == 400