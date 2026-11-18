"""Database access for notifications. All notification SQL lives here."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.notifications.models import Notification


def _utc_now() -> datetime:
    """Current time as naive UTC, the format every CFBS datetime column stores."""
    return datetime.now(UTC).replace(tzinfo=None)


class NotificationRepository:
    """Stores and reads notifications through the session it is given; it sets the timestamps."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user_id: int, event_type: str, message: str) -> Notification:
        """Stage a new unread notification created now; the caller commits."""
        notification = Notification(
            user_id=user_id, event_type=event_type, message=message, created_at=_utc_now()
        )
        self._session.add(notification)
        self._session.flush()
        return notification

    def list_for_user(self, user_id: int) -> list[Notification]:
        """Return the user's notifications, newest first."""
        query = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc(), Notification.id.desc())
        )
        return list(self._session.scalars(query))

    def get_for_user(self, notification_id: int, user_id: int) -> Notification | None:
        """Return the notification only if it belongs to this user, otherwise None."""
        query = select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user_id
        )
        return self._session.scalar(query)

    def mark_read(self, notification: Notification) -> None:
        """Set read_at to now."""
        notification.read_at = _utc_now()
        self._session.flush()

    def commit(self) -> None:
        """Commit the current transaction."""
        self._session.commit()
