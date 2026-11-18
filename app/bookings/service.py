"""Business logic for booking requests (FR-04, FR-05, FR-06, FR-08, FR-09).

BookingService receives everything it depends on through its constructor, typed with Protocols
(Dependency Inversion): its own store, the facility lookup, the role policies (Strategy), the
event publisher (Observer) and a clock, so unit tests pass fakes and a fixed "now".

Rules agreed in the M2 team plan:
- A request for a restricted facility is stored as PENDING and does not reserve the slot.
- Every status change writes a history row in the same transaction as the change.
- Events are published only after the commit; creating a PENDING booking publishes nothing.
"""

from collections.abc import Callable
from datetime import date, datetime
from typing import Protocol

from app.bookings.models import Booking, BookingHistory
from app.core.deps import CurrentUser
from app.core.enums import BookingStatus, Role
from app.core.events import BookingConfirmed
from app.core.exceptions import BookingConflict, FacilityUnavailable, InvalidBookingTime
from app.core.interfaces import BookingPolicy, EventPublisher, FacilityInfo, FacilityLookup


class BookingStore(Protocol):
    """What the service needs from storage (implemented by BookingRepository)."""

    def add(
        self,
        user_id: int,
        facility_id: int,
        start: datetime,
        end: datetime,
        status: BookingStatus,
    ) -> Booking:
        """Stage a new booking and return it with its id."""

    def get(self, booking_id: int) -> Booking | None:
        """Return the booking or None."""

    def find_confirmed_overlaps(
        self, facility_id: int, start: datetime, end: datetime, exclude_id: int | None = None
    ) -> list[Booking]:
        """Return CONFIRMED bookings that overlap [start, end)."""

    def add_history(
        self,
        booking_id: int,
        old_status: BookingStatus | None,
        new_status: BookingStatus,
        changed_at: datetime,
        actor_id: int,
    ) -> None:
        """Stage one status-change row."""

    def history_for(self, booking_id: int) -> list[BookingHistory]:
        """Return the booking's status changes, oldest first."""

    def list_for_user(self, user_id: int) -> list[Booking]:
        """Return the user's bookings."""

    def list_pending(self) -> list[Booking]:
        """Return the PENDING bookings."""

    def confirmed_on(self, facility_id: int, day: date) -> list[Booking]:
        """Return the facility's CONFIRMED bookings on that day."""

    def commit(self) -> None:
        """Commit the current transaction."""


class BookingService:  # pylint: disable=too-few-public-methods  # step 4 adds cancel and approval methods
    """Creates bookings after checking the interval, the facility, the role policy and conflicts."""

    def __init__(  # pylint: disable=too-many-arguments  # five injected collaborators, by design (DIP)
        self,
        *,
        repository: BookingStore,
        facilities: FacilityLookup,
        policy_for: Callable[[Role], BookingPolicy],
        publisher: EventPublisher,
        now: Callable[[], datetime],
    ) -> None:
        self._store = repository
        self._facilities = facilities
        self._policy_for = policy_for
        self._publisher = publisher
        self._now = now

    def request_booking(
        self, user: CurrentUser, facility_id: int, start: datetime, end: datetime
    ) -> Booking:
        """Request [start, end) for the user and return the booking.

        Restricted facilities give a PENDING booking (no overlap check, nothing published); others
        give a CONFIRMED booking after the overlap check, then BookingConfirmed after the commit.
        """
        self._check_interval(start, end)
        facility = self._facilities.get_facility(facility_id)
        self._check_available(facility, start, end)
        self._policy_for(user.role).validate(user, facility, start, end)
        if facility.requires_approval:
            return self._create(user, facility_id, start, end, BookingStatus.PENDING)
        self._check_no_conflict(facility_id, start, end)
        booking = self._create(user, facility_id, start, end, BookingStatus.CONFIRMED)
        self._publisher.publish(
            BookingConfirmed(
                booking_id=booking.id,
                user_id=booking.user_id,
                facility_id=booking.facility_id,
                occurred_at=self._now(),
            )
        )
        return booking

    def _check_interval(self, start: datetime, end: datetime) -> None:
        """Raise InvalidBookingTime unless start < end and start is not in the past."""
        if end <= start:
            raise InvalidBookingTime("The booking must end after it starts")
        if start < self._now():
            raise InvalidBookingTime("The booking cannot start in the past")

    def _check_available(self, facility: FacilityInfo, start: datetime, end: datetime) -> None:
        """Raise FacilityUnavailable if the facility is inactive, closed or blocked then."""
        if not facility.active:
            raise FacilityUnavailable(f"Facility {facility.id} is not active")
        if not self._facilities.is_within_hours(facility.id, start, end):
            raise FacilityUnavailable(f"Facility {facility.id} is closed at that time")
        if self._facilities.overlaps_block(facility.id, start, end):
            raise FacilityUnavailable(f"Facility {facility.id} is blocked for maintenance")

    def _check_no_conflict(
        self, facility_id: int, start: datetime, end: datetime, exclude_id: int | None = None
    ) -> None:
        """Raise BookingConflict if [start, end) overlaps a CONFIRMED booking (FR-05)."""
        if self._store.find_confirmed_overlaps(facility_id, start, end, exclude_id):
            raise BookingConflict("The facility is already booked for an overlapping time")

    def _create(
        self,
        user: CurrentUser,
        facility_id: int,
        start: datetime,
        end: datetime,
        status: BookingStatus,
    ) -> Booking:
        """Store the booking and its first history row in one transaction, then commit."""
        booking = self._store.add(user.id, facility_id, start, end, status)
        self._store.add_history(booking.id, None, status, self._now(), user.id)
        self._store.commit()
        return booking
