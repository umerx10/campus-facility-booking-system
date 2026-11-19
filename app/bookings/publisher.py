"""BookingEventPublisher: the Observer subject for booking events.

The booking service publishes BookingConfirmed, BookingRejected and BookingCancelled after its
transaction commits. Subscribers (notifications, and any later listener) register a handler for an
exact event type, so a new subscriber is added without changing the booking code (Open/Closed).

Subscriptions are made once at application start-up (app.main lifespan), before requests are served,
so the handler lists are only read while requests run.
"""

import logging
from collections import defaultdict
from collections.abc import Callable

from app.core.events import BookingEvent

logger = logging.getLogger(__name__)

Handler = Callable[[BookingEvent], None]


class BookingEventPublisher:
    """Implements the EventPublisher Protocol: calls each handler subscribed to the event's type."""

    def __init__(self) -> None:
        self._handlers: defaultdict[type[BookingEvent], list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type[BookingEvent], handler: Handler) -> None:
        """Call `handler` for every published event whose type is exactly `event_type`."""
        self._handlers[event_type].append(handler)

    def publish(self, event: BookingEvent) -> None:
        """Send `event` to its handlers in subscription order.

        A handler that raises is logged at ERROR and skipped: the booking is already committed, so
        one failing subscriber must not stop the others or turn a successful request into an error.
        """
        for handler in list(self._handlers.get(type(event), [])):
            try:
                handler(event)
            except Exception:  # pylint: disable=broad-exception-caught  # isolate subscribers (see docstring)
                logger.exception(
                    "Subscriber %r failed for %s #%s",
                    handler,
                    type(event).__name__,
                    event.booking_id,
                )


booking_events = BookingEventPublisher()
