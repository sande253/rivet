"""UI routes — public landing and protected dashboard."""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

ui_bp = Blueprint("ui", __name__)


@ui_bp.route("/")
def index():
    """Root: redirect authenticated users to dashboard, guests to login."""
    if current_user.is_authenticated:
        return redirect(url_for("ui.dashboard"))
    return redirect(url_for("auth.login"))


@ui_bp.route("/dashboard")
@login_required
def dashboard():
    """Main application dashboard — requires login."""
    return render_template("index.html", user=current_user)
