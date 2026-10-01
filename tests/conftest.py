import pytest

from app import create_app
from app.db import init_db


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "DATABASE": str(tmp_path / "test.sqlite"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })
    with app.app_context():
        init_db()
    yield app


@pytest.fixture
def client(app):
    return app.test_client()