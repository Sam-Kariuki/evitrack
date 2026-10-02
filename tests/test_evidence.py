import hashlib
import io
import os

import pytest

from app.db import get_db
from app.utils import sha256_of_file

ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def upload(client, case_id=1, name="notes.txt", data=b"hello evidence"):
    return client.post(
        f"/cases/{case_id}/evidence/upload",
        data={"file": (io.BytesIO(data), name)},
        content_type="multipart/form-data",
    )


def evidence_rows(app):
    with app.app_context():
        return get_db().execute("SELECT * FROM evidence").fetchall()


def stored_files(app):
    return os.listdir(app.config["UPLOAD_FOLDER"])


@pytest.fixture
def case_client(client, auth):
    auth.register()
    auth.login()
    client.post("/cases/new", data={"title": "Test case", "description": "x"})
    return client


def test_upload_requires_login(client):
    resp = upload(client)
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_upload_stores_correct_hash(case_client, app):
    data = b"hello evidence"
    assert upload(case_client, data=data).status_code == 302
    row = evidence_rows(app)[0]
    expected = hashlib.sha256(data).hexdigest()
    assert row["sha256"] == expected
    assert row["original_name"] == "notes.txt"
    assert row["case_id"] == 1
    assert row["uploaded_by"] == 1
    path = os.path.join(app.config["UPLOAD_FOLDER"], row["stored_name"])
    assert os.path.exists(path)
    assert sha256_of_file(path) == expected


def test_known_sha256_vector(case_client, app):
    upload(case_client, data=b"abc")
    assert evidence_rows(app)[0]["sha256"] == ABC_SHA256


def test_stored_name_is_random_and_has_no_extension(case_client, app):
    upload(case_client)
    row = evidence_rows(app)[0]
    assert row["stored_name"] != row["original_name"]
    assert "." not in row["stored_name"]
    assert len(row["stored_name"]) == 32


def test_filename_is_sanitised(case_client, app):
    upload(case_client, name="../../evil.txt")
    assert evidence_rows(app)[0]["original_name"] == "evil.txt"
    assert len(stored_files(app)) == 1


@pytest.mark.parametrize("name", [
    "run.exe", "page.php", "script.sh", "report.txt.exe", "noextension",
])
def test_disallowed_extension_rejected(case_client, app, name):
    resp = upload(case_client, name=name)
    assert b"not allowed" in resp.data
    assert evidence_rows(app) == []
    assert stored_files(app) == []


def test_empty_file_rejected(case_client, app):
    resp = upload(case_client, data=b"")
    assert b"empty" in resp.data
    assert evidence_rows(app) == []
    assert stored_files(app) == []


def test_no_file_selected(case_client, app):
    resp = case_client.post(
        "/cases/1/evidence/upload",
        data={"note": "x"},
        content_type="multipart/form-data",
    )
    assert b"choose a file" in resp.data
    assert evidence_rows(app) == []


def test_closed_case_blocks_upload(case_client, app):
    case_client.post("/cases/1/status", data={"status": "closed"})
    resp = upload(case_client)
    assert resp.status_code == 302
    assert evidence_rows(app) == []
    assert stored_files(app) == []


def test_other_investigator_gets_404(client, auth, app):
    auth.register("alice")
    auth.login("alice")
    client.post("/cases/new", data={"title": "Alice case", "description": ""})
    auth.logout()
    auth.register("bob")
    auth.login("bob")
    assert upload(client).status_code == 404
    assert evidence_rows(app) == []
    assert stored_files(app) == []


def test_oversize_upload_rejected(case_client, app):
    app.config["MAX_CONTENT_LENGTH"] = 1024
    resp = upload(case_client, data=b"x" * 4096)
    assert resp.status_code == 413
    assert evidence_rows(app) == []


def test_evidence_listed_on_case_page(case_client):
    upload(case_client, data=b"abc")
    page = case_client.get("/cases/1")
    assert b"notes.txt" in page.data
    assert ABC_SHA256.encode() in page.data

def test_413_page_keeps_logged_in_nav(case_client, app):
    app.config["WTF_CSRF_ENABLED"] = True
    app.config["MAX_CONTENT_LENGTH"] = 1024
    resp = upload(case_client, data=b"x" * 4096)
    assert resp.status_code == 413
    assert b"Log out" in resp.data 