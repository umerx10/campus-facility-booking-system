
"""Unit tests for the approval workflow (FR-08)."""

from unittest.mock import Mock

import pytest

from app.approvals.service import ApprovalService
from app.core.deps import CurrentUser
from app.core.enums import Role
from app.core.exceptions import (
    BookingConflict,
    NotFound,
    UnauthorizedOperation,
)


ADMIN = CurrentUser(id=1, role=Role.ADMIN)
STUDENT = CurrentUser(id=2, role=Role.STUDENT)
FACULTY = CurrentUser(id=3, role=Role.FACULTY)


@pytest.fixture
def booking_actions() -> Mock:
    """Create fake booking operations without a database."""
    return Mock()


def test_admin_can_approve_booking(booking_actions: Mock) -> None:
    """Approval delegates to the booking service."""
    booking = object()
    booking_actions.confirm_pending.return_value = booking

    service = ApprovalService(booking_actions)
    result = service.approve(10, ADMIN)

    assert result is booking
    booking_actions.confirm_pending.assert_called_once_with(10, ADMIN)


def test_admin_can_reject_booking(booking_actions: Mock) -> None:
    """Rejection delegates to the booking service."""
    booking = object()
    booking_actions.reject_pending.return_value = booking

    service = ApprovalService(booking_actions)
    result = service.reject(10, ADMIN)

    assert result is booking
    booking_actions.reject_pending.assert_called_once_with(10, ADMIN)


def test_admin_can_list_pending(booking_actions: Mock) -> None:
    """Pending bookings are returned from the booking service."""
    bookings = [object(), object()]
    booking_actions.list_pending.return_value = bookings

    service = ApprovalService(booking_actions)
    result = service.list_pending(ADMIN)

    assert result is bookings
    booking_actions.list_pending.assert_called_once_with()


@pytest.mark.parametrize("actor", [STUDENT, FACULTY])
def test_non_admin_cannot_approve(
    booking_actions: Mock, actor: CurrentUser
) -> None:
    """Only admins may approve bookings."""
    service = ApprovalService(booking_actions)

    with pytest.raises(UnauthorizedOperation):
        service.approve(10, actor)

    booking_actions.confirm_pending.assert_not_called()


@pytest.mark.parametrize("actor", [STUDENT, FACULTY])
def test_non_admin_cannot_reject(
    booking_actions: Mock, actor: CurrentUser
) -> None:
    """Only admins may reject bookings."""
    service = ApprovalService(booking_actions)

    with pytest.raises(UnauthorizedOperation):
        service.reject(10, actor)

    booking_actions.reject_pending.assert_not_called()


@pytest.mark.parametrize("actor", [STUDENT, FACULTY])
def test_non_admin_cannot_list_pending(
    booking_actions: Mock, actor: CurrentUser
) -> None:
    """Only admins may view pending bookings."""
    service = ApprovalService(booking_actions)

    with pytest.raises(UnauthorizedOperation):
        service.list_pending(actor)

    booking_actions.list_pending.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [BookingConflict("Invalid state"), NotFound("Booking missing")],
)
def test_approve_propagates_domain_errors(
    booking_actions: Mock, error: Exception
) -> None:
    """Approval preserves domain errors from the booking service."""
    booking_actions.confirm_pending.side_effect = error
    service = ApprovalService(booking_actions)

    with pytest.raises(type(error)):
        service.approve(10, ADMIN)


@pytest.mark.parametrize(
    "error",
    [BookingConflict("Invalid state"), NotFound("Booking missing")],
)
def test_reject_propagates_domain_errors(
    booking_actions: Mock, error: Exception
) -> None:
    """Rejection preserves domain errors from the booking service."""
    booking_actions.reject_pending.side_effect = error
    service = ApprovalService(booking_actions)

    with pytest.raises(type(error)):
        service.reject(10, ADMIN)
