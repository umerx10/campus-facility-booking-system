"""FastAPI dependencies for identity and authorization.

`get_current_user` is a temporary stub that trusts the X-User-Id and X-User-Role headers. User and
Access replaces it with Bearer-token decoding under the same name, signature and return type, so no
other module has to change. Tests never rely on the stub: they use the `as_user` fixture.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header

from app.core.enums import Role
from app.core.exceptions import AuthenticationFailed, UnauthorizedOperation


@dataclass(frozen=True)
class CurrentUser:
    """The authenticated caller: only what authorization decisions need."""

    id: int
    role: Role


def get_current_user(
    x_user_id: Annotated[str | None, Header()] = None,
    x_user_role: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    """Identify the caller from headers (stub). Bad or missing headers: AuthenticationFailed."""
    if x_user_id is None or x_user_role is None:
        raise AuthenticationFailed("Missing X-User-Id or X-User-Role header")
    try:
        return CurrentUser(id=int(x_user_id), role=Role(x_user_role.upper()))
    except ValueError as exc:
        raise AuthenticationFailed("Invalid X-User-Id or X-User-Role header") from exc


def require_role(*roles: Role) -> Callable[[CurrentUser], CurrentUser]:
    """Build a dependency that lets only the given roles through and returns the caller."""
    allowed = frozenset(roles)

    def check_role(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in allowed:
            names = ", ".join(sorted(role.value for role in allowed))
            raise UnauthorizedOperation(f"This action requires role: {names}")
        return user

    return check_role
