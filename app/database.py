"""Database engine, session factory, and initialization."""
import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def get_db_path() -> Path:
    """Return the path to the SQLite database file."""
    data_dir = Path(os.getenv("LOJAFLOW_DATA", Path.home() / ".lojaflow"))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "lojaflow.db"


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        db_url = f"sqlite:///{get_db_path()}"
        _engine = create_engine(db_url, connect_args={"check_same_thread": False})
    return _engine


def init_db():
    """Create all tables if they don't exist."""
    from app.models import product, sale, customer, user  # noqa: F401 — register models
    Base.metadata.create_all(bind=get_engine())
    _seed_default_user()


def _seed_default_user():
    """Create a default admin user if none exists."""
    from app.models.user import User
    import hashlib

    with get_session() as session:
        if not session.query(User).first():
            admin = User(
                name="Administrador",
                username="admin",
                password_hash=hashlib.sha256(b"admin123").hexdigest(),
                role="admin",
                active=True,
            )
            session.add(admin)
            session.commit()


@contextmanager
def get_session():
    """Provide a transactional database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    session: Session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
