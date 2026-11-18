"""Small fakes for unit testing BookingService without a database (Dependency Inversion).

A shared `log` list records the order of store commits and publisher calls, so tests can prove
that events are published only after the commit.
"""

from collections.abc import Callable
from datetime import date, datetime

from app.core.deps import CurrentUser
from app.core.enums import BookingStatus, Role
from app.core.events import BookingEvent
from app.core.exceptions import NotFound, PolicyViolation
from app.core.interfaces import BookingPolicy, FacilityInfo
from app.bookings.models import Booking, BookingHistory


class FakeStore:
    """In-memory BookingStore."""

    def __init__(self, log: list[str]) -> None:
        self.bookings: dict[int, Booking] = {}
        self.history: list[BookingHistory] = []
        self.log = log
        self._next_id = 1

    def add(
        self,
        user_id: int,
        facility_id: int,
        start: datetime,
        end: datetime,
        status: BookingStatus,
    ) -> Booking:
        booking = Booking(
            id=self._next_id,
            user_id=user_id,
            facility_id=facility_id,
            start_at=start,
            end_at=end,
            status=status,
        )
        self.bookings[booking.id] = booking
        self._next_id += 1
        return booking

    def get(self, booking_id: int) -> Booking | None:
        return self.bookings.get(booking_id)

    def find_confirmed_overlaps(
        self, facility_id: int, start: datetime, end: datetime, exclude_id: int | None = None
    ) -> list[Booking]:
        return [
            b
            for b in self.bookings.values()
            if b.facility_id == facility_id
            and b.status == BookingStatus.CONFIRMED
            and b.start_at < end
            and start < b.end_at
            and b.id != exclude_id
        ]

    def add_history(
        self,
        booking_id: int,
        old_status: BookingStatus | None,
        new_status: BookingStatus,
        changed_at: datetime,
        actor_id: int,
    ) -> None:
        self.history.append(
            BookingHistory(
                booking_id=booking_id,
                old_status=old_status,
                new_status=new_status,
                changed_at=changed_at,
                actor_id=actor_id,
            )
        )

    def history_for(self, booking_id: int) -> list[BookingHistory]:
        return [h for h in self.history if h.booking_id == booking_id]

    def list_for_user(self, user_id: int) -> list[Booking]:
        return [b for b in self.bookings.values() if b.user_id == user_id]

    def list_pending(self) -> list[Booking]:
        return [b for b in self.bookings.values() if b.status == BookingStatus.PENDING]

    def confirmed_on(self, facility_id: int, day: date) -> list[Booking]:
        return [
            b
            for b in self.bookings.values()
            if b.facility_id == facility_id
            and b.status == BookingStatus.CONFIRMED
            and b.start_at.date() == day
        ]

    def commit(self) -> None:
        self.log.append("commit")


class FakeLookup:
    """FacilityLookup with fixed answers."""

    def __init__(self, facilities: list[FacilityInfo]) -> None:
        self.facilities = {f.id: f for f in facilities}
        self.open = True
        self.blocked = False

    def get_facility(self, facility_id: int) -> FacilityInfo:
        if facility_id not in self.facilities:
            raise NotFound(f"Facility {facility_id} not found")
        return self.facilities[facility_id]

    def is_within_hours(self, facility_id: int, start: datetime, end: datetime) -> bool:
        return self.open

    def overlaps_block(self, facility_id: int, start: datetime, end: datetime) -> bool:
        return self.blocked


class FakePolicy:
    """BookingPolicy that records its calls and raises PolicyViolation when told to."""

    def __init__(self) -> None:
        self.calls: list[tuple[CurrentUser, FacilityInfo, datetime, datetime]] = []
        self.violation: str | None = None

    def validate(
        self, user: CurrentUser, facility: FacilityInfo, start: datetime, end: datetime
    ) -> None:
        self.calls.append((user, facility, start, end))
        if self.violation is not None:
            raise PolicyViolation(self.violation)


class RecordingPolicyFor:
    """policy_for replacement: remembers which roles were asked for, returns one FakePolicy."""

    def __init__(self, policy: FakePolicy) -> None:
        self.policy = policy
        self.roles: list[Role] = []

    def __call__(self, role: Role) -> BookingPolicy:
        self.roles.append(role)
        return self.policy


class FakePublisher:
    """EventPublisher that records published events."""

    def __init__(self, log: list[str]) -> None:
        self.events: list[BookingEvent] = []
        self.log = log

    def subscribe(
        self, event_type: type[BookingEvent], handler: Callable[[BookingEvent], None]
    ) -> None:
        raise AssertionError("BookingService must not subscribe")

    def publish(self, event: BookingEvent) -> None:
        self.events.append(event)
        self.log.append(f"publish:{type(event).__name__}")
