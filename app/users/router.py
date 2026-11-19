"""HTTP routes for User and Access (FR-01): validate input, call a service, return a schema."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.deps import CurrentUser, get_current_user, require_role
from app.core.enums import Role
from app.users.repository import UserRepository
from app.users.schemas import LoginRequest, TokenResponse, UserOut
from app.users.service import AuthService, UserService

# No prefix: this module serves both /auth/... and /users/... paths.
router = APIRouter(tags=["users"])


def get_user_repository(session: Annotated[Session, Depends(get_session)]) -> UserRepository:
    """Build the repository on the request's session."""
    return UserRepository(session)


def get_auth_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> AuthService:
    """Inject the repository into AuthService."""
    return AuthService(users)


def get_user_service(
    users: Annotated[UserRepository, Depends(get_user_repository)],
) -> UserService:
    """Inject the repository into UserService."""
    return UserService(users)


@router.post("/auth/login")
def login(
    body: LoginRequest, service: Annotated[AuthService, Depends(get_auth_service)]
) -> TokenResponse:
    """Exchange email and password for a bearer token."""
    return TokenResponse(access_token=service.login(body.email, body.password))


@router.get("/users/me")
def read_me(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserOut:
    """Return the caller's own profile."""
    return UserOut.model_validate(service.get_profile(user.id))


@router.get("/users", dependencies=[Depends(require_role(Role.ADMIN))])
def list_users(service: Annotated[UserService, Depends(get_user_service)]) -> list[UserOut]:
    """Return every user. Administrators only."""
    return [UserOut.model_validate(user) for user in service.list_users()]
