import functools
import re
import sqlite3

import click
from flask import (Blueprint, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .lockout import clear_failed_logins, is_locked_out, record_failed_login

bp = Blueprint("auth", __name__, url_prefix="/auth")

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
MIN_PASSWORD_LENGTH = 10

# Checked when the username does not exist, so a failed login takes about the
# same time whether or not the account is real.
DUMMY_HASH = generate_password_hash("not-a-real-password")


@bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        g.user = get_db().execute(
            "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        if g.user is None:
            session.clear()


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @functools.wraps(view)
        def wrapped(*args, **kwargs):
            if g.user is None:
                flash("Please log in to continue.")
                return redirect(url_for("auth.login"))
            if g.user["role"] not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        error = None
        if not USERNAME_RE.match(username):
            error = "Username must be 3-30 characters: letters, numbers, underscore."
        elif len(password) < MIN_PASSWORD_LENGTH:
            error = f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        elif password != confirm:
            error = "Passwords do not match."

        if error is None:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
            except sqlite3.IntegrityError:
                error = "That username is already taken."
            else:
                flash("Account created. Please log in.")
                return redirect(url_for("auth.login"))

        flash(error)
    return render_template("register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()

        # Checked before the password, so a correct guess made during a
        # lockout is refused too.
        if is_locked_out(db, username):
            flash("Too many failed login attempts. Please try again in a few minutes.")
            return render_template("login.html"), 429

        user = db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user is None:
            check_password_hash(DUMMY_HASH, password)
            valid = False
        else:
            valid = check_password_hash(user["password_hash"], password)

        if not valid:
            record_failed_login(db, username, request.remote_addr)
            flash("Invalid username or password.")
        else:
            clear_failed_logins(db, username)
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = True
            return redirect(url_for("index"))
    return render_template("login.html")


@bp.route("/logout", methods=("POST",))
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("index"))


@click.command("create-admin")
@click.argument("username")
@click.password_option()
def create_admin_command(username, password):
    """Create an administrator account."""
    username = username.strip().lower()
    if not USERNAME_RE.match(username) or len(password) < MIN_PASSWORD_LENGTH:
        raise click.ClickException(
            f"Invalid username, or password shorter than {MIN_PASSWORD_LENGTH} characters."
        )
    db = get_db()
    try:
        db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
            (username, generate_password_hash(password)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        raise click.ClickException("That username already exists.")
    click.echo(f"Administrator '{username}' created.")