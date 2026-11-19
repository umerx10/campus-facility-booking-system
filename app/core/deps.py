"""FastAPI dependencies for identity and authorization.

`get_current_user` reads a Bearer token from the Authorization header (User and Access, FR-01). It
replaced the Phase 1 header stub with the same name, signature style and CurrentUser return type,
so no other module had to change. Tests that are not about authentication use the `as_user`
fixture instead of real tokens.

Tokens are stateless: the user is not reloaded from the database on each request, so a deleted or
demoted user keeps access until the token expires (60 minutes). This is accepted for this scope.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.enums import Role
from app.core.exceptions import AuthenticationFailed, UnauthorizedOperation
from app.users.security import TokenError, decode_access_token

# auto_error=False: a missing header reaches our code, so it becomes AuthenticationFailed (401)
# through the one DomainError handler, with the same JSON body as every other error.
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    """The authenticated caller: only what authorization decisions need."""

    id: int
    role: Role


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> CurrentUser:
    """Identify the caller from the Bearer token, or raise AuthenticationFailed."""
    if credentials is None:
        raise AuthenticationFailed("Missing bearer token")
    try:
        data = decode_access_token(credentials.credentials)
        role = Role(data.role)
    except (TokenError, ValueError) as exc:
        raise AuthenticationFailed("Invalid or expired access token") from exc
    return CurrentUser(id=data.user_id, role=role)


def require_role(*roles: Role) -> Callable[[CurrentUser], CurrentUser]:
    """Build a dependency that lets only the given roles through and returns the caller."""
    allowed = frozenset(roles)

    def check_role(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in allowed:
            names = ", ".join(sorted(role.value for role in allowed))
            raise UnauthorizedOperation(f"This action requires role: {names}")
        return user

    return check_role
