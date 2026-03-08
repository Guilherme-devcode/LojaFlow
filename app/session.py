"""Application session — tracks the currently logged-in user."""
from __future__ import annotations

from app.models.user import User


class Session:
    """Singleton-style session store. Use class attributes directly."""
    current_user: User | None = None

    @classmethod
    def login(cls, user: User) -> None:
        cls.current_user = user

    @classmethod
    def logout(cls) -> None:
        cls.current_user = None

    @classmethod
    def is_admin(cls) -> bool:
        return cls.current_user is not None and cls.current_user.role == "admin"

    @classmethod
    def is_logged_in(cls) -> bool:
        return cls.current_user is not None
