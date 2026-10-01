import pytest

from app import create_app
from app.db import init_db


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "WTF_CSRF_ENABLED": False,
        "DATABASE": str(tmp_path / "test.sqlite"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })
    with app.app_context():
        init_db()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


class AuthActions:
    def __init__(self, client):
        self._client = client

    def register(self, username="alice", password="correct-horse-1"):
        return self._client.post("/auth/register", data={
            "username": username, "password": password, "confirm": password})

    def login(self, username="alice", password="correct-horse-1"):
        return self._client.post("/auth/login", data={
            "username": username, "password": password})

    def logout(self):
        return self._client.post("/auth/logout")


@pytest.fixture
def auth(client):
    return AuthActions(client)