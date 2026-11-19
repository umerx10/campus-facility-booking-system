"""Tests for NotificationFactory (Factory pattern, FR-10)."""

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from app.core.events import BookingCancelled, BookingConfirmed, BookingEvent, BookingRejected
from app.notifications.factory import (
    CancellationNotice,
    ConfirmationNotice,
    Notice,
    NotificationFactory,
    RejectionNotice,
    UnsupportedEventError,
)

OCCURRED_AT = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)


def _event(event_cls: type[BookingEvent]) -> BookingEvent:
    return event_cls(booking_id=42, user_id=7, facility_id=3, occurred_at=OCCURRED_AT)


@dataclass(frozen=True)
class BookingWaitlisted(BookingEvent):
    """An event type the factory does not know about out of the box."""


@dataclass(frozen=True)
class WaitlistNotice(Notice):
    """A notice type added by a test, without changing the factory."""

    @classmethod
    def from_event(cls, event: BookingEvent) -> "WaitlistNotice":
        return cls(
            user_id=event.user_id,
            event_type="BOOKING_WAITLISTED",
            message=f"Booking {event.booking_id} is on the waiting list.",
        )


@pytest.mark.parametrize(
    ("event_cls", "notice_cls", "event_type"),
    [
        (BookingConfirmed, ConfirmationNotice, "BOOKING_CONFIRMED"),
        (BookingRejected, RejectionNotice, "BOOKING_REJECTED"),
        (BookingCancelled, CancellationNotice, "BOOKING_CANCELLED"),
    ],
)
def test_create_builds_the_matching_notice(
    event_cls: type[BookingEvent], notice_cls: type[Notice], event_type: str
) -> None:
    notice = NotificationFactory().create(_event(event_cls))

    assert type(notice) is notice_cls  # pylint: disable=unidiomatic-typecheck  # exact class
    assert notice.user_id == 7
    assert notice.event_type == event_type
    assert "42" in notice.message


def test_each_built_in_notice_has_its_own_message() -> None:
    factory = NotificationFactory()

    messages = {
        factory.create(_event(cls)).message
        for cls in (BookingConfirmed, BookingRejected, BookingCancelled)
    }

    assert len(messages) == 3


def test_unregistered_event_type_raises_unsupported_event_error() -> None:
    with pytest.raises(UnsupportedEventError):
        NotificationFactory().create(_event(BookingWaitlisted))


def test_register_adds_a_new_event_type_without_changing_the_factory() -> None:
    """Open/Closed: a new notice type is added by registration, not by editing the factory."""
    factory = NotificationFactory()

    factory.register(BookingWaitlisted, WaitlistNotice)
    notice = factory.create(_event(BookingWaitlisted))

    assert isinstance(notice, WaitlistNotice)
    assert notice.event_type == "BOOKING_WAITLISTED"
    assert notice.user_id == 7


def test_registering_on_one_factory_does_not_change_another() -> None:
    first = NotificationFactory()
    second = NotificationFactory()

    first.register(BookingWaitlisted, WaitlistNotice)

    with pytest.raises(UnsupportedEventError):
        second.create(_event(BookingWaitlisted))
