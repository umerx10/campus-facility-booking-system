"""Wiring for the Notifications module.

The integration lead calls register_notifications once the booking module's publisher exists, for
example in app.main's lifespan. app.main is deliberately not edited here.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from app.core.interfaces import EventPublisher
from app.notifications.factory import NotificationFactory
from app.notifications.subscriber import NotificationSubscriber, TaskExecutor


def register_notifications(
    publisher: EventPublisher,
    session_factory: Callable[[], Session],
    executor: TaskExecutor | None = None,
) -> NotificationSubscriber:
    """Create the subscriber, subscribe it to the publisher, and return it.

    Without an executor, a small pool of two worker threads named "notify-*" is created; the
    caller should shut it down when the app stops.
    """
    if executor is None:
        executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="notify")
    subscriber = NotificationSubscriber(NotificationFactory(), session_factory, executor)
    subscriber.register(publisher)
    return subscriber
