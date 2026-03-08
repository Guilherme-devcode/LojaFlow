"""User management service."""
from __future__ import annotations

import hashlib

from app.database import get_session
from app.models.user import User


def list_users() -> list[User]:
    with get_session() as s:
        return s.query(User).order_by(User.name).all()


def get_user_by_id(user_id: int) -> User | None:
    with get_session() as s:
        return s.get(User, user_id)


def create_user(name: str, username: str, password: str, role: str = "cashier") -> User:
    with get_session() as s:
        existing = s.query(User).filter_by(username=username).first()
        if existing:
            raise ValueError(f"Usuário '{username}' já existe")
        user = User(
            name=name,
            username=username,
            password_hash=hashlib.sha256(password.encode()).hexdigest(),
            role=role,
            active=True,
        )
        s.add(user)
        s.flush()
        s.refresh(user)
        return user


def update_user(user_id: int, name: str, role: str, new_password: str | None = None) -> User:
    with get_session() as s:
        user = s.get(User, user_id)
        if not user:
            raise ValueError(f"Usuário #{user_id} não encontrado")
        user.name = name
        user.role = role
        if new_password:
            user.password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        s.flush()
        s.refresh(user)
        return user


def deactivate_user(user_id: int) -> None:
    with get_session() as s:
        user = s.get(User, user_id)
        if not user:
            raise ValueError(f"Usuário #{user_id} não encontrado")
        if user.username == "admin":
            raise ValueError("Não é possível desativar o usuário admin")
        user.active = False


def reactivate_user(user_id: int) -> None:
    with get_session() as s:
        user = s.get(User, user_id)
        if not user:
            raise ValueError(f"Usuário #{user_id} não encontrado")
        user.active = True
