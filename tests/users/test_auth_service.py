"""Unit tests for AuthService.login, with a fake repository instead of the database."""

import logging

import pytest

from app.core.enums import Role
from app.core.exceptions import AuthenticationFailed
from app.users.models import User
from app.users.security import TokenData, decode_access_token, hash_password
from app.users.service import AuthService

PASSWORD = "correct-horse"


class FakeUserRepository:
    """Holds users in a dict keyed by email; only what login needs."""

    def __init__(self, users: list[User]) -> None:
        self._by_email = {user.email: user for user in users}

    def get_by_email(self, email: str) -> User | None:
        """Return the user with this email, or None."""
        return self._by_email.get(email)


@pytest.fixture(scope="module")
def password_hash() -> str:
    """Hashed once per module: each hash costs 600000 PBKDF2 iterations."""
    return hash_password(PASSWORD)


@pytest.fixture
def service(password_hash: str) -> AuthService:
    faculty = User(
        id=3,
        name="Faculty Member",
        email="faculty@example.com",
        role=Role.FACULTY,
        password_hash=password_hash,
    )
    return AuthService(FakeUserRepository([faculty]))


def test_login_with_correct_password_returns_token_for_that_user(service: AuthService) -> None:
    token = service.login("faculty@example.com", PASSWORD)

    assert decode_access_token(token) == TokenData(user_id=3, role="FACULTY")


def test_wrong_password_and_unknown_email_fail_with_the_same_message(service: AuthService) -> None:
    with pytest.raises(AuthenticationFailed) as wrong_password:
        service.login("faculty@example.com", "not-the-password")
    with pytest.raises(AuthenticationFailed) as unknown_email:
        service.login("nobody@example.com", PASSWORD)

    assert str(wrong_password.value) == str(unknown_email.value)
    assert str(wrong_password.value) == "Invalid email or password"


def test_failed_login_is_logged_with_email_but_never_the_password(
    service: AuthService, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.INFO), pytest.raises(AuthenticationFailed):
        service.login("faculty@example.com", "guess-12345")

    assert any(
        r.levelno == logging.INFO and "faculty@example.com" in r.getMessage()
        for r in caplog.records
    )
    assert "guess-12345" not in caplog.text
