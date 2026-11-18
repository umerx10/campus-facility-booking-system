"""Tests for NotificationSubscriber: Observer registration, storage, failure isolation, asynchrony."""

import logging
import threading
from collections import defaultdict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.enums import Role
from app.core.events import BookingCancelled, BookingConfirmed, BookingEvent, BookingRejected
from app.notifications.factory import NotificationFactory
from app.notifications.models import Notification
from app.notifications.subscriber import NotificationSubscriber
from app.users.models import User


class FakePublisher:
    """Implements the EventPublisher Protocol in memory."""

    def __init__(self) -> None:
        self.handlers: dict[type[BookingEvent], list[Callable[[BookingEvent], None]]] = (
            defaultdict(list)
        )

    def subscribe(
        self, event_type: type[BookingEvent], handler: Callable[[BookingEvent], None]
    ) -> None:
        """Remember the handler for this event type."""
        self.handlers[event_type].append(handler)

    def publish(self, event: BookingEvent) -> None:
        """Call every handler subscribed to the event's type."""
        for handler in self.handlers[type(event)]:
            handler(event)


class ImmediateExecutor:
    """An executor whose submit runs the function at once, so unit tests stay synchronous."""

    def submit(self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> None:
        """Run fn now."""
        fn(*args, **kwargs)


def _event(event_cls: type[BookingEvent] = BookingConfirmed, user_id: int = 7) -> BookingEvent:
    return event_cls(
        booking_id=42, user_id=user_id, facility_id=3, occurred_at=datetime(2026, 11, 18, tzinfo=UTC)
    )


def _add_user(factory: Callable[[], Session], user_id: int = 7) -> None:
    with factory() as session:
        session.add(
            User(
                id=user_id, name="Notified User", email=f"user{user_id}@example.com",
                role=Role.STUDENT, password_hash="not-used-here",
            )
        )
        session.commit()


def _notifications(factory: Callable[[], Session]) -> list[Notification]:
    with factory() as session:
        return list(session.scalars(select(Notification)))


def _count(factory: Callable[[], Session]) -> int:
    with factory() as session:
        return session.scalar(select(func.count()).select_from(Notification)) or 0


@pytest.fixture
def memory_factory(engine: Engine) -> sessionmaker[Session]:
    """Session factory on the in-memory test database."""
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_register_subscribes_handle_to_all_three_booking_events(
    memory_factory: sessionmaker[Session],
) -> None:
    publisher = FakePublisher()
    subscriber = NotificationSubscriber(NotificationFactory(), memory_factory, ImmediateExecutor())

    subscriber.register(publisher)

    assert set(publisher.handlers) == {BookingConfirmed, BookingRejected, BookingCancelled}
    for handlers in publisher.handlers.values():
        assert handlers == [subscriber.handle]


def test_published_confirmation_is_stored_as_one_notification(
    memory_factory: sessionmaker[Session],
) -> None:
    _add_user(memory_factory, user_id=7)
    publisher = FakePublisher()
    NotificationSubscriber(NotificationFactory(), memory_factory, ImmediateExecutor()).register(
        publisher
    )

    publisher.publish(_event(BookingConfirmed, user_id=7))

    rows = _notifications(memory_factory)
    assert len(rows) == 1
    assert rows[0].user_id == 7
    assert rows[0].event_type == "BOOKING_CONFIRMED"
    assert "42" in rows[0].message
    assert rows[0].created_at is not None
    assert rows[0].read_at is None


def test_a_failed_save_is_logged_at_error_and_does_not_raise(
    memory_factory: sessionmaker[Session], caplog: pytest.LogCaptureFixture
) -> None:
    """M1 promise: a notification failure never undoes or breaks the booking that caused it."""
    subscriber = NotificationSubscriber(NotificationFactory(), memory_factory, ImmediateExecutor())

    # No user 999 exists, so the foreign key makes the insert fail inside delivery.
    with caplog.at_level(logging.ERROR):
        subscriber.handle(_event(BookingConfirmed, user_id=999))

    assert any(r.levelno == logging.ERROR and r.exc_info for r in caplog.records)
    assert _count(memory_factory) == 0


def test_handle_returns_before_delivery_finishes(
    session_factory_file: sessionmaker[Session],
) -> None:
    """Proves asynchrony: handle() returns while delivery is still blocked on a worker thread."""
    _add_user(session_factory_file, user_id=7)
    release = threading.Event()

    def blocked_session_factory() -> Session:
        release.wait(timeout=5)
        return session_factory_file()

    executor = ThreadPoolExecutor(max_workers=1)
    subscriber = NotificationSubscriber(NotificationFactory(), blocked_session_factory, executor)
    try:
        subscriber.handle(_event(BookingConfirmed, user_id=7))
        assert not release.is_set()
        assert _count(session_factory_file) == 0
    finally:
        release.set()
        executor.shutdown(wait=True)

    assert _count(session_factory_file) == 1
