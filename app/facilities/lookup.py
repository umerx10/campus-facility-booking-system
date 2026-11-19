"""SqlFacilityLookup: the database implementation of the FacilityLookup Protocol (FR-03).

The Booking module depends on the FacilityLookup Protocol in app.core.interfaces, not on this class
or on the Facility model (Dependency Inversion), so its service is unit tested with a fake lookup
and receives this class only when the API wires it up.

Operating hours are compared in the same time base as bookings (naive UTC); this is an M2
assumption. A booking must start and end on the same day, inside that weekday's window.
"""

from datetime import datetime
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.exceptions import NotFound
from app.core.interfaces import FacilityInfo
from app.facilities.repository import FacilityRepository


class SqlFacilityLookup:
    """Answers the facility questions Booking asks, using FacilityRepository for all SQL."""

    def __init__(self, session: Session) -> None:
        self._facilities = FacilityRepository(session)

    def get_facility(self, facility_id: int) -> FacilityInfo:
        """Return the facility's facts, active or not, or raise NotFound."""
        facility = self._facilities.get(facility_id)
        if facility is None:
            raise NotFound(f"Facility {facility_id} not found")
        return FacilityInfo(
            id=facility.id,
            capacity=facility.capacity,
            requires_approval=facility.requires_approval,
            active=facility.active,
        )

    def is_within_hours(self, facility_id: int, start: datetime, end: datetime) -> bool:
        """True if [start, end) lies inside the opening window of start's weekday.

        False when start and end are on different days or the facility has no window that day.
        """
        if start.date() != end.date():
            return False
        hours = self._facilities.hours_for(facility_id, start.weekday())
        if hours is None:
            return False
        return hours.opens_at <= start.time() and end.time() <= hours.closes_at

    def overlaps_block(self, facility_id: int, start: datetime, end: datetime) -> bool:
        """True if [start, end) overlaps a maintenance block (half-open: back-to-back is free)."""
        return self._facilities.has_block_overlapping(facility_id, start, end)


def get_facility_lookup(session: Annotated[Session, Depends(get_session)]) -> SqlFacilityLookup:
    """FastAPI dependency: the lookup on the request's session."""
    return SqlFacilityLookup(session)
