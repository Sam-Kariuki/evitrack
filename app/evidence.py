import os

from flask import (Blueprint, abort, current_app, flash, g, redirect,
                   render_template, request, send_file, url_for)
from werkzeug.utils import secure_filename

from datetime import datetime, timezone
from .auth import login_required
from .cases import get_case_or_404
from .custody import log_action, verify_chain
from .db import get_db
from .utils import (ALLOWED_EXTENSIONS, allowed_file, save_upload,
                    sha256_of_file)

bp = Blueprint("evidence", __name__, url_prefix="/cases")


def get_evidence_or_404(case_id, evidence_id):
    """Return (case, evidence), or 404.

    get_case_or_404 enforces case ownership. The extra case_id condition stops
    someone using a case they own to reach evidence from another case.
    """
    case = get_case_or_404(case_id)
    item = get_db().execute(
        "SELECT e.id, e.case_id, e.original_name, e.stored_name, e.sha256, "
        "e.uploaded_at, u.username AS uploader "
        "FROM evidence e JOIN users u ON u.id = e.uploaded_by "
        "WHERE e.id = ? AND e.case_id = ?",
        (evidence_id, case_id),
    ).fetchone()
    if item is None:
        abort(404)
    return case, item


def stored_path(item):
    """Absolute path of the stored file for an evidence row."""
    return os.path.abspath(
        os.path.join(current_app.config["UPLOAD_FOLDER"], item["stored_name"])
    )


def check_integrity(item):
    """Rehash the stored file and compare it with the hash recorded at upload.

    Returns (ok, message).
    """
    path = stored_path(item)
    if not os.path.isfile(path):
        return False, "stored file is missing"
    actual = sha256_of_file(path)
    if actual != item["sha256"]:
        return False, (
            f"hash mismatch (recorded {item['sha256']}, computed {actual})"
        )
    return True, f"hash matches recorded SHA-256 {actual}"


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
                    cur = db.execute(
                        "INSERT INTO evidence "
                        "(case_id, original_name, stored_name, sha256, uploaded_by) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (case_id, original_name, stored_name, digest, g.user["id"]),
                    )
                    log_action(
                        db, cur.lastrowid, g.user["id"], "UPLOADED",
                        f"File '{original_name}' uploaded ({size} bytes). "
                        f"SHA-256: {digest}",
                    )
                    db.commit()
                except Exception:
                    db.rollback()
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


@bp.route("/<int:case_id>/evidence/<int:evidence_id>")
@login_required
def detail(case_id, evidence_id):
    case, item = get_evidence_or_404(case_id, evidence_id)

    db = get_db()
    log_action(db, evidence_id, g.user["id"], "VIEWED")
    db.commit()

    history = db.execute(
        "SELECT c.id, c.timestamp, c.action, c.notes, c.entry_hash, "
        "u.username "
        "FROM custody_log c JOIN users u ON u.id = c.user_id "
        "WHERE c.evidence_id = ? ORDER BY c.id",
        (evidence_id,),
    ).fetchall()
    chain_ok, chain_broken_id, chain_message = verify_chain(db)
    return render_template(
        "evidence_detail.html",
        case=case,
        item=item,
        history=history,
        chain_ok=chain_ok,
        chain_broken_id=chain_broken_id,
        chain_message=chain_message,
    )


@bp.route("/<int:case_id>/evidence/<int:evidence_id>/verify", methods=("POST",))
@login_required
def verify(case_id, evidence_id):
    case, item = get_evidence_or_404(case_id, evidence_id)
    ok, message = check_integrity(item)
    db = get_db()
    log_action(
        db, evidence_id, g.user["id"], "HASH_VERIFIED",
        f"{'PASS' if ok else 'FAIL'}: {message}",
    )
    db.commit()
    if ok:
        flash("Integrity check passed.")
    else:
        flash("INTEGRITY CHECK FAILED: " + message)
    return redirect(
        url_for("evidence.detail", case_id=case_id, evidence_id=evidence_id)
    )


@bp.route("/<int:case_id>/evidence/<int:evidence_id>/download")
@login_required
def download(case_id, evidence_id):
    case, item = get_evidence_or_404(case_id, evidence_id)
    ok, message = check_integrity(item)
    db = get_db()
    if not ok:
        log_action(
            db, evidence_id, g.user["id"], "HASH_VERIFIED",
            f"FAIL: {message}. Download blocked.",
        )
        db.commit()
        flash("Integrity check failed, so the download was blocked. "
              "The event was logged.")
        return redirect(
            url_for("evidence.detail", case_id=case_id, evidence_id=evidence_id)
        )

    log_action(
        db, evidence_id, g.user["id"], "DOWNLOADED",
        f"Integrity verified before download. SHA-256: {item['sha256']}",
    )
    db.commit()
    return send_file(
        stored_path(item),
        as_attachment=True,
        download_name=item["original_name"],
    )

@bp.route("/<int:case_id>/report")
@login_required
def case_report(case_id):
    case = get_case_or_404(case_id)
    db = get_db()

    items = db.execute(
        "SELECT e.id, e.original_name, e.stored_name, e.sha256, "
        "e.uploaded_at, u.username AS uploader "
        "FROM evidence e JOIN users u ON u.id = e.uploaded_by "
        "WHERE e.case_id = ? ORDER BY e.id",
        (case_id,),
    ).fetchall()

    # Rehash every file for this report. Each check is logged, so the report
    # itself leaves a trace in the custody chain.
    results = []
    for item in items:
        ok, message = check_integrity(item)
        log_action(
            db, item["id"], g.user["id"], "HASH_VERIFIED",
            f"Case report: {'PASS' if ok else 'FAIL'}: {message}",
        )
        results.append({"item": item, "ok": ok, "message": message})
    db.commit()

    history = db.execute(
        "SELECT c.id, c.timestamp, c.action, c.notes, c.entry_hash, "
        "u.username, e.original_name "
        "FROM custody_log c "
        "JOIN users u ON u.id = c.user_id "
        "JOIN evidence e ON e.id = c.evidence_id "
        "WHERE e.case_id = ? ORDER BY c.id",
        (case_id,),
    ).fetchall()

    chain_ok, chain_broken_id, chain_message = verify_chain(db)
    head = db.execute(
        "SELECT id, entry_hash FROM custody_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    return render_template(
        "case_report.html",
        case=case,
        results=results,
        history=history,
        chain_ok=chain_ok,
        chain_message=chain_message,
        head=head,
        generated=generated,
    )