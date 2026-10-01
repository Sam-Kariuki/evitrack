import os

from dotenv import load_dotenv
from flask import Flask, render_template

load_dotenv()


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
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    from . import db
    db.init_app(app)

    @app.route("/")
    def index():
        return render_template("index.html")

    return app