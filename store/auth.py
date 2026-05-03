from functools import wraps
from flask import (Blueprint, render_template, request, redirect, url_for,
                   session, flash, g)
from werkzeug.security import check_password_hash, generate_password_hash

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


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        full_name = request.form.get("full_name", "").strip()
        age      = request.form.get("age", "").strip()
        location = request.form.get("location", "").strip()

        error = None
        if not username or not email or not password:
            error = "Username, email, and password are required."
        elif len(password) < 4:
            error = "Password must be at least 4 characters."

        if error is None:
            db = get_db()
            try:
                cur = db.execute(
                    "INSERT INTO users(username, email, password_hash, full_name, age, location) "
                    "VALUES (?,?,?,?,?,?)",
                    (username, email, generate_password_hash(password),
                     full_name or None,
                     int(age) if age.isdigit() else None,
                     location or None),
                )
                db.commit()
                session.clear()
                session["user_id"] = cur.lastrowid
                return redirect(url_for("home"))
            except Exception as e:
                msg = str(e).lower()
                if "users.username" in msg:
                    error = "Username already taken."
                elif "users.email" in msg:
                    error = "Email already registered."
                else:
                    error = "Could not register."
        flash(error, "error")
    return render_template("auth/register.html")


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
        flash("Invalid credentials.", "error")
    return render_template("auth/login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))
