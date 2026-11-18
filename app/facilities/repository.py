"""Database access for facilities. All facility SQL lives here."""

from datetime import datetime, time

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from app.facilities.models import Facility, FacilityBlock, FacilityOperatingHours


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

    def replace_hours(self, facility_id: int, week: list[tuple[int, time, time]]) -> None:
        """Delete the facility's opening windows and store `week` (weekday, opens_at, closes_at)."""
        self._session.execute(
            delete(FacilityOperatingHours).where(FacilityOperatingHours.facility_id == facility_id)
        )
        self._session.add_all(
            FacilityOperatingHours(
                facility_id=facility_id, weekday=weekday, opens_at=opens_at, closes_at=closes_at
            )
            for weekday, opens_at, closes_at in week
        )
        self._session.flush()

    def list_hours(self, facility_id: int) -> list[FacilityOperatingHours]:
        """Return the facility's opening windows ordered by weekday."""
        query = (
            select(FacilityOperatingHours)
            .where(FacilityOperatingHours.facility_id == facility_id)
            .order_by(FacilityOperatingHours.weekday)
        )
        return list(self._session.scalars(query))

    def hours_for(self, facility_id: int, weekday: int) -> FacilityOperatingHours | None:
        """Return the opening window for that weekday, or None if the facility is closed."""
        query = select(FacilityOperatingHours).where(
            FacilityOperatingHours.facility_id == facility_id,
            FacilityOperatingHours.weekday == weekday,
        )
        return self._session.scalar(query)

    def add_block(
        self, facility_id: int, start_at: datetime, end_at: datetime, reason: str
    ) -> FacilityBlock:
        """Stage a maintenance block and return it with its id."""
        block = FacilityBlock(
            facility_id=facility_id, start_at=start_at, end_at=end_at, reason=reason
        )
        self._session.add(block)
        self._session.flush()
        return block

    def blocks_overlapping(
        self, facility_id: int, start: datetime, end: datetime
    ) -> list[FacilityBlock]:
        """Return the blocks that overlap [start, end), ordered by start time (half-open rule)."""
        query = (
            select(FacilityBlock)
            .where(
                FacilityBlock.facility_id == facility_id,
                FacilityBlock.start_at < end,
                start < FacilityBlock.end_at,
            )
            .order_by(FacilityBlock.start_at)
        )
        return list(self._session.scalars(query))

    def has_block_overlapping(self, facility_id: int, start: datetime, end: datetime) -> bool:
        """True if any block overlaps [start, end): block.start < end and start < block.end."""
        query = select(
            exists().where(
                FacilityBlock.facility_id == facility_id,
                FacilityBlock.start_at < end,
                start < FacilityBlock.end_at,
            )
        )
        return bool(self._session.scalar(query))

    def commit(self) -> None:
        """Commit the current transaction."""
        self._session.commit()
