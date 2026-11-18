"""NotificationSubscriber: the Observer that turns booking events into stored notifications (FR-10).

Asynchronous delivery and its thread-safety strategy:
- `handle(event)` only submits `_deliver(event)` to an executor and returns at once, so the request
  that published the event never waits for, or fails because of, a notification.
- Each delivery runs on a worker thread and opens its OWN session from `session_factory`; a session
  is never shared between threads, and never the request's session.
- Writes from several workers and requests are serialized by SQLite's write lock, taken at the
  start of every transaction by the BEGIN IMMEDIATE recipe in app.core.db.
- The publisher calls subscribers only after the booking transaction has committed (Booking module
  contract), so a notification can never refer to a booking that was rolled back, and a failed
  notification can never roll a booking back.
- A delivery failure is rolled back and logged with its stack trace (logger.exception); it is never
  re-raised, because nobody is waiting for the result on the worker thread.
"""

import logging
from collections.abc import Callable
from typing import Any, Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.events import BookingCancelled, BookingConfirmed, BookingEvent, BookingRejected
from app.core.interfaces import EventPublisher
from app.notifications.factory import NotificationFactory, UnsupportedEventError
from app.notifications.repository import NotificationRepository

logger = logging.getLogger(__name__)

SUBSCRIBED_EVENTS: tuple[type[BookingEvent], ...] = (
    BookingConfirmed,
    BookingRejected,
    BookingCancelled,
)


class TaskExecutor(Protocol):  # pylint: disable=too-few-public-methods  # one method by design (ISP)
    """Anything that can run a function later, such as concurrent.futures.ThreadPoolExecutor."""

    def submit(self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
        """Schedule fn(*args, **kwargs)."""


class NotificationSubscriber:
    """Listens for booking events and stores one in-app notification per event, asynchronously.

    Its collaborators are injected (Dependency Inversion): the factory decides what to say, the
    session factory gives each delivery its own session, and the executor decides where it runs.
    Unit tests pass an executor that runs immediately; production passes a ThreadPoolExecutor.
    """

    def __init__(
        self,
        factory: NotificationFactory,
        session_factory: Callable[[], Session],
        executor: TaskExecutor,
    ) -> None:
        self._factory = factory
        self._session_factory = session_factory
        self._executor = executor

    def register(self, publisher: EventPublisher) -> None:
        """Subscribe handle() to every booking event that produces a notification."""
        for event_type in SUBSCRIBED_EVENTS:
            publisher.subscribe(event_type, self.handle)

    def handle(self, event: BookingEvent) -> None:
        """Queue delivery of the event's notification and return immediately."""
        self._executor.submit(self._deliver, event)

    def _deliver(self, event: BookingEvent) -> None:
        """Build and store the notice on the worker thread. Never raises."""
        try:
            notice = self._factory.create(event)
        except UnsupportedEventError:
            logger.exception("No notice type for event %s", type(event).__name__)
            return
        with self._session_factory() as session:
            try:
                NotificationRepository(session).add(
                    notice.user_id, notice.event_type, notice.message
                )
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                logger.exception(
                    "Could not store %s notification for user %s (booking %s)",
                    notice.event_type,
                    notice.user_id,
                    event.booking_id,
                )
