"""Request and response bodies for bookings.

API datetimes are ISO 8601. Timezone-aware input is converted to naive UTC; naive input is taken as
UTC (M2 team plan). The interval rules themselves (end after start, not in the past) are checked by
BookingService, so they hold for every caller, not only the API.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import BookingStatus


class BookingRequest(BaseModel):
    """A request for a facility over [start_at, end_at)."""

    facility_id: int = Field(ge=1)
    start_at: datetime
    end_at: datetime

    @field_validator("start_at", "end_at")
    @classmethod
    def to_naive_utc(cls, value: datetime) -> datetime:
        """Store every datetime as naive UTC."""
        if value.tzinfo is None:
            return value
        return value.astimezone(UTC).replace(tzinfo=None)


class BookingOut(BaseModel):
    """A booking as its owner or an administrator sees it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    facility_id: int
    start_at: datetime
    end_at: datetime
    status: BookingStatus


class BookingHistoryOut(BaseModel):
    """One status change of a booking (FR-09)."""

    model_config = ConfigDict(from_attributes=True)

    old_status: BookingStatus | None
    new_status: BookingStatus
    changed_at: datetime
    actor_id: int
