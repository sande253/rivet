"""Page routes for the application."""
from flask import Blueprint, render_template
from flask_login import login_required, current_user

pages_bp = Blueprint('pages', __name__)


@pages_bp.route('/')
@pages_bp.route('/home')
def home():
    """Home page."""
    if current_user.is_authenticated:
        return render_template('home.html', user=current_user)
    # Redirect to login if not authenticated
    from flask import redirect, url_for
    return redirect(url_for('auth.login'))


@pages_bp.route('/analyze')
@login_required
def analyze():
    """Analyze page."""
    return render_template('analyze.html', user=current_user)


@pages_bp.route('/market')
def market():
    """Market intelligence page."""
    if current_user.is_authenticated:
        return render_template('market.html', user=current_user)
    from flask import redirect, url_for
    return redirect(url_for('auth.login'))


@pages_bp.route('/how')
def how():
    """How it works page."""
    if current_user.is_authenticated:
        return render_template('how.html', user=current_user)
    from flask import redirect, url_for
    return redirect(url_for('auth.login'))


@pages_bp.route('/account')
@login_required
def account():
    """Account page."""
    return render_template('account.html', user=current_user)


@pages_bp.route('/analyses')
@login_required
def analyses():
    """My analyses page."""
    return render_template('analyses.html', user=current_user)
