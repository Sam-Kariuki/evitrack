from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, url_for)

from .auth import login_required
from .db import get_db

bp = Blueprint("cases", __name__, url_prefix="/cases")

TITLE_MIN, TITLE_MAX = 3, 120
DESC_MAX = 2000

LIST_QUERY = (
    "SELECT c.id, c.title, c.status, c.created_at, u.username AS owner "
    "FROM cases c JOIN users u ON u.id = c.created_by"
)


def get_case_or_404(case_id):
    case = get_db().execute(
        "SELECT c.id, c.title, c.description, c.status, c.created_by, "
        "c.created_at, u.username AS owner "
        "FROM cases c JOIN users u ON u.id = c.created_by WHERE c.id = ?",
        (case_id,),
    ).fetchone()
    if case is None:
        abort(404)
    if g.user["role"] != "admin" and case["created_by"] != g.user["id"]:
        abort(404)
    return case


def validate_case_form(form):
    title = form.get("title", "").strip()
    description = form.get("description", "").strip()
    error = None
    if not TITLE_MIN <= len(title) <= TITLE_MAX:
        error = f"Title must be {TITLE_MIN}-{TITLE_MAX} characters."
    elif len(description) > DESC_MAX:
        error = f"Description must be at most {DESC_MAX} characters."
    return title, description, error


@bp.route("/")
@login_required
def index():
    db = get_db()
    if g.user["role"] == "admin":
        rows = db.execute(LIST_QUERY + " ORDER BY c.id DESC").fetchall()
    else:
        rows = db.execute(
            LIST_QUERY + " WHERE c.created_by = ? ORDER BY c.id DESC",
            (g.user["id"],),
        ).fetchall()
    return render_template("case_list.html", cases=rows)


@bp.route("/new", methods=("GET", "POST"))
@login_required
def new():
    values = {"title": "", "description": ""}
    if request.method == "POST":
        title, description, error = validate_case_form(request.form)
        values = {"title": title, "description": description}
        if error is None:
            db = get_db()
            cur = db.execute(
                "INSERT INTO cases (title, description, created_by) VALUES (?, ?, ?)",
                (title, description, g.user["id"]),
            )
            db.commit()
            flash("Case created.")
            return redirect(url_for("cases.detail", case_id=cur.lastrowid))
        flash(error)
    return render_template("case_form.html", case=None, values=values)


@bp.route("/<int:case_id>")
@login_required
def detail(case_id):
    case = get_case_or_404(case_id)
    return render_template("case_detail.html", case=case)


@bp.route("/<int:case_id>/edit", methods=("GET", "POST"))
@login_required
def edit(case_id):
    case = get_case_or_404(case_id)
    if case["status"] == "closed":
        flash("Closed cases cannot be edited.")
        return redirect(url_for("cases.detail", case_id=case_id))

    values = {"title": case["title"], "description": case["description"] or ""}
    if request.method == "POST":
        title, description, error = validate_case_form(request.form)
        values = {"title": title, "description": description}
        if error is None:
            db = get_db()
            db.execute(
                "UPDATE cases SET title = ?, description = ? WHERE id = ?",
                (title, description, case_id),
            )
            db.commit()
            flash("Case updated.")
            return redirect(url_for("cases.detail", case_id=case_id))
        flash(error)
    return render_template("case_form.html", case=case, values=values)


@bp.route("/<int:case_id>/status", methods=("POST",))
@login_required
def set_status(case_id):
    case = get_case_or_404(case_id)
    new_status = request.form.get("status")
    if new_status not in ("open", "closed"):
        abort(400)
    if new_status == "open" and g.user["role"] != "admin":
        abort(403)
    if new_status != case["status"]:
        db = get_db()
        db.execute("UPDATE cases SET status = ? WHERE id = ?", (new_status, case_id))
        db.commit()
        flash(f"Case {new_status}.")
    return redirect(url_for("cases.detail", case_id=case_id))