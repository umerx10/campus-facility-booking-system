"""HTTP routes for Notifications (FR-10): validate input, call a service, return a schema."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.deps import CurrentUser, get_current_user
from app.notifications.repository import NotificationRepository
from app.notifications.schemas import NotificationOut
from app.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service(
    session: Annotated[Session, Depends(get_session)],
) -> NotificationService:
    """Build the service on the request's session."""
    return NotificationService(NotificationRepository(session))


@router.get("")
def list_notifications(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> list[NotificationOut]:
    """Return the caller's notifications, newest first."""
    return [NotificationOut.model_validate(n) for n in service.list_for_user(user.id)]


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationOut:
    """Mark one of the caller's notifications as read."""
    return NotificationOut.model_validate(service.mark_read(notification_id, user.id))
