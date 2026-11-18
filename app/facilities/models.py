"""Facility tables (M1 section 8). Written in the shared skeleton; the owner takes them over."""

from datetime import datetime, time

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Facility(Base):
    """A bookable room, lab or ground. Deactivated facilities are kept, not deleted (FR-02)."""

    __tablename__ = "facilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    capacity: Mapped[int]
    requires_approval: Mapped[bool] = mapped_column(default=False)
    active: Mapped[bool] = mapped_column(default=True)


class FacilityOperatingHours(Base):
    """Opening window of a facility on one weekday (0 = Monday, as in datetime.weekday())."""

    __tablename__ = "facility_operating_hours"

    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"))
    weekday: Mapped[int]
    opens_at: Mapped[time]
    closes_at: Mapped[time]


class FacilityBlock(Base):
    """A maintenance block: no booking may overlap [start_at, end_at)."""

    __tablename__ = "facility_blocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"))
    start_at: Mapped[datetime]
    end_at: Mapped[datetime]
    reason: Mapped[str] = mapped_column(String(255))
