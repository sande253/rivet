"""UI routes — public landing and protected dashboard."""
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

ui_bp = Blueprint("ui", __name__)


@ui_bp.route("/")
def index():
    """Root: redirect authenticated users to home, guests to login."""
    if current_user.is_authenticated:
        return redirect(url_for("ui.home"))
    return redirect(url_for("auth.login"))


@ui_bp.route("/dashboard")
@login_required
def dashboard():
    """Legacy route - redirect to home."""
    return redirect(url_for("ui.home"))


@ui_bp.route("/home")
@login_required
def home():
    """Home page."""
    return render_template("index.html", user=current_user, active_page="home")


@ui_bp.route("/analyze")
@login_required
def analyze():
    """Analyze page."""
    return render_template("index.html", user=current_user, active_page="analyze")


@ui_bp.route("/market")
@login_required
def market():
    """Market intelligence page."""
    return render_template("index.html", user=current_user, active_page="market")


@ui_bp.route("/how")
@login_required
def how():
    """How it works page."""
    return render_template("index.html", user=current_user, active_page="how")


@ui_bp.route("/account")
@login_required
def account():
    """Account management page."""
    return render_template("index.html", user=current_user, active_page="account")


@ui_bp.route("/analyses")
@login_required
def analyses():
    """My analyses page."""
    return render_template("index.html", user=current_user, active_page="analyses")
