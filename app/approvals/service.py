
"""Approval workflow service for restricted facility bookings (FR-08).

Uses dependency inversion: ApprovalService depends on the
PendingBookingActions Protocol rather than a concrete BookingService.
"""

from typing import Protocol

from app.bookings.models import Booking
from app.core.deps import CurrentUser
from app.core.enums import Role
from app.core.exceptions import UnauthorizedOperation


class PendingBookingActions(Protocol):
    """Operations required from the booking service."""

    def confirm_pending(
        self, booking_id: int, actor: CurrentUser
    ) -> Booking:
        """Confirm a pending booking."""

    def reject_pending(
        self, booking_id: int, actor: CurrentUser
    ) -> Booking:
        """Reject a pending booking."""

    def list_pending(self) -> list[Booking]:
        """Return all pending bookings."""


class ApprovalService:
    """Coordinate approval decisions for restricted bookings."""

    def __init__(self, booking_actions: PendingBookingActions) -> None:
        """Receive booking operations through an abstract interface."""
        self._booking_actions = booking_actions

    @staticmethod
    def _require_admin(actor: CurrentUser) -> None:
        """Reject approval operations performed by non-admin users."""
        if actor.role != Role.ADMIN:
            raise UnauthorizedOperation(
                "Only administrators can manage booking approvals"
            )

    def approve(self, booking_id: int, actor: CurrentUser) -> Booking:
        """Approve a pending booking using the booking service."""
        self._require_admin(actor)
        return self._booking_actions.confirm_pending(booking_id, actor)

    def reject(self, booking_id: int, actor: CurrentUser) -> Booking:
        """Reject a pending booking using the booking service."""
        self._require_admin(actor)
        return self._booking_actions.reject_pending(booking_id, actor)

    def list_pending(self, actor: CurrentUser) -> list[Booking]:
        """List pending bookings for an administrator."""
        self._require_admin(actor)
        return self._booking_actions.list_pending()
