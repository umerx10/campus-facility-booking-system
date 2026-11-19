"""Narrow interfaces between modules (Interface Segregation, Dependency Inversion).

Services depend on these Protocols, not on another module's concrete classes. Module owners
provide the implementations (for example `BookingEventPublisher` implements `EventPublisher`;
`StudentPolicy` and `FacultyPolicy` implement `BookingPolicy`), and unit tests pass small fakes.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.core.deps import CurrentUser
from app.core.events import BookingEvent


@dataclass(frozen=True)
class FacilityInfo:
    """The facility facts other modules need, without exposing the Facility model."""

    id: int
    capacity: int
    requires_approval: bool
    active: bool


class FacilityLookup(Protocol):
    """Read-only facility queries used by Booking and Approval."""

    def get_facility(self, facility_id: int) -> FacilityInfo:
        """Return the facility or raise NotFound."""

    def is_within_hours(self, facility_id: int, start: datetime, end: datetime) -> bool:
        """True if [start, end) lies inside the facility's operating hours."""

    def overlaps_block(self, facility_id: int, start: datetime, end: datetime) -> bool:
        """True if [start, end) overlaps a maintenance block."""


class BookingPolicy(Protocol):  # pylint: disable=too-few-public-methods  # one method by design (ISP)
    """Role-specific booking rules (Strategy pattern, FR-06)."""

    def validate(
        self, user: CurrentUser, facility: FacilityInfo, start: datetime, end: datetime
    ) -> None:
        """Return if the request is allowed; otherwise raise PolicyViolation."""


class EventPublisher(Protocol):
    """Delivers booking events to subscribers (Observer pattern)."""

    def subscribe(
        self, event_type: type[BookingEvent], handler: Callable[[BookingEvent], None]
    ) -> None:
        """Call `handler` for every published event of `event_type`."""

    def publish(self, event: BookingEvent) -> None:
        """Send `event` to the handlers subscribed to its type."""
