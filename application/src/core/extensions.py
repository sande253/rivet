"""Flask extension singletons.

Initialised here without an app so that models can import them freely
without circular imports. The app factory calls .init_app(app) on each.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db: SQLAlchemy = SQLAlchemy()
login_manager: LoginManager = LoginManager()
bcrypt: Bcrypt = Bcrypt()
limiter: Limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)
