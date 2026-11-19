"""Tests for BookingEventPublisher, the Observer subject for booking events."""

import logging
from datetime import datetime

import pytest

from app.bookings.publisher import BookingEventPublisher, booking_events
from app.core.events import BookingCancelled, BookingConfirmed, BookingEvent

CONFIRMED = BookingConfirmed(
    booking_id=1, user_id=2, facility_id=3, occurred_at=datetime(2026, 11, 23, 9, 0)
)
CANCELLED = BookingCancelled(
    booking_id=1, user_id=2, facility_id=3, occurred_at=datetime(2026, 11, 23, 9, 5)
)


def test_handler_receives_only_events_of_its_exact_type() -> None:
    publisher = BookingEventPublisher()
    confirmed: list[BookingEvent] = []
    base: list[BookingEvent] = []
    publisher.subscribe(BookingConfirmed, confirmed.append)
    publisher.subscribe(BookingEvent, base.append)

    publisher.publish(CONFIRMED)
    publisher.publish(CANCELLED)

    assert confirmed == [CONFIRMED]
    assert base == []


def test_every_handler_of_the_type_is_called_in_subscription_order() -> None:
    publisher = BookingEventPublisher()
    calls: list[str] = []
    publisher.subscribe(BookingCancelled, lambda e: calls.append("first"))
    publisher.subscribe(BookingCancelled, lambda e: calls.append("second"))

    publisher.publish(CANCELLED)

    assert calls == ["first", "second"]


def test_publish_with_no_subscribers_does_nothing() -> None:
    BookingEventPublisher().publish(CONFIRMED)


def test_failing_handler_is_logged_and_does_not_stop_the_others(
    caplog: pytest.LogCaptureFixture,
) -> None:
    publisher = BookingEventPublisher()
    received: list[BookingEvent] = []

    def broken(_event: BookingEvent) -> None:
        raise RuntimeError("handler exploded")

    publisher.subscribe(BookingConfirmed, broken)
    publisher.subscribe(BookingConfirmed, received.append)

    with caplog.at_level(logging.ERROR):
        publisher.publish(CONFIRMED)

    assert received == [CONFIRMED]
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1
    assert "handler exploded" in caplog.text


def test_shared_instance_is_a_booking_event_publisher() -> None:
    assert isinstance(booking_events, BookingEventPublisher)
