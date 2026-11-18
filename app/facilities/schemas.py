"""Request and response bodies for Facility Management. Input is validated here, before any service.

The limits come from the facilities table (name is String(100)) and FR-02: a facility must have a
name and room for at least one person. Out-of-range input is rejected with 422 by FastAPI.
"""

import datetime as dt

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

NAME_MAX_LENGTH = 100


class FacilityCreate(BaseModel):
    """A new facility. requires_approval marks restricted facilities (FR-08)."""

    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    capacity: int = Field(ge=1)
    requires_approval: bool = False


class FacilityUpdate(BaseModel):
    """A partial update: only the fields that are sent (and not null) are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    capacity: int | None = Field(default=None, ge=1)
    requires_approval: bool | None = None


class FacilityOut(BaseModel):
    """A facility as every authenticated user sees it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    capacity: int
    requires_approval: bool
    active: bool


def to_naive_utc(value: dt.datetime) -> dt.datetime:
    """Convert a timezone-aware datetime to naive UTC; a naive datetime is taken as UTC already."""
    if value.tzinfo is None:
        return value
    return value.astimezone(dt.UTC).replace(tzinfo=None)


class OperatingHoursIn(BaseModel):
    """Opening window for one weekday (0 = Monday). Opening must be before closing."""

    weekday: int = Field(ge=0, le=6)
    opens_at: dt.time
    closes_at: dt.time

    @model_validator(mode="after")
    def check_window(self) -> "OperatingHoursIn":
        """Reject an empty or reversed window (opens_at >= closes_at)."""
        if self.opens_at >= self.closes_at:
            raise ValueError("opens_at must be before closes_at")
        return self


class OperatingHoursOut(BaseModel):
    """A stored opening window."""

    model_config = ConfigDict(from_attributes=True)

    weekday: int
    opens_at: dt.time
    closes_at: dt.time


class BlockIn(BaseModel):
    """A maintenance block [start_at, end_at). Datetimes are stored as naive UTC."""

    start_at: dt.datetime
    end_at: dt.datetime
    reason: str = Field(min_length=1, max_length=255)

    @field_validator("start_at", "end_at")
    @classmethod
    def normalise(cls, value: dt.datetime) -> dt.datetime:
        """Store every datetime as naive UTC."""
        return to_naive_utc(value)

    @model_validator(mode="after")
    def check_interval(self) -> "BlockIn":
        """Reject an empty or reversed interval (start_at >= end_at)."""
        if self.start_at >= self.end_at:
            raise ValueError("start_at must be before end_at")
        return self


class BlockOut(BaseModel):
    """A stored maintenance block."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    start_at: dt.datetime
    end_at: dt.datetime
    reason: str


class DayHours(BaseModel):
    """Opening window on the requested day."""

    model_config = ConfigDict(from_attributes=True)

    opens_at: dt.time
    closes_at: dt.time


class ScheduleOut(BaseModel):
    """A facility's hours and maintenance blocks on one day (FR-03, facility half).

    hours is None when the facility is closed that weekday. Bookings are served by the Booking
    module at GET /bookings/schedule.
    """

    facility_id: int
    date: dt.date
    hours: DayHours | None
    blocks: list[BlockOut]
