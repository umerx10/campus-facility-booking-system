"""Business logic for managing facilities (FR-02).

The service depends on the FacilityStore Protocol, not on SQLAlchemy, so it can be unit tested
with a fake store (Dependency Inversion). Role checks are done by the router (require_role).
"""

from datetime import date, datetime, time, timedelta
from typing import Protocol

from app.core.exceptions import NotFound
from app.facilities.models import Facility, FacilityBlock, FacilityOperatingHours


class FacilityStore(Protocol):
    """What the service needs from storage (implemented by FacilityRepository)."""

    def add(self, name: str, capacity: int, requires_approval: bool) -> Facility:
        """Stage a new active facility and return it with its id."""

    def get(self, facility_id: int) -> Facility | None:
        """Return the facility, active or not, or None."""

    def list_active(self) -> list[Facility]:
        """Return the active facilities."""

    def update(
        self,
        facility: Facility,
        name: str | None = None,
        capacity: int | None = None,
        requires_approval: bool | None = None,
    ) -> None:
        """Change the given fields; None keeps the current value."""

    def deactivate(self, facility: Facility) -> None:
        """Mark the facility inactive."""

    def replace_hours(self, facility_id: int, week: list[tuple[int, time, time]]) -> None:
        """Replace the facility's opening windows."""

    def list_hours(self, facility_id: int) -> list[FacilityOperatingHours]:
        """Return the opening windows ordered by weekday."""

    def hours_for(self, facility_id: int, weekday: int) -> FacilityOperatingHours | None:
        """Return the opening window for that weekday, or None."""

    def add_block(
        self, facility_id: int, start_at: datetime, end_at: datetime, reason: str
    ) -> FacilityBlock:
        """Stage a maintenance block and return it."""

    def blocks_overlapping(
        self, facility_id: int, start: datetime, end: datetime
    ) -> list[FacilityBlock]:
        """Return the blocks that overlap [start, end)."""

    def commit(self) -> None:
        """Commit the current transaction."""


class FacilityService:
    """Creates, lists, updates and deactivates facilities. Facilities are never deleted."""

    def __init__(self, facilities: FacilityStore) -> None:
        self._facilities = facilities

    def create(self, name: str, capacity: int, requires_approval: bool = False) -> Facility:
        """Create an active facility and return it."""
        facility = self._facilities.add(name, capacity, requires_approval)
        self._facilities.commit()
        return facility

    def list_active(self) -> list[Facility]:
        """Return the facilities that can be booked."""
        return self._facilities.list_active()

    def get(self, facility_id: int) -> Facility:
        """Return the facility, including an inactive one, or raise NotFound."""
        facility = self._facilities.get(facility_id)
        if facility is None:
            raise NotFound(f"Facility {facility_id} not found")
        return facility

    def update(
        self,
        facility_id: int,
        name: str | None = None,
        capacity: int | None = None,
        requires_approval: bool | None = None,
    ) -> Facility:
        """Change the given fields of a facility and return it; raise NotFound if unknown."""
        facility = self.get(facility_id)
        self._facilities.update(facility, name, capacity, requires_approval)
        self._facilities.commit()
        return facility

    def deactivate(self, facility_id: int) -> Facility:
        """Take a facility out of service and return it; raise NotFound if unknown.

        Deactivating an inactive facility changes nothing (idempotent).
        """
        facility = self.get(facility_id)
        if facility.active:
            self._facilities.deactivate(facility)
            self._facilities.commit()
        return facility

    def set_hours(
        self, facility_id: int, week: list[tuple[int, time, time]]
    ) -> list[FacilityOperatingHours]:
        """Replace the weekly opening hours and return them; raise NotFound if unknown.

        A weekday that is not in `week` is closed.
        """
        self.get(facility_id)
        self._facilities.replace_hours(facility_id, week)
        self._facilities.commit()
        return self._facilities.list_hours(facility_id)

    def add_block(
        self, facility_id: int, start_at: datetime, end_at: datetime, reason: str
    ) -> FacilityBlock:
        """Add a maintenance block [start_at, end_at) and return it; raise NotFound if unknown."""
        self.get(facility_id)
        block = self._facilities.add_block(facility_id, start_at, end_at, reason)
        self._facilities.commit()
        return block

    def schedule(
        self, facility_id: int, day: date
    ) -> tuple[FacilityOperatingHours | None, list[FacilityBlock]]:
        """Return the opening window (None if closed) and the blocks that touch `day`."""
        self.get(facility_id)
        day_start = datetime.combine(day, time.min)
        day_end = day_start + timedelta(days=1)
        hours = self._facilities.hours_for(facility_id, day.weekday())
        blocks = self._facilities.blocks_overlapping(facility_id, day_start, day_end)
        return hours, blocks
