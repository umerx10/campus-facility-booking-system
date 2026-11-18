"""Business logic for User and Access (FR-01).

Services receive their repository through the constructor and depend only on the small Protocols
below (Dependency Inversion, Interface Segregation), so unit tests pass fakes instead of a database.
"""

import logging
import secrets
from functools import cache
from typing import Protocol

from app.core.exceptions import AuthenticationFailed, NotFound
from app.users.models import User
from app.users.security import create_access_token, hash_password, verify_password

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS = "Invalid email or password"


class UserByEmail(Protocol):  # pylint: disable=too-few-public-methods  # one method by design (ISP)
    """What login needs from storage."""

    def get_by_email(self, email: str) -> User | None:
        """Return the user with this email, or None."""


class UserReader(Protocol):
    """What profile and listing need from storage."""

    def get_by_id(self, user_id: int) -> User | None:
        """Return the user with this id, or None."""

    def list_all(self) -> list[User]:
        """Return every user."""


@cache
def _dummy_hash() -> str:
    """A hash of a random password, made once, used when the email is unknown (see AuthService)."""
    return hash_password(secrets.token_urlsafe(16))


class AuthService:  # pylint: disable=too-few-public-methods  # login only, by design (SRP)
    """Checks credentials and issues access tokens.

    Every failure raises the same AuthenticationFailed message, so a caller cannot tell an unknown
    email from a wrong password. For an unknown email the password is still checked against a dummy
    hash, so both failures take about the same time and timing does not reveal which emails exist.
    Failures are logged at INFO with the email only; the password is never logged.
    """

    def __init__(self, users: UserByEmail) -> None:
        self._users = users

    def login(self, email: str, password: str) -> str:
        """Return an access token for valid credentials, otherwise raise AuthenticationFailed."""
        user = self._users.get_by_email(email)
        stored_hash = user.password_hash if user is not None else _dummy_hash()
        password_ok = verify_password(password, stored_hash)
        if user is None or not password_ok:
            logger.info("Failed login for email %s", email)
            raise AuthenticationFailed(INVALID_CREDENTIALS)
        return create_access_token(user_id=user.id, role=user.role)


class UserService:
    """Read-only user queries for the profile and the admin user list."""

    def __init__(self, users: UserReader) -> None:
        self._users = users

    def get_profile(self, user_id: int) -> User:
        """Return the user, or raise NotFound (for example, a valid token for a deleted user)."""
        user = self._users.get_by_id(user_id)
        if user is None:
            raise NotFound(f"User {user_id} not found")
        return user

    def list_users(self) -> list[User]:
        """Return every user."""
        return self._users.list_all()
