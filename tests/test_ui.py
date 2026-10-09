import io
import os

import pytest

from app.db import get_db


def upload(client, case_id=1, name="notes.txt", data=b"hello evidence"):
    return client.post(
        f"/cases/{case_id}/evidence/upload",
        data={"file": (io.BytesIO(data), name)},
        content_type="multipart/form-data",
    )


def stored_file(app, evidence_id=1):
    with app.app_context():
        name = get_db().execute(
            "SELECT stored_name FROM evidence WHERE id = ?", (evidence_id,)
        ).fetchone()["stored_name"]
        return os.path.join(app.config["UPLOAD_FOLDER"], name)


@pytest.fixture
def case_client(client, auth):
    auth.register()
    auth.login()
    client.post("/cases/new", data={"title": "Test case", "description": "x"})
    return client


def test_error_messages_are_styled_as_errors(client, auth):
    resp = auth.login("ghost", "wrong-password-1")
    assert b'class="flash error"' in resp.data


def test_success_messages_are_styled_as_success(client):
    resp = client.post(
        "/auth/register",
        data={"username": "alice", "password": "correct-horse-1",
              "confirm": "correct-horse-1"},
        follow_redirects=True,
    )
    assert b'class="flash success"' in resp.data


def test_evidence_page_shows_a_chain_status_banner(case_client):
    upload(case_client)
    resp = case_client.get("/cases/1/evidence/1")
    assert b'class="status ok"' in resp.data


def test_report_summary_when_every_file_passes(case_client):
    upload(case_client)
    resp = case_client.post("/cases/1/report")
    assert b"1 of 1 files passed the integrity check." in resp.data


def test_report_summary_and_row_style_when_a_file_fails(case_client, app):
    upload(case_client)
    with open(stored_file(app), "ab") as f:
        f.write(b" tampered")
    resp = case_client.post("/cases/1/report")
    assert b"0 of 1 files passed the integrity check." in resp.data
    assert b'class="row-fail"' in resp.data