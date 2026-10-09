import os
from datetime import timedelta

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect

load_dotenv()

csrf = CSRFProtect()

DEFAULT_SECRET_KEY = "dev-only-change-me"


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY),
        DATABASE=os.environ.get(
            "DATABASE", os.path.join(app.instance_path, "evitrack.sqlite")
        ),
        UPLOAD_FOLDER=os.environ.get(
            "UPLOAD_FOLDER", os.path.join(app.instance_path, "uploads")
        ),
        MAX_CONTENT_LENGTH=int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Set SESSION_COOKIE_SECURE=1 once the app is served over HTTPS.
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
        PERMANENT_SESSION_LIFETIME=timedelta(
            hours=int(os.environ.get("SESSION_HOURS", "8"))
        ),
        # Set ALLOW_REGISTRATION=0 on a public deployment and create accounts
        # with the create-user and create-admin commands instead.
        ALLOW_REGISTRATION=os.environ.get("ALLOW_REGISTRATION", "1") == "1",
    )

    if test_config:
        app.config.update(test_config)

    # A known secret key lets anyone forge sessions and CSRF tokens.
    if (
        app.config["SECRET_KEY"] in ("", DEFAULT_SECRET_KEY)
        and not app.testing
        and not app.debug
    ):
        raise RuntimeError(
            "SECRET_KEY is not set. Put a long random SECRET_KEY in the "
            "environment or the .env file before running outside debug mode."
        )

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    csrf.init_app(app)

    from . import admin, auth, cases, db, evidence, security

    db.init_app(app)
    security.init_app(app)

    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(cases.bp)
    app.register_blueprint(evidence.bp)

    app.cli.add_command(auth.create_admin_command)
    app.cli.add_command(auth.create_user_command)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        auth.load_logged_in_user()
        return render_template("413.html"), 413

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    return app