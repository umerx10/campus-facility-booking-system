"""Booking tables (M1 section 8). Written in the shared skeleton; the owner takes them over."""

from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.enums import BookingStatus

STATUS_TYPE = Enum(BookingStatus, native_enum=False, length=20)


class Booking(Base):
    """A request for a facility over the half-open interval [start_at, end_at)."""

    __tablename__ = "bookings"
    # Overlap checks filter by facility and time, so this index serves them.
    __table_args__ = (Index("ix_bookings_facility_interval", "facility_id", "start_at", "end_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    facility_id: Mapped[int] = mapped_column(ForeignKey("facilities.id"))
    start_at: Mapped[datetime]
    end_at: Mapped[datetime]
    status: Mapped[BookingStatus] = mapped_column(STATUS_TYPE, default=BookingStatus.PENDING)


class BookingHistory(Base):
    """One status change of a booking (FR-09). old_status is empty for the first entry."""

    __tablename__ = "booking_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"))
    old_status: Mapped[BookingStatus | None] = mapped_column(STATUS_TYPE)
    new_status: Mapped[BookingStatus] = mapped_column(STATUS_TYPE)
    changed_at: Mapped[datetime]
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
