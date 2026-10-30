"""Web routes.

Fixes versus the original ss-ums routes.py:

* ``/user/<id>`` actually queries the database (the original rendered the
  list template with no users) and 404s for an unknown id;
* ``/users`` is searchable, filterable by member/guest, and paginated
  (the original did an unbounded ``query.all()``);
* import is a POST with an uploaded CSV, not a GET that hard-coded
  ``f:\\Code\\ss-ums\\data\\all_users.csv`` and crashed on a second import;
* ``/report`` is the mp-active-users report, served from the same database:
  an HTML summary, a downloadable PDF, and member/guest CSV downloads.
"""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for

from . import db
from .importers import import_users_to_db, load_users_from_csv
from .models import User
from .reporting import export_to_pdf, split_users_to_csv, summarize

bp = Blueprint("main", __name__)


def _page_size() -> int:
    from flask import current_app

    return int(current_app.config.get("UMS_PAGE_SIZE", 25))


@bp.route("/")
@bp.route("/index")
def index():
    total = User.query.count()
    guests = User.query.filter(User.user_type == "Guest").count()
    return render_template("index.html", title="Home", total=total, guests=guests)


@bp.route("/users")
def users():
    query = request.args.get("q", "").strip()
    kind = request.args.get("kind", "").strip().lower()
    page = request.args.get("page", 1, type=int)
    stmt = User.query
    if query:
        like = f"%{query}%"
        stmt = stmt.filter(
            (User.display_name.like(like))
            | (User.user_principal_name.like(like))
            | (User.mail.like(like))
        )
    if kind == "guest":
        stmt = stmt.filter(User.user_type == "Guest")
    elif kind == "member":
        stmt = stmt.filter(User.user_type != "Guest")
    pagination = stmt.order_by(User.display_name).paginate(
        page=page, per_page=_page_size(), error_out=False
    )
    return render_template(
        "users.html", title="Users", pagination=pagination, q=query, kind=kind
    )


@bp.route("/user/<user_id>")
def user_detail(user_id: str):
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    return render_template("user.html", title="User Profile", user=user)


@bp.route("/import", methods=["GET", "POST"])
def import_users():
    if request.method == "GET":
        return render_template("import.html", title="Import users")
    upload = request.files.get("csv_file")
    if upload is None or not upload.filename:
        flash("Choose a CSV file to import.")
        return redirect(url_for("main.import_users"))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "upload.csv"
        upload.save(path)
        try:
            parsed = load_users_from_csv(path)
        except (ValueError, FileNotFoundError) as exc:
            flash(f"Could not import that file: {exc}")
            return redirect(url_for("main.import_users"))
        result = import_users_to_db(db, parsed)
    flash(
        f"Imported {result.imported} new, updated {result.updated} "
        f"existing, from {result.rows_read} rows."
    )
    return redirect(url_for("main.users"))


@bp.route("/report")
def report():
    users = [user.to_directory() for user in User.query.order_by(User.display_name).all()]
    return render_template("report.html", title="Report", summary=summarize(users))


@bp.route("/report.pdf")
def report_pdf():
    users = [user.to_directory() for user in User.query.order_by(User.display_name).all()]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "user_analysis_report.pdf"
        export_to_pdf(users, path)
        data = path.read_bytes()
    return send_file(
        io.BytesIO(data), mimetype="application/pdf",
        as_attachment=True, download_name="user_analysis_report.pdf",
    )


@bp.route("/report/<kind>.csv")
def report_csv(kind: str):
    if kind not in ("internal", "external"):
        abort(404)
    users = [user.to_directory() for user in User.query.order_by(User.display_name).all()]
    with tempfile.TemporaryDirectory() as tmp:
        internal = Path(tmp) / "internal_users.csv"
        external = Path(tmp) / "external_users.csv"
        split_users_to_csv(users, internal, external)
        data = (internal if kind == "internal" else external).read_bytes()
    return send_file(
        io.BytesIO(data), mimetype="text/csv",
        as_attachment=True, download_name=f"{kind}_users.csv",
    )
