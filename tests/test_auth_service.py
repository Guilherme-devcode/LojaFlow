"""Tests for authentication service."""
import os
import tempfile
import pytest

_tmpdir = tempfile.mkdtemp()
os.environ["LOJAFLOW_DATA"] = _tmpdir

from app.database import init_db
from app.services.auth_service import verify_password, get_user_by_username


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    yield


class TestVerifyPassword:
    def test_correct_credentials(self):
        user = verify_password("admin", "admin123")
        assert user is not None
        assert user.username == "admin"

    def test_wrong_password(self):
        user = verify_password("admin", "wrongpassword")
        assert user is None

    def test_nonexistent_user(self):
        user = verify_password("ghost", "password")
        assert user is None

    def test_empty_password(self):
        user = verify_password("admin", "")
        assert user is None


class TestGetUserByUsername:
    def test_existing_user(self):
        user = get_user_by_username("admin")
        assert user is not None
        assert user.role == "admin"
        assert user.active is True

    def test_nonexistent_user(self):
        user = get_user_by_username("nobody")
        assert user is None
