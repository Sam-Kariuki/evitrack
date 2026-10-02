import os

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect

load_dotenv()

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-me"),
        DATABASE=os.environ.get(
            "DATABASE", os.path.join(app.instance_path, "evitrack.sqlite")
        ),
        UPLOAD_FOLDER=os.environ.get(
            "UPLOAD_FOLDER", os.path.join(app.instance_path, "uploads")
        ),
        MAX_CONTENT_LENGTH=int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    csrf.init_app(app)

    from . import admin, auth, cases, db, evidence
    db.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(cases.bp)
    app.register_blueprint(evidence.bp)
    app.cli.add_command(auth.create_admin_command)

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
        return render_template("413.html"), 413

    return app