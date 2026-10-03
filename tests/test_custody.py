import hashlib
import io
import re
import sqlite3

import pytest

from app.custody import GENESIS_HASH, compute_entry_hash
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


@pytest.fixture
def case_client(client, auth):
    auth.register()
    auth.login()
    client.post("/cases/new", data={"title": "Test case", "description": "x"})
    return client


def test_upload_creates_custody_entry(case_client, app):
    upload(case_client)
    rows = log_rows(app)
    assert len(rows) == 1
    row = rows[0]
    assert row["action"] == "UPLOADED"
    assert row["evidence_id"] == 1
    assert row["user_id"] == 1
    assert row["prev_hash"] == GENESIS_HASH
    assert re.fullmatch(r"[0-9a-f]{64}", row["entry_hash"])
    assert "14 bytes" in row["notes"]
    assert hashlib.sha256(b"hello evidence").hexdigest() in row["notes"]


def test_entries_are_chained(case_client, app):
    upload(case_client, name="a.txt", data=b"aaa")
    upload(case_client, name="b.txt", data=b"bbb")
    first, second = log_rows(app)
    assert second["prev_hash"] == first["entry_hash"]


def test_entry_hash_is_reproducible(case_client, app):
    upload(case_client)
    row = log_rows(app)[0]
    expected = compute_entry_hash(
        row["prev_hash"], row["evidence_id"], row["user_id"],
        row["action"], row["notes"], row["timestamp"],
    )
    assert row["entry_hash"] == expected


def test_changing_any_field_changes_the_hash():
    base = (GENESIS_HASH, 1, 1, "UPLOADED", "n", "2026-10-02 10:00:00")
    original = compute_entry_hash(*base)
    changes = ["f" * 64, 2, 2, "VIEWED", "x", "2026-10-02 10:00:01"]
    for index, new_value in enumerate(changes):
        fields = list(base)
        fields[index] = new_value
        assert compute_entry_hash(*fields) != original


def test_viewing_evidence_is_logged(case_client, app):
    upload(case_client)
    resp = case_client.get("/cases/1/evidence/1")
    assert resp.status_code == 200
    assert [r["action"] for r in log_rows(app)] == ["UPLOADED", "VIEWED"]
    assert b"UPLOADED" in resp.data
    assert b"VIEWED" in resp.data


def test_evidence_page_requires_login(client):
    resp = client.get("/cases/1/evidence/1")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_rejected_upload_creates_no_entry(case_client, app):
    upload(case_client, name="run.exe")
    assert log_rows(app) == []


def test_other_investigator_cannot_view_or_log(client, auth, app):
    auth.register("alice")
    auth.login("alice")
    client.post("/cases/new", data={"title": "Alice case", "description": ""})
    upload(client)
    auth.logout()
    auth.register("bob")
    auth.login("bob")
    assert client.get("/cases/1/evidence/1").status_code == 404
    assert [r["action"] for r in log_rows(app)] == ["UPLOADED"]


def test_evidence_must_belong_to_case_in_url(case_client, app):
    case_client.post("/cases/new", data={"title": "Second case", "description": ""})
    upload(case_client, case_id=1)
    assert case_client.get("/cases/2/evidence/1").status_code == 404
    assert [r["action"] for r in log_rows(app)] == ["UPLOADED"]


def test_custody_log_is_append_only(case_client, app):
    upload(case_client)
    with app.app_context():
        db = get_db()
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("UPDATE custody_log SET action = 'TAMPERED' WHERE id = 1")
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("DELETE FROM custody_log WHERE id = 1")
    assert log_rows(app)[0]["action"] == "UPLOADED"