"""In-app notice types and the NotificationFactory that builds them (Factory pattern, FR-10).

Each booking event type maps to one notice class. The notice class owns its own wording, the
factory owns the mapping, and the booking code only publishes events. Adding a notice type means
registering one more pair; no existing class changes (Open/Closed).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Self

from app.core.events import BookingCancelled, BookingConfirmed, BookingEvent, BookingRejected


class UnsupportedEventError(Exception):
    """No notice type is registered for this event type."""


@dataclass(frozen=True)
class Notice(ABC):
    """An in-app message for one user, ready to be stored as a notifications row."""

    user_id: int
    event_type: str
    message: str

    @classmethod
    @abstractmethod
    def from_event(cls, event: BookingEvent) -> Self:
        """Build this notice from the event that caused it."""


@dataclass(frozen=True)
class ConfirmationNotice(Notice):
    """Tells the user their booking is confirmed."""

    @classmethod
    def from_event(cls, event: BookingEvent) -> Self:
        return cls(
            user_id=event.user_id,
            event_type="BOOKING_CONFIRMED",
            message=(
                f"Your booking #{event.booking_id} for facility {event.facility_id} "
                "has been confirmed."
            ),
        )


@dataclass(frozen=True)
class RejectionNotice(Notice):
    """Tells the user an administrator rejected their booking request."""

    @classmethod
    def from_event(cls, event: BookingEvent) -> Self:
        return cls(
            user_id=event.user_id,
            event_type="BOOKING_REJECTED",
            message=(
                f"Your booking request #{event.booking_id} for facility {event.facility_id} "
                "was rejected."
            ),
        )


@dataclass(frozen=True)
class CancellationNotice(Notice):
    """Tells the user their booking was cancelled."""

    @classmethod
    def from_event(cls, event: BookingEvent) -> Self:
        return cls(
            user_id=event.user_id,
            event_type="BOOKING_CANCELLED",
            message=(
                f"Your booking #{event.booking_id} for facility {event.facility_id} "
                "has been cancelled."
            ),
        )


class NotificationFactory:
    """Builds the right Notice for a booking event, using a registry instead of conditionals.

    Why a factory (M1 section 6): construction of notices stays out of BookingService. The rejected
    alternative was an if/elif chain on the event type inside BookingService, which would make the
    booking code change every time a notice type is added and mix two responsibilities.

    The registry is per instance, so registering a type in one factory (for example in a test)
    never changes another.
    """

    def __init__(self) -> None:
        self._registry: dict[type[BookingEvent], type[Notice]] = {
            BookingConfirmed: ConfirmationNotice,
            BookingRejected: RejectionNotice,
            BookingCancelled: CancellationNotice,
        }

    def register(self, event_cls: type[BookingEvent], notice_cls: type[Notice]) -> None:
        """Map an event type to the notice type built for it (adds or replaces)."""
        self._registry[event_cls] = notice_cls

    def create(self, event: BookingEvent) -> Notice:
        """Return the notice for this event, or raise UnsupportedEventError."""
        notice_cls = self._registry.get(type(event))
        if notice_cls is None:
            raise UnsupportedEventError(f"No notice registered for {type(event).__name__}")
        return notice_cls.from_event(event)
