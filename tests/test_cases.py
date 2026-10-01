import pytest
from werkzeug.security import generate_password_hash

from app.db import get_db


def make_admin(app, username="boss", password="correct-horse-1"):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
            (username, generate_password_hash(password)),
        )
        db.commit()


def create_case(client, title="Laptop seizure", description="Initial triage"):
    return client.post("/cases/new", data={"title": title, "description": description})


def get_case(app, case_id):
    with app.app_context():
        return get_db().execute(
            "SELECT * FROM cases WHERE id = ?", (case_id,)
        ).fetchone()


def test_login_required(client):
    resp = client.get("/cases/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_create_case(client, auth, app):
    auth.register()
    auth.login()
    assert create_case(client).status_code == 302
    case = get_case(app, 1)
    assert case["title"] == "Laptop seizure"
    assert case["created_by"] == 1
    assert case["status"] == "open"


@pytest.mark.parametrize(("title", "description", "message"), [
    ("ab", "ok", b"Title must be"),
    ("x" * 121, "ok", b"Title must be"),
    ("Valid title", "d" * 2001, b"Description must be"),
])
def test_case_validation(client, auth, title, description, message):
    auth.register()
    auth.login()
    resp = create_case(client, title, description)
    assert message in resp.data


def test_list_shows_only_own_cases(client, auth):
    auth.register("alice")
    auth.login("alice")
    create_case(client, title="Alice case")
    auth.logout()
    auth.register("bob")
    auth.login("bob")
    create_case(client, title="Bob case")
    resp = client.get("/cases/")
    assert b"Bob case" in resp.data
    assert b"Alice case" not in resp.data


def test_other_investigator_gets_404(client, auth):
    auth.register("alice")
    auth.login("alice")
    create_case(client)
    auth.logout()
    auth.register("bob")
    auth.login("bob")
    assert client.get("/cases/1").status_code == 404
    assert client.get("/cases/1/edit").status_code == 404
    assert client.post("/cases/1/status", data={"status": "closed"}).status_code == 404


def test_admin_can_view_any_case(client, auth, app):
    auth.register("alice")
    auth.login("alice")
    create_case(client, title="Alice case")
    auth.logout()
    make_admin(app)
    auth.login("boss")
    assert client.get("/cases/1").status_code == 200
    assert b"Alice case" in client.get("/cases/").data


def test_owner_can_edit_open_case(client, auth, app):
    auth.register()
    auth.login()
    create_case(client)
    resp = client.post("/cases/1/edit", data={"title": "New title", "description": "Updated"})
    assert resp.status_code == 302
    assert get_case(app, 1)["title"] == "New title"


def test_closed_case_cannot_be_edited(client, auth, app):
    auth.register()
    auth.login()
    create_case(client)
    client.post("/cases/1/status", data={"status": "closed"})
    resp = client.post("/cases/1/edit", data={"title": "Tampered title", "description": "x"})
    assert resp.status_code == 302
    assert get_case(app, 1)["title"] == "Laptop seizure"


def test_only_admin_can_reopen(client, auth, app):
    auth.register()
    auth.login()
    create_case(client)
    client.post("/cases/1/status", data={"status": "closed"})
    assert client.post("/cases/1/status", data={"status": "open"}).status_code == 403
    assert get_case(app, 1)["status"] == "closed"
    auth.logout()
    make_admin(app)
    auth.login("boss")
    assert client.post("/cases/1/status", data={"status": "open"}).status_code == 302
    assert get_case(app, 1)["status"] == "open"


def test_invalid_status_rejected(client, auth):
    auth.register()
    auth.login()
    create_case(client)
    assert client.post("/cases/1/status", data={"status": "deleted"}).status_code == 400


def test_html_in_title_is_escaped(client, auth):
    auth.register()
    auth.login()
    create_case(client, title="<script>alert(1)</script>")
    resp = client.get("/cases/1")
    assert b"<script>alert(1)</script>" not in resp.data
    assert b"&lt;script&gt;" in resp.data


def test_sql_injection_text_stored_literally(client, auth, app):
    auth.register()
    auth.login()
    payload = "x'); DROP TABLE cases;--"
    create_case(client, title=payload)
    assert get_case(app, 1)["title"] == payload
    assert client.get("/cases/").status_code == 200