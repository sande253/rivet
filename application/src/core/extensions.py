"""Flask extension singletons.

Initialised here without an app so that models can import them freely
without circular imports. The app factory calls .init_app(app) on each.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
db: SQLAlchemy = SQLAlchemy()
login_manager: LoginManager = LoginManager()
bcrypt: Bcrypt = Bcrypt()
