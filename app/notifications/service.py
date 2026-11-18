"""Business logic for reading notifications and marking them read (FR-10)."""

from typing import Protocol

from app.core.exceptions import NotFound
from app.notifications.models import Notification


class NotificationStore(Protocol):
    """What the service needs from storage (implemented by NotificationRepository)."""

    def list_for_user(self, user_id: int) -> list[Notification]:
        """Return the user's notifications, newest first."""

    def get_for_user(self, notification_id: int, user_id: int) -> Notification | None:
        """Return the notification if it belongs to the user, else None."""

    def mark_read(self, notification: Notification) -> None:
        """Set read_at to now."""

    def commit(self) -> None:
        """Commit the current transaction."""


class NotificationService:
    """Lets a user see and acknowledge only their own notifications."""

    def __init__(self, notifications: NotificationStore) -> None:
        self._notifications = notifications

    def list_for_user(self, user_id: int) -> list[Notification]:
        """Return the user's notifications, newest first."""
        return self._notifications.list_for_user(user_id)

    def mark_read(self, notification_id: int, user_id: int) -> Notification:
        """Mark the user's notification read and return it.

        Another user's notification gives the same NotFound as a missing one, so ids belonging to
        other users are not revealed. Marking twice keeps the first read time.
        """
        notification = self._notifications.get_for_user(notification_id, user_id)
        if notification is None:
            raise NotFound(f"Notification {notification_id} not found")
        if notification.read_at is None:
            self._notifications.mark_read(notification)
            self._notifications.commit()
        return notification
