import hashlib
import io
import re
import sqlite3

import pytest

from app.custody import GENESIS_HASH, compute_entry_hash
from app.db import get_db
import os

from app.custody import GENESIS_HASH, compute_entry_hash, verify_chain


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

def stored_file(app, evidence_id=1):
    """Path of the stored file for an evidence row, so tests can tamper with it."""
    with app.app_context():
        name = get_db().execute(
            "SELECT stored_name FROM evidence WHERE id = ?", (evidence_id,)
        ).fetchone()["stored_name"]
        return os.path.join(app.config["UPLOAD_FOLDER"], name)


def actions(app):
    return [r["action"] for r in log_rows(app)]


# ---- download and verify (issue #7) ----

def test_download_returns_file_and_logs(case_client, app):
    upload(case_client)
    resp = case_client.get("/cases/1/evidence/1/download")
    assert resp.status_code == 200
    assert resp.data == b"hello evidence"
    assert "notes.txt" in resp.headers["Content-Disposition"]
    assert actions(app) == ["UPLOADED", "DOWNLOADED"]


def test_verify_passes_on_untouched_file(case_client, app):
    upload(case_client)
    resp = case_client.post("/cases/1/evidence/1/verify")
    assert resp.status_code == 302
    rows = log_rows(app)
    assert rows[-1]["action"] == "HASH_VERIFIED"
    assert rows[-1]["notes"].startswith("PASS")


def test_verify_detects_modified_file(case_client, app):
    upload(case_client)
    with open(stored_file(app), "ab") as f:
        f.write(b" tampered")
    case_client.post("/cases/1/evidence/1/verify")
    last = log_rows(app)[-1]
    assert last["action"] == "HASH_VERIFIED"
    assert last["notes"].startswith("FAIL")
    assert "mismatch" in last["notes"]


def test_verify_detects_missing_file(case_client, app):
    upload(case_client)
    os.remove(stored_file(app))
    case_client.post("/cases/1/evidence/1/verify")
    last = log_rows(app)[-1]
    assert last["notes"].startswith("FAIL")
    assert "missing" in last["notes"]


def test_download_blocked_if_file_was_modified(case_client, app):
    upload(case_client)
    with open(stored_file(app), "ab") as f:
        f.write(b" tampered")
    resp = case_client.get("/cases/1/evidence/1/download")
    assert resp.status_code == 302
    assert b"tampered" not in resp.data
    assert actions(app) == ["UPLOADED", "HASH_VERIFIED"]
    assert "Download blocked" in log_rows(app)[-1]["notes"]


def test_download_and_verify_require_login(client):
    assert client.get("/cases/1/evidence/1/download").status_code == 302
    assert client.post("/cases/1/evidence/1/verify").status_code == 302


def test_other_investigator_cannot_download_or_verify(client, auth, app):
    auth.register("alice")
    auth.login("alice")
    client.post("/cases/new", data={"title": "Alice case", "description": ""})
    upload(client)
    auth.logout()
    auth.register("bob")
    auth.login("bob")
    assert client.get("/cases/1/evidence/1/download").status_code == 404
    assert client.post("/cases/1/evidence/1/verify").status_code == 404
    assert actions(app) == ["UPLOADED"]


# ---- chain verification (issue #10) ----

def test_verify_chain_passes_on_clean_log(case_client, app):
    upload(case_client, name="a.txt", data=b"aaa")
    upload(case_client, name="b.txt", data=b"bbb")
    case_client.get("/cases/1/evidence/1")
    with app.app_context():
        ok, broken_id, message = verify_chain(get_db())
    assert ok is True
    assert broken_id is None
    assert "3 entries" in message


def test_verify_chain_passes_on_empty_log(app):
    with app.app_context():
        assert verify_chain(get_db())[0] is True


def test_verify_chain_detects_edited_entry(case_client, app):
    upload(case_client, name="a.txt", data=b"aaa")
    upload(case_client, name="b.txt", data=b"bbb")
    with app.app_context():
        db = get_db()
        # The trigger blocks edits through the app. Removing it simulates an
        # attacker with direct access to the database file.
        db.execute("DROP TRIGGER custody_log_no_update")
        db.execute("UPDATE custody_log SET notes = 'changed' WHERE id = 1")
        db.commit()
        ok, broken_id, _ = verify_chain(db)
    assert ok is False
    assert broken_id == 1


def test_verify_chain_detects_deleted_entry(case_client, app):
    for i in range(3):
        upload(case_client, name=f"f{i}.txt", data=bytes([65 + i]) * 5)
    with app.app_context():
        db = get_db()
        db.execute("DROP TRIGGER custody_log_no_delete")
        db.execute("DELETE FROM custody_log WHERE id = 2")
        db.commit()
        ok, broken_id, _ = verify_chain(db)
    assert ok is False
    assert broken_id == 3


def test_detail_page_shows_chain_status(case_client):
    upload(case_client)
    resp = case_client.get("/cases/1/evidence/1")
    assert b"Chain intact" in resp.data

def test_verify_form_includes_csrf_token(case_client):
    upload(case_client)
    resp = case_client.get("/cases/1/evidence/1")
    assert b'name="csrf_token"' in resp.data