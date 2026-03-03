"""Application factory."""
import logging
import os

from flask import Flask
from dotenv import load_dotenv

from .config import config
from .core.extensions import db, login_manager, bcrypt

log = logging.getLogger(__name__)


def create_app(config_name: str = None) -> Flask:
    """Create and configure the Flask application.

    Usage:
        Local:   flask --app src.wsgi:app run
        Testing: create_app("development")
        Prod:    gunicorn src.wsgi:app
    """
    load_dotenv()  # no-op if .env is absent (e.g. ECS where vars are injected)

    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
    )
    app.config.from_object(config[config_name])

    _configure_logging(app)
    _init_extensions(app)
    _ensure_directories(app)
    _create_tables(app)

    from .routes import register_blueprints
    register_blueprints(app)

    log.info("Rivet app started [env=%s]", config_name)
    return app


# ── helpers ───────────────────────────────────────────────────────────────────

def _configure_logging(app: Flask) -> None:
    level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    if not app.config.get("DEBUG"):
        logging.getLogger("werkzeug").setLevel(logging.WARNING)


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"           # type: ignore[assignment]
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))


def _create_tables(app: Flask) -> None:
    with app.app_context():
        from .models import user  # noqa: F401 — registers model with SQLAlchemy
        try:
            db.create_all()
            log.debug("Database tables verified / created.")
        except Exception as e:
            # Tables may already exist (race condition with multiple workers)
            # or database may be read-only. Log and continue.
            log.warning(f"Table creation skipped: {e}")


def _ensure_directories(app: Flask) -> None:
    """Create required directories for uploads and database."""
    # Create upload folder
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    
    # Create database directory if using SQLite
    db_url = app.config["SQLALCHEMY_DATABASE_URI"]
    if db_url.startswith("sqlite:///"):
        # Extract path from sqlite:///path/to/db.db or sqlite:///C:/path/to/db.db
        db_path = db_url.replace("sqlite:///", "", 1)
        # Convert forward slashes back to OS-specific separators
        db_path = db_path.replace("/", os.sep)
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            log.debug("Database directory ensured: %s", db_dir)
