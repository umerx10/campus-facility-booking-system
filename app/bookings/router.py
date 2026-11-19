"""HTTP routes for Booking and Scheduling (FR-03, FR-04, FR-05, FR-07, FR-09).

Routes validate input, call BookingService and return schemas. get_booking_service is the one place
where the real collaborators are wired: the repository and the facility lookup share the request's
session, so the checks and the write are one BEGIN IMMEDIATE transaction.
"""

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.approvals.policies import policy_for
from app.bookings.publisher import booking_events
from app.bookings.repository import BookingRepository
from app.bookings.schemas import BookingHistoryOut, BookingOut, BookingRequest
from app.bookings.service import BookingService
from app.core.db import get_session
from app.core.deps import CurrentUser, get_current_user
from app.facilities.lookup import SqlFacilityLookup

router = APIRouter(prefix="/bookings", tags=["bookings"])


def utc_now() -> datetime:
    """Current time as naive UTC, the format every CFBS datetime column stores."""
    return datetime.now(UTC).replace(tzinfo=None)


def get_booking_service(session: Annotated[Session, Depends(get_session)]) -> BookingService:
    """Build the service with its real collaborators on the request's session."""
    return BookingService(
        repository=BookingRepository(session),
        facilities=SqlFacilityLookup(session),
        policy_for=policy_for,
        publisher=booking_events,
        now=utc_now,
    )


ServiceDep = Annotated[BookingService, Depends(get_booking_service)]
UserDep = Annotated[CurrentUser, Depends(get_current_user)]


@router.post("", status_code=status.HTTP_201_CREATED)
def request_booking(body: BookingRequest, user: UserDep, service: ServiceDep) -> BookingOut:
    """Request a facility; CONFIRMED at once, or PENDING for a restricted facility."""
    booking = service.request_booking(user, body.facility_id, body.start_at, body.end_at)
    return BookingOut.model_validate(booking)


@router.get("/me")
def my_bookings(user: UserDep, service: ServiceDep) -> list[BookingOut]:
    """Return the caller's bookings (FR-09)."""
    return [BookingOut.model_validate(b) for b in service.list_for_user(user.id)]


@router.get("/schedule", dependencies=[Depends(get_current_user)])
def schedule(
    facility_id: int,
    day: Annotated[date, Query(alias="date")],
    service: ServiceDep,
) -> list[BookingOut]:
    """Return the facility's CONFIRMED bookings on one day (FR-03, booking half)."""
    return [BookingOut.model_validate(b) for b in service.schedule(facility_id, day)]


@router.get("/{booking_id}/history")
def booking_history(
    booking_id: int, user: UserDep, service: ServiceDep
) -> list[BookingHistoryOut]:
    """Return the booking's status changes, oldest first; owner or administrator only."""
    return [BookingHistoryOut.model_validate(h) for h in service.history(booking_id, user)]


@router.post("/{booking_id}/cancel")
def cancel_booking(booking_id: int, user: UserDep, service: ServiceDep) -> BookingOut:
    """Cancel one of the caller's bookings (an administrator may cancel any)."""
    return BookingOut.model_validate(service.cancel(booking_id, user))
