from flask import Blueprint, render_template

from .auth import role_required
from .db import get_db

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@role_required("admin")
def users():
    rows = get_db().execute(
        "SELECT id, username, role, created_at FROM users ORDER BY id"
    ).fetchall()
    return render_template("admin_users.html", users=rows)