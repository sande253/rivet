"""User database model."""
from datetime import datetime

from flask_login import UserMixin

from ..core.extensions import db


class User(UserMixin, db.Model):
    """Application user.

    Passwords are never stored in plain text — only bcrypt hashes.
    """
    __tablename__ = "users"

    id: int = db.Column(db.Integer, primary_key=True)
    email: str = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash: str = db.Column(db.String(255), nullable=False)
    created_at: datetime = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )
    last_login: datetime = db.Column(db.DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r}>"
