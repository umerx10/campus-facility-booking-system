"""Database access for facilities. All facility SQL lives here."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.facilities.models import Facility


class FacilityRepository:
    """Stores and reads facilities through the session it is given; the caller commits."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, name: str, capacity: int, requires_approval: bool) -> Facility:
        """Stage a new active facility and return it with its id."""
        facility = Facility(
            name=name, capacity=capacity, requires_approval=requires_approval, active=True
        )
        self._session.add(facility)
        self._session.flush()
        return facility

    def get(self, facility_id: int) -> Facility | None:
        """Return the facility, active or not, or None if the id is unknown."""
        return self._session.get(Facility, facility_id)

    def list_active(self) -> list[Facility]:
        """Return the active facilities ordered by name."""
        query = select(Facility).where(Facility.active.is_(True)).order_by(
            Facility.name, Facility.id
        )
        return list(self._session.scalars(query))

    def update(
        self,
        facility: Facility,
        name: str | None = None,
        capacity: int | None = None,
        requires_approval: bool | None = None,
    ) -> None:
        """Change the given fields; a field left as None keeps its current value."""
        if name is not None:
            facility.name = name
        if capacity is not None:
            facility.capacity = capacity
        if requires_approval is not None:
            facility.requires_approval = requires_approval
        self._session.flush()

    def deactivate(self, facility: Facility) -> None:
        """Mark the facility inactive. The row is kept so old bookings still refer to it."""
        facility.active = False
        self._session.flush()

    def commit(self) -> None:
        """Commit the current transaction."""
        self._session.commit()
