import io
import os

import pytest

from app.auth import create_admin_command, create_user_command
from app.db import get_db, init_db_command
from app.utils import save_upload


@pytest.fixture
def case_client(client, auth):
    auth.register()
    auth.login()
    client.post("/cases/new", data={"title": "Test case", "description": "x"})
    return client


def test_admin_page_redirects_visitors_who_are_not_logged_in(client):
    resp = client.get("/admin/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_missing_case_gives_404(case_client):
    assert case_client.get("/cases/999").status_code == 404


def test_invalid_status_value_is_rejected(case_client, app):
    resp = case_client.post("/cases/1/status", data={"status": "bogus"})
    assert resp.status_code == 400
    with app.app_context():
        row = get_db().execute("SELECT status FROM cases WHERE id = 1").fetchone()
    assert row["status"] == "open"


def test_failed_upload_leaves_no_row_and_no_file(case_client, app, monkeypatch):
    """The evidence row, the custody entry and the stored file succeed or fail together."""
    def boom(*args, **kwargs):
        raise RuntimeError("log write failed")

    monkeypatch.setattr("app.evidence.log_action", boom)
    with pytest.raises(RuntimeError):
        case_client.post(
            "/cases/1/evidence/upload",
            data={"file": (io.BytesIO(b"hello evidence"), "notes.txt")},
            content_type="multipart/form-data",
        )
    with app.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) AS n FROM evidence").fetchone()["n"] == 0
        assert db.execute("SELECT COUNT(*) AS n FROM custody_log").fetchone()["n"] == 0
    assert os.listdir(app.config["UPLOAD_FOLDER"]) == []


class ExplodingStream:
    def __init__(self):
        self.calls = 0

    def read(self, size):
        self.calls += 1
        if self.calls == 1:
            return b"partial data"
        raise OSError("disk error")


class FakeUpload:
    def __init__(self):
        self.stream = ExplodingStream()


def test_failed_save_removes_the_partial_file(tmp_path):
    with pytest.raises(OSError):
        save_upload(FakeUpload(), str(tmp_path))
    assert list(tmp_path.iterdir()) == []


def test_create_user_command_makes_an_investigator(app):
    runner = app.test_cli_runner()
    with app.app_context():
        result = runner.invoke(
            create_user_command, ["bob_1"],
            input="correct-horse-1\ncorrect-horse-1\n",
        )
        assert result.exit_code == 0, result.output
        assert "Investigator 'bob_1' created." in result.output
        row = get_db().execute(
            "SELECT role FROM users WHERE username = 'bob_1'"
        ).fetchone()
        assert row["role"] == "investigator"


def test_create_admin_command_makes_an_administrator(app):
    runner = app.test_cli_runner()
    with app.app_context():
        result = runner.invoke(
            create_admin_command, ["root_1"],
            input="correct-horse-1\ncorrect-horse-1\n",
        )
        assert result.exit_code == 0, result.output
        row = get_db().execute(
            "SELECT role FROM users WHERE username = 'root_1'"
        ).fetchone()
        assert row["role"] == "admin"


def test_create_user_command_rejects_a_short_password(app):
    runner = app.test_cli_runner()
    with app.app_context():
        result = runner.invoke(create_user_command, ["bob_1"], input="short\nshort\n")
        assert result.exit_code != 0
        assert "password shorter than" in result.output


def test_init_db_command_runs(app):
    runner = app.test_cli_runner()
    with app.app_context():
        result = runner.invoke(init_db_command)
        assert result.exit_code == 0, result.output
        assert "Initialised the database." in result.output

def test_filename_that_sanitises_to_nothing_is_rejected(case_client, app):
        resp = case_client.post(
          "/cases/1/evidence/upload",
          data={"file": (io.BytesIO(b"hello"), "...")},
          content_type="multipart/form-data",
      )
        assert b"Invalid file name." in resp.data
        with app.app_context():
          count = get_db().execute("SELECT COUNT(*) AS n FROM evidence").fetchone()["n"]
        assert count == 0

def test_session_for_a_deleted_user_is_treated_as_logged_out(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 999
    resp = client.get("/cases/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_closed_case_cannot_be_edited(case_client, app):
    case_client.post("/cases/1/status", data={"status": "closed"})
    assert case_client.get("/cases/1/edit").status_code == 302
    resp = case_client.post(
        "/cases/1/edit", data={"title": "Changed title", "description": "new"}
    )
    assert resp.status_code == 302
    with app.app_context():
        row = get_db().execute("SELECT title FROM cases WHERE id = 1").fetchone()
    assert row["title"] == "Test case"