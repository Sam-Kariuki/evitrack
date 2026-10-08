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


def log_rows(app):
    with app.app_context():
        return get_db().execute(
            "SELECT * FROM custody_log ORDER BY id"
        ).fetchall()


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


def test_report_requires_login(client):
    resp = client.post("/cases/1/report")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_report_rejects_get_requests(case_client, app):
    upload(case_client)
    assert case_client.get("/cases/1/report").status_code == 405
    assert [r["action"] for r in log_rows(app)] == ["UPLOADED"]


def test_other_investigator_cannot_see_report(client, auth, app):
    auth.register("alice")
    auth.login("alice")
    client.post("/cases/new", data={"title": "Alice case", "description": ""})
    upload(client)
    auth.logout()
    auth.register("bob")
    auth.login("bob")
    assert client.post("/cases/1/report").status_code == 404
    assert [r["action"] for r in log_rows(app)] == ["UPLOADED"]


def test_report_contents_for_clean_case(case_client, app):
    upload(case_client)
    resp = case_client.post("/cases/1/report")
    assert resp.status_code == 200
    assert b"Test case" in resp.data
    assert b"notes.txt" in resp.data
    assert b"PASS" in resp.data
    assert b"Chain intact" in resp.data
    with app.app_context():
        head = get_db().execute(
            "SELECT entry_hash FROM custody_log ORDER BY id DESC LIMIT 1"
        ).fetchone()["entry_hash"]
    assert head.encode() in resp.data


def test_report_flags_modified_file(case_client, app):
    upload(case_client)
    with open(stored_file(app), "ab") as f:
        f.write(b" tampered")
    resp = case_client.post("/cases/1/report")
    assert resp.status_code == 200
    assert b"FAIL" in resp.data
    assert b"hash mismatch" in resp.data


def test_report_flags_missing_file(case_client, app):
    upload(case_client)
    os.remove(stored_file(app))
    resp = case_client.post("/cases/1/report")
    assert b"FAIL" in resp.data
    assert b"stored file is missing" in resp.data


def test_report_logs_each_integrity_check(case_client, app):
    upload(case_client)
    case_client.post("/cases/1/report")
    rows = log_rows(app)
    assert [r["action"] for r in rows] == ["UPLOADED", "HASH_VERIFIED"]
    assert rows[-1]["notes"].startswith("Case report: PASS")


def test_report_for_case_without_evidence(case_client, app):
    resp = case_client.post("/cases/1/report")
    assert resp.status_code == 200
    assert b"No evidence has been uploaded" in resp.data
    assert log_rows(app) == []


def test_report_only_lists_this_cases_entries(case_client):
    case_client.post("/cases/new", data={"title": "Second case", "description": ""})
    upload(case_client, case_id=1, name="alpha.txt", data=b"aaa")
    upload(case_client, case_id=2, name="bravo.txt", data=b"bbb")
    resp = case_client.post("/cases/1/report")
    assert b"alpha.txt" in resp.data
    assert b"bravo.txt" not in resp.data


def test_case_page_report_button_is_a_form_with_a_csrf_token(case_client):
    html = case_client.get("/cases/1").data.decode()
    assert 'action="/cases/1/report"' in html
    form = html.split('action="/cases/1/report"')[1].split("</form>")[0]
    assert 'name="csrf_token"' in form