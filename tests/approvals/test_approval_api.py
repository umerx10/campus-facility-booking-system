
"""API tests for administrator approval operations (FR-08)."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.bookings.router import get_booking_service
from app.core.enums import BookingStatus, Role
from app.core.exceptions import BookingConflict
from app.main import app


def fake_booking(status: BookingStatus) -> SimpleNamespace:
    """Return a booking-shaped object for response serialization."""
    return SimpleNamespace(
        id=10,
        user_id=2,
        facility_id=3,
        start_at=datetime(2026, 11, 20, 10, 0),
        end_at=datetime(2026, 11, 20, 11, 0),
        status=status,
    )


@pytest.fixture
def booking_service(client: TestClient) -> Mock:
    """Replace the real BookingService with isolated fake actions."""
    service = Mock()
    app.dependency_overrides[get_booking_service] = lambda: service
    return service


def test_admin_lists_pending(
    client: TestClient, as_user, booking_service: Mock
) -> None:
    """Administrators can retrieve pending booking requests."""
    as_user(Role.ADMIN)
    booking_service.list_pending.return_value = [
        fake_booking(BookingStatus.PENDING)
    ]

    response = client.get("/approvals/pending")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["status"] == "PENDING"


def test_admin_approves(
    client: TestClient, as_user, booking_service: Mock
) -> None:
    """Administrators can confirm a pending booking."""
    actor = as_user(Role.ADMIN)
    booking_service.confirm_pending.return_value = fake_booking(
        BookingStatus.CONFIRMED
    )

    response = client.post("/approvals/10/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "CONFIRMED"
    booking_service.confirm_pending.assert_called_once_with(10, actor)


def test_admin_rejects(
    client: TestClient, as_user, booking_service: Mock
) -> None:
    """Administrators can reject a pending booking."""
    actor = as_user(Role.ADMIN)
    booking_service.reject_pending.return_value = fake_booking(
        BookingStatus.REJECTED
    )

    response = client.post("/approvals/10/reject")

    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"
    booking_service.reject_pending.assert_called_once_with(10, actor)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/approvals/pending"),
        ("POST", "/approvals/10/approve"),
        ("POST", "/approvals/10/reject"),
    ],
)
def test_student_forbidden(
    client: TestClient,
    as_user,
    booking_service: Mock,
    method: str,
    path: str,
) -> None:
    """Students cannot access approval endpoints."""
    as_user(Role.STUDENT)

    response = client.request(method, path)

    assert response.status_code == 403
    booking_service.confirm_pending.assert_not_called()
    booking_service.reject_pending.assert_not_called()
    booking_service.list_pending.assert_not_called()


def test_conflicting_approval_returns_409(
    client: TestClient, as_user, booking_service: Mock
) -> None:
    """Booking conflicts must produce HTTP 409."""
    as_user(Role.ADMIN)
    booking_service.confirm_pending.side_effect = BookingConflict(
        "Booking slot is already occupied"
    )

    response = client.post("/approvals/10/approve")

    assert response.status_code == 409
    assert response.json()["error"] == "BookingConflict"
