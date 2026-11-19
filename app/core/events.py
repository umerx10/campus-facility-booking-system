"""Booking domain events, published after the booking transaction commits (Observer pattern)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BookingEvent:
    """Fields shared by every booking event. Frozen, so subscribers cannot change it."""

    booking_id: int
    user_id: int
    facility_id: int
    occurred_at: datetime


@dataclass(frozen=True)
class BookingConfirmed(BookingEvent):
    """A booking became CONFIRMED."""


@dataclass(frozen=True)
class BookingRejected(BookingEvent):
    """An administrator rejected a pending booking."""


@dataclass(frozen=True)
class BookingCancelled(BookingEvent):
    """A booking was cancelled."""
