"""Business logic for managing facilities (FR-02).

The service depends on the FacilityStore Protocol, not on SQLAlchemy, so it can be unit tested
with a fake store (Dependency Inversion). Role checks are done by the router (require_role).
"""

from typing import Protocol

from app.core.exceptions import NotFound
from app.facilities.models import Facility


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
