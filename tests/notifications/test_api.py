"""API tests for listing notifications and marking them read (FR-10)."""

from collections.abc import Callable
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.core.enums import Role
from app.notifications.models import Notification
from app.users.models import User


@pytest.fixture
def notes(db_session: Session) -> dict[str, Notification]:
    """Two notifications for user 1 (older, newer) and one for user 2."""
    db_session.add_all(
        [
            User(id=1, name="User One", email="one@example.com", role=Role.STUDENT,
                 password_hash="x"),
            User(id=2, name="User Two", email="two@example.com", role=Role.FACULTY,
                 password_hash="x"),
        ]
    )
    # Without ORM relationships SQLAlchemy does not order inserts by foreign key, so the users
    # are flushed first to exist before their notifications.
    db_session.flush()
    older = Notification(
        user_id=1, event_type="BOOKING_CONFIRMED", message="Booking #1 confirmed",
        created_at=datetime(2026, 11, 18, 9, 0),
    )
    newer = Notification(
        user_id=1, event_type="BOOKING_CANCELLED", message="Booking #2 cancelled",
        created_at=datetime(2026, 11, 18, 10, 0),
    )
    other = Notification(
        user_id=2, event_type="BOOKING_REJECTED", message="Booking #3 rejected",
        created_at=datetime(2026, 11, 18, 11, 0),
    )
    db_session.add_all([older, newer, other])
    db_session.commit()
    return {"older": older, "newer": newer, "other": other}


def test_list_returns_only_my_notifications_newest_first(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    notes: dict[str, Notification],
) -> None:
    as_user(Role.STUDENT, user_id=1)

    response = client.get("/notifications")

    assert response.status_code == 200
    body = response.json()
    assert [n["id"] for n in body] == [notes["newer"].id, notes["older"].id]
    assert body[0]["event_type"] == "BOOKING_CANCELLED"
    assert body[0]["message"] == "Booking #2 cancelled"
    assert body[0]["read_at"] is None


def test_mark_read_sets_read_at(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    notes: dict[str, Notification],
    db_session: Session,
) -> None:
    as_user(Role.STUDENT, user_id=1)

    response = client.patch(f"/notifications/{notes['older'].id}/read")

    assert response.status_code == 200
    assert response.json()["read_at"] is not None
    db_session.refresh(notes["older"])
    assert notes["older"].read_at is not None


def test_mark_read_on_another_users_notification_returns_404(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    notes: dict[str, Notification],
    db_session: Session,
) -> None:
    as_user(Role.STUDENT, user_id=1)

    response = client.patch(f"/notifications/{notes['other'].id}/read")

    assert response.status_code == 404
    assert response.json()["error"] == "NotFound"
    db_session.refresh(notes["other"])
    assert notes["other"].read_at is None


@pytest.mark.usefixtures("notes")
def test_mark_read_on_an_unknown_id_returns_404(
    client: TestClient, as_user: Callable[..., CurrentUser]
) -> None:
    as_user(Role.STUDENT, user_id=1)

    response = client.patch("/notifications/9999/read")

    assert response.status_code == 404
    assert response.json()["error"] == "NotFound"


def test_list_without_authentication_returns_401(client: TestClient) -> None:
    response = client.get("/notifications")

    assert response.status_code == 401
    assert response.json()["error"] == "AuthenticationFailed"
