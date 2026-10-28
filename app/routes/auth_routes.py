from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auction.dashboard"))

    if request.method == "POST":
        data = request.form if request.form else request.get_json(silent=True) or {}
        username_or_email = data.get("username_or_email", "").strip()
        password = data.get("password", "")

        user = User.query.filter(
            (User.username == username_or_email) | (User.email == username_or_email)
        ).first()

        if user and user.check_password(password):
            login_user(user, remember=True)
            flash("Welcome back, " + user.username + "!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("auction.dashboard"))
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("auction.dashboard"))

    if request.method == "POST":
        data = request.form if request.form else request.get_json(silent=True) or {}
        username = data.get("username", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        confirm_password = data.get("confirm_password", "")

        errors = []
        if len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if "@" not in email or "." not in email:
            errors.append("Please enter a valid email address.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        if User.query.filter_by(username=username).first():
            errors.append("Username already taken. Please pick another.")
        if User.query.filter_by(email=email).first():
            errors.append("Email already registered.")

        if errors:
            for err in errors:
                flash(err, "danger")
        else:
            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash("Registration successful! Welcome to IPL Auction Simulator.", "success")
            return redirect(url_for("auction.dashboard"))

    return render_template("register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auction.index"))


@auth_bp.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)


# API Endpoints
@auth_bp.route("/api/auth/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not username or not email or not password:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"success": False, "message": "Username or email already exists"}), 409

    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    login_user(user)
    return jsonify({"success": True, "user": user.to_dict()}), 201


@auth_bp.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    ident = data.get("username_or_email", "").strip()
    password = data.get("password", "")

    user = User.query.filter((User.username == ident) | (User.email == ident)).first()
    if user and user.check_password(password):
        login_user(user)
        return jsonify({"success": True, "user": user.to_dict()})
    return jsonify({"success": False, "message": "Invalid credentials"}), 401


@auth_bp.route("/api/auth/logout", methods=["POST"])
@login_required
def api_logout():
    logout_user()
    return jsonify({"success": True, "message": "Logged out successfully"})


@auth_bp.route("/api/auth/me", methods=["GET"])
def api_me():
    if current_user.is_authenticated:
        return jsonify({"authenticated": True, "user": current_user.to_dict()})
    return jsonify({"authenticated": False, "user": None})
