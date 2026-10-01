from app.db import get_db


def test_index_loads(client):
    assert client.get("/").status_code == 200


def test_tables_exist(app):
    with app.app_context():
        rows = get_db().execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    names = {row["name"] for row in rows}
    assert {"users", "cases", "evidence", "custody_log"} <= names


def test_foreign_keys_enabled(app):
    with app.app_context():
        assert get_db().execute("PRAGMA foreign_keys").fetchone()[0] == 1