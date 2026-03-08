"""Authentication service — password verification and user lookup."""
from __future__ import annotations

import hashlib

from app.database import get_session
from app.models.user import User


def get_user_by_username(username: str) -> User | None:
    with get_session() as s:
        return s.query(User).filter_by(username=username, active=True).first()


def verify_password(username: str, password: str) -> User | None:
    """Return the User if credentials are valid, else None."""
    user = get_user_by_username(username)
    if not user:
        return None
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    if user.password_hash == password_hash:
        return user
    return None
