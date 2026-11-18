"""API tests for login, the Bearer-token current user, and the admin-only user list (FR-01, QR-04).

These tests do NOT use the as_user fixture: they prove the real token path end to end.
"""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy.orm import Session

from app.core.enums import Role
from app.users.models import User
from app.users.security import create_access_token, decode_access_token, hash_password

PASSWORD = "correct-horse"


@pytest.fixture(scope="module")
def password_hash() -> str:
    """Hashed once per module: each hash costs 600000 PBKDF2 iterations."""
    return hash_password(PASSWORD)


@pytest.fixture
def users(db_session: Session, password_hash: str) -> dict[str, User]:
    student = User(
        name="Student One", email="student@example.com", role=Role.STUDENT,
        password_hash=password_hash,
    )
    admin = User(
        name="Admin One", email="admin@example.com", role=Role.ADMIN,
        password_hash=password_hash,
    )
    db_session.add_all([student, admin])
    db_session.commit()
    return {"student": student, "admin": admin}


def _login(client: TestClient, email: str, password: str) -> Response:
    return client.post("/auth/login", json={"email": email, "password": password})


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------- POST /auth/login ----------


def test_login_with_valid_credentials_returns_a_bearer_token(
    client: TestClient, users: dict[str, User]
) -> None:
    response = _login(client, "student@example.com", PASSWORD)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert decode_access_token(body["access_token"]).user_id == users["student"].id


@pytest.mark.usefixtures("users")
def test_wrong_password_and_unknown_email_get_the_same_401(client: TestClient) -> None:
    wrong_password = _login(client, "student@example.com", "not-the-password")
    unknown_email = _login(client, "nobody@example.com", PASSWORD)

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json()["detail"] == unknown_email.json()["detail"]


@pytest.mark.parametrize(
    ("email", "password"),
    [("", PASSWORD), ("student@example.com", ""), ("not-an-email", PASSWORD)],
)
def test_login_with_empty_or_malformed_input_returns_422(
    client: TestClient, email: str, password: str
) -> None:
    assert _login(client, email, password).status_code == 422


# ---------- GET /users/me ----------


def test_me_returns_the_profile_without_the_password_hash(
    client: TestClient, users: dict[str, User]
) -> None:
    token = _login(client, "student@example.com", PASSWORD).json()["access_token"]

    response = client.get("/users/me", headers=_bearer(token))

    assert response.status_code == 200
    assert response.json() == {
        "id": users["student"].id,
        "name": "Student One",
        "email": "student@example.com",
        "role": "STUDENT",
    }


def test_me_with_a_tampered_token_returns_401(
    client: TestClient, users: dict[str, User]
) -> None:
    token = create_access_token(user_id=users["student"].id, role="STUDENT")
    header, payload, signature = token.split(".")
    changed = ("A" if signature[0] != "A" else "B") + signature[1:]

    response = client.get("/users/me", headers=_bearer(f"{header}.{payload}.{changed}"))

    assert response.status_code == 401
    assert response.json()["error"] == "AuthenticationFailed"


def test_me_with_an_expired_token_returns_401(
    client: TestClient, users: dict[str, User]
) -> None:
    token = create_access_token(
        user_id=users["student"].id, role="STUDENT", expires_in=timedelta(seconds=-1)
    )

    response = client.get("/users/me", headers=_bearer(token))

    assert response.status_code == 401
    assert response.json()["error"] == "AuthenticationFailed"


def test_me_without_an_authorization_header_returns_401(client: TestClient) -> None:
    response = client.get("/users/me")

    assert response.status_code == 401
    assert response.json()["error"] == "AuthenticationFailed"


def test_me_for_a_user_that_no_longer_exists_returns_404(client: TestClient) -> None:
    token = create_access_token(user_id=999, role="STUDENT")

    response = client.get("/users/me", headers=_bearer(token))

    assert response.status_code == 404
    assert response.json()["error"] == "NotFound"


# ---------- GET /users (admin only) ----------


def test_list_users_is_forbidden_for_a_student(
    client: TestClient, users: dict[str, User]
) -> None:
    token = create_access_token(user_id=users["student"].id, role="STUDENT")

    response = client.get("/users", headers=_bearer(token))

    assert response.status_code == 403
    assert response.json()["error"] == "UnauthorizedOperation"


def test_list_users_returns_all_users_to_an_admin(
    client: TestClient, users: dict[str, User]
) -> None:
    token = create_access_token(user_id=users["admin"].id, role="ADMIN")

    response = client.get("/users", headers=_bearer(token))

    assert response.status_code == 200
    listed = response.json()
    assert {user["email"] for user in listed} == {"student@example.com", "admin@example.com"}
    assert all("password_hash" not in user for user in listed)
