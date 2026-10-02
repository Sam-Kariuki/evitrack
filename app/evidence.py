import os

from flask import (Blueprint, current_app, flash, g, redirect,
                   render_template, request, url_for)
from werkzeug.utils import secure_filename

from .auth import login_required
from .cases import get_case_or_404
from .db import get_db
from .utils import ALLOWED_EXTENSIONS, allowed_file, save_upload

bp = Blueprint("evidence", __name__, url_prefix="/cases")


@bp.route("/<int:case_id>/evidence/upload", methods=("GET", "POST"))
@login_required
def upload(case_id):
    case = get_case_or_404(case_id)
    if case["status"] == "closed":
        flash("Evidence cannot be added to a closed case.")
        return redirect(url_for("cases.detail", case_id=case_id))

    if request.method == "POST":
        file = request.files.get("file")
        error = None
        original_name = ""

        if file is None or file.filename == "":
            error = "Please choose a file."
        else:
            original_name = secure_filename(file.filename)
            if not original_name:
                error = "Invalid file name."
            elif not allowed_file(original_name):
                error = "That file type is not allowed."

        if error is None:
            folder = current_app.config["UPLOAD_FOLDER"]
            stored_name, digest, size = save_upload(file, folder)
            if size == 0:
                os.remove(os.path.join(folder, stored_name))
                error = "The file is empty."
            else:
                db = get_db()
                try:
                    db.execute(
                        "INSERT INTO evidence "
                        "(case_id, original_name, stored_name, sha256, uploaded_by) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (case_id, original_name, stored_name, digest, g.user["id"]),
                    )
                    db.commit()
                except Exception:
                    os.remove(os.path.join(folder, stored_name))
                    raise
                flash("Evidence uploaded and SHA-256 hash recorded.")
                return redirect(url_for("cases.detail", case_id=case_id))

        flash(error)

    max_mb = current_app.config["MAX_CONTENT_LENGTH"] // (1024 * 1024)
    return render_template(
        "evidence_upload.html",
        case=case,
        allowed=sorted(ALLOWED_EXTENSIONS),
        max_mb=max_mb,
    )