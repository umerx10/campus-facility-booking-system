"""Request and response bodies for User and Access. Input is validated here, before any service."""

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import Role

# Deliberately simple (something@something.something); full RFC checking would need another package.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class LoginRequest(BaseModel):
    """Login form. Empty fields or a malformed email are rejected with 422 by FastAPI."""

    email: str = Field(min_length=1, max_length=255, pattern=EMAIL_PATTERN)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """A bearer token for the Authorization header."""

    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    """Public view of a user. The password hash is not a field, so it can never be returned."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: Role
