import io
import re

import pytest

from app import DEFAULT_SECRET_KEY, create_app
from app.db import init_db


def config_for(tmp_path, **overrides):
    config = {
        "TESTING": True,
        "SECRET_KEY": "test",
        "WTF_CSRF_ENABLED": False,
        "DATABASE": str(tmp_path / "test.sqlite"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    }
    config.update(overrides)
    return config


def make_app(tmp_path, **overrides):
    app = create_app(config_for(tmp_path, **overrides))
    with app.app_context():
        init_db()
    return app


# ---- secret key ----

@pytest.mark.parametrize("key", [DEFAULT_SECRET_KEY, ""])
def test_weak_secret_key_refused_outside_debug(tmp_path, key):
    with pytest.raises(RuntimeError):
        create_app(config_for(tmp_path, TESTING=False, DEBUG=False, SECRET_KEY=key))


def test_default_secret_key_allowed_in_debug(tmp_path):
    app = create_app(
        config_for(tmp_path, TESTING=False, DEBUG=True, SECRET_KEY=DEFAULT_SECRET_KEY)
    )
    assert app.debug


def test_real_secret_key_accepted_outside_debug(tmp_path):
    app = create_app(
        config_for(tmp_path, TESTING=False, DEBUG=False, SECRET_KEY="x" * 32)
    )
    assert not app.debug


# ---- CSRF coverage ----

def post_routes(app):
    adapter = app.url_map.bind("localhost")
    for rule in app.url_map.iter_rules():
        if "POST" not in rule.methods or rule.endpoint == "static":
            continue
        values = {name: 1 for name in rule.arguments}
        yield rule.endpoint, adapter.build(rule.endpoint, values, method="POST")


def test_every_post_route_rejects_requests_without_a_csrf_token(tmp_path):
    app = make_app(tmp_path, WTF_CSRF_ENABLED=True)
    client = app.test_client()
    routes = list(post_routes(app))
    assert len(routes) >= 8  # guards against the loop silently checking nothing
    for endpoint, url in routes:
        resp = client.post(url, data={})
        assert resp.status_code == 400, (
            f"{endpoint} ({url}) accepted a POST without a CSRF token"
        )


def test_post_with_a_valid_token_passes_the_csrf_check(tmp_path):
    app = make_app(tmp_path, WTF_CSRF_ENABLED=True)
    client = app.test_client()
    page = client.get("/auth/login")
    token = re.search(
        rb'name="csrf_token" value="([^"]+)"', page.data
    ).group(1).decode()
    resp = client.post(
        "/auth/login",
        data={"username": "nobody", "password": "x", "csrf_token": token},
    )
    assert resp.status_code == 200  # wrong login, but not rejected by CSRF


# ---- session cookie ----

def test_session_cookie_flags(tmp_path):
    app = make_app(tmp_path, SESSION_COOKIE_SECURE=True)
    client = app.test_client()
    client.post("/auth/register", data={
        "username": "alice", "password": "correct-horse-1",
        "confirm": "correct-horse-1"})
    resp = client.post("/auth/login", data={
        "username": "alice", "password": "correct-horse-1"})
    cookie = " ".join(resp.headers.getlist("Set-Cookie"))
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=Lax" in cookie
    assert "Expires=" in cookie  # permanent session, so it has a lifetime


# ---- security headers ----

def test_security_headers_on_every_response(client):
    resp = client.get("/")
    csp = resp.headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "same-origin"
    assert "Strict-Transport-Security" not in resp.headers


def test_error_pages_also_get_headers(client):
    resp = client.get("/no-such-page")
    assert resp.status_code == 404
    assert resp.headers["X-Content-Type-Options"] == "nosniff"


def test_logged_in_pages_are_not_cached(client, auth):
    auth.register()
    auth.login()
    resp = client.get("/cases/")
    assert resp.headers["Cache-Control"] == "no-store"


def test_logged_out_pages_keep_default_caching(client):
    resp = client.get("/")
    assert resp.headers.get("Cache-Control") != "no-store"


def test_static_files_stay_cacheable(client, auth):
    auth.register()
    auth.login()
    resp = client.get("/static/style.css")
    assert resp.status_code == 200
    assert resp.headers.get("Cache-Control") != "no-store"


def test_evidence_download_is_not_cached(client, auth):
    auth.register()
    auth.login()
    client.post("/cases/new", data={"title": "Test case", "description": "x"})
    client.post(
        "/cases/1/evidence/upload",
        data={"file": (io.BytesIO(b"hello"), "n.txt")},
        content_type="multipart/form-data",
    )
    resp = client.get("/cases/1/evidence/1/download")
    assert resp.status_code == 200
    assert resp.headers["Cache-Control"] == "no-store"
    assert resp.headers["X-Content-Type-Options"] == "nosniff"


def test_hsts_only_when_cookies_are_secure(tmp_path):
    app = make_app(tmp_path, SESSION_COOKIE_SECURE=True)
    resp = app.test_client().get("/")
    assert "max-age=" in resp.headers["Strict-Transport-Security"]


# ---- error handling ----

def test_server_errors_do_not_leak_details(tmp_path):
    app = make_app(tmp_path, PROPAGATE_EXCEPTIONS=False)

    @app.route("/boom")
    def boom():
        raise ZeroDivisionError("secret-internal-detail")

    resp = app.test_client().get("/boom")
    assert resp.status_code == 500
    assert b"Something went wrong" in resp.data
    assert b"secret-internal-detail" not in resp.data
    assert b"Traceback" not in resp.data