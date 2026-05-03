from functools import wraps
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, g)
from werkzeug.security import check_password_hash

from db import get_db


bp = Blueprint("auth", __name__, url_prefix="/auth")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def load_logged_in_user():
    uid = session.get("user_id")
    if uid is None:
        g.user = None
        return
    g.user = get_db().execute(
        "SELECT id, username, email, full_name, age, location FROM users WHERE id = ?",
        (uid,),
    ).fetchone()


PUBLIC_ENDPOINTS = {"auth.login", "auth.logout", "static"}


def require_login_globally():
    if g.user is not None:
        return
    if request.endpoint in PUBLIC_ENDPOINTS:
        return
    return redirect(url_for("auth.login", next=request.path))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password   = request.form.get("password", "")
        row = get_db().execute(
            "SELECT id, password_hash FROM users WHERE username = ? OR email = ?",
            (identifier, identifier.lower()),
        ).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            session.clear()
            session["user_id"] = row["id"]
            return redirect(request.args.get("next") or url_for("home"))
        flash("بيانات الدخول غير صحيحة.", "error")
    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))
