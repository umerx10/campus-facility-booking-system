
"""Administrator approval API for restricted bookings (FR-08).

Routes enforce administrator authorization and delegate booking
operations to ApprovalService. The Booking module owns database
transactions, conflict detection, and status transitions.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.approvals.service import ApprovalService
from app.bookings.router import get_booking_service
from app.bookings.schemas import BookingOut
from app.bookings.service import BookingService
from app.core.deps import CurrentUser, require_role
from app.core.enums import Role


router = APIRouter(prefix="/approvals", tags=["approvals"])

AdminDep = Annotated[
    CurrentUser,
    Depends(require_role(Role.ADMIN)),
]

BookingDep = Annotated[
    BookingService,
    Depends(get_booking_service),
]


@router.get("/pending", response_model=list[BookingOut])
def list_pending(
    actor: AdminDep,
    booking_service: BookingDep,
) -> list[BookingOut]:
    """List pending bookings for administrators."""
    service = ApprovalService(booking_service)

    return [
        BookingOut.model_validate(booking)
        for booking in service.list_pending(actor)
    ]


@router.post("/{booking_id}/approve", response_model=BookingOut)
def approve_booking(
    booking_id: int,
    actor: AdminDep,
    booking_service: BookingDep,
) -> BookingOut:
    """Approve a pending booking after administrator authorization."""
    service = ApprovalService(booking_service)
    booking = service.approve(booking_id, actor)

    return BookingOut.model_validate(booking)


@router.post("/{booking_id}/reject", response_model=BookingOut)
def reject_booking(
    booking_id: int,
    actor: AdminDep,
    booking_service: BookingDep,
) -> BookingOut:
    """Reject a pending booking after administrator authorization."""
    service = ApprovalService(booking_service)
    booking = service.reject(booking_id, actor)

    return BookingOut.model_validate(booking)
