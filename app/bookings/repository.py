"""Database access for bookings and their history. All booking SQL lives here."""

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bookings.models import Booking, BookingHistory
from app.core.enums import BookingStatus


class BookingRepository:
    """Stores and reads bookings through the session it is given; the caller commits.

    Every engine runs `BEGIN IMMEDIATE` at the start of a transaction (app/core/db.py), so the
    overlap query and the insert that follows it run under SQLite's write lock.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        user_id: int,
        facility_id: int,
        start: datetime,
        end: datetime,
        status: BookingStatus,
    ) -> Booking:
        """Stage a new booking and return it with its id."""
        booking = Booking(
            user_id=user_id, facility_id=facility_id, start_at=start, end_at=end, status=status
        )
        self._session.add(booking)
        self._session.flush()
        return booking

    def get(self, booking_id: int) -> Booking | None:
        """Return the booking or None."""
        return self._session.get(Booking, booking_id)

    def find_confirmed_overlaps(
        self, facility_id: int, start: datetime, end: datetime, exclude_id: int | None = None
    ) -> list[Booking]:
        """Return CONFIRMED bookings of the facility that overlap [start, end) (half-open)."""
        query = select(Booking).where(
            Booking.facility_id == facility_id,
            Booking.status == BookingStatus.CONFIRMED,
            Booking.start_at < end,
            start < Booking.end_at,
        )
        if exclude_id is not None:
            query = query.where(Booking.id != exclude_id)
        return list(self._session.scalars(query))

    def add_history(
        self,
        booking_id: int,
        old_status: BookingStatus | None,
        new_status: BookingStatus,
        changed_at: datetime,
        actor_id: int,
    ) -> None:
        """Stage one status-change row (FR-09)."""
        self._session.add(
            BookingHistory(
                booking_id=booking_id,
                old_status=old_status,
                new_status=new_status,
                changed_at=changed_at,
                actor_id=actor_id,
            )
        )
        self._session.flush()

    def history_for(self, booking_id: int) -> list[BookingHistory]:
        """Return the booking's status changes, oldest first."""
        query = (
            select(BookingHistory)
            .where(BookingHistory.booking_id == booking_id)
            .order_by(BookingHistory.changed_at, BookingHistory.id)
        )
        return list(self._session.scalars(query))

    def list_for_user(self, user_id: int) -> list[Booking]:
        """Return the user's bookings ordered by start time."""
        query = select(Booking).where(Booking.user_id == user_id).order_by(Booking.start_at)
        return list(self._session.scalars(query))

    def list_pending(self) -> list[Booking]:
        """Return the PENDING bookings ordered by start time."""
        query = (
            select(Booking)
            .where(Booking.status == BookingStatus.PENDING)
            .order_by(Booking.start_at, Booking.id)
        )
        return list(self._session.scalars(query))

    def confirmed_on(self, facility_id: int, day: date) -> list[Booking]:
        """Return the facility's CONFIRMED bookings that overlap `day`, ordered by start time."""
        day_start = datetime.combine(day, time.min)
        day_end = day_start + timedelta(days=1)
        query = (
            select(Booking)
            .where(
                Booking.facility_id == facility_id,
                Booking.status == BookingStatus.CONFIRMED,
                Booking.start_at < day_end,
                day_start < Booking.end_at,
            )
            .order_by(Booking.start_at)
        )
        return list(self._session.scalars(query))

    def commit(self) -> None:
        """Commit the current transaction."""
        self._session.commit()
