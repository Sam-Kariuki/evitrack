import click
import pytest

from app import create_app
from app.auth import create_account
from app.db import get_db, init_db


def make_app(tmp_path, **overrides):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test",
        "WTF_CSRF_ENABLED": False,
        "DATABASE": str(tmp_path / "test.sqlite"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    }
    config.update(overrides)
    app = create_app(config)
    with app.app_context():
        init_db()
    return app


def test_registration_is_open_when_enabled(tmp_path):
    client = make_app(tmp_path, ALLOW_REGISTRATION=True).test_client()
    assert client.get("/auth/register").status_code == 200


def test_registration_can_be_switched_off(tmp_path):
    client = make_app(tmp_path, ALLOW_REGISTRATION=False).test_client()
    assert client.get("/auth/register").status_code == 404
    resp = client.post("/auth/register", data={
        "username": "mallory", "password": "correct-horse-1",
        "confirm": "correct-horse-1"})
    assert resp.status_code == 404


def test_register_links_are_hidden_when_registration_is_off(tmp_path):
    client = make_app(tmp_path, ALLOW_REGISTRATION=False).test_client()
    for url in ("/", "/auth/login"):
        assert b"/auth/register" not in client.get(url).data


def test_create_account_makes_an_investigator(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        assert create_account("  Bob_1 ", "correct-horse-1", "investigator") == "bob_1"
        row = get_db().execute(
            "SELECT role FROM users WHERE username = 'bob_1'"
        ).fetchone()
        assert row["role"] == "investigator"


def test_create_account_rejects_duplicates_and_weak_passwords(tmp_path):
    app = make_app(tmp_path)
    with app.app_context():
        create_account("bob_1", "correct-horse-1", "investigator")
        with pytest.raises(click.ClickException):
            create_account("bob_1", "correct-horse-1", "investigator")
        with pytest.raises(click.ClickException):
            create_account("carol", "short", "investigator")