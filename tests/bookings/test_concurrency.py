"""Concurrency test for booking confirmation (QR-03, risk R1).

100 different slots; for each, two threads released together by a Barrier request the same slot,
each with its own session on a file database and a real BookingRepository. The BEGIN IMMEDIATE
recipe in app/core/db.py makes the overlap check and the insert one locked transaction, so exactly
one request per slot may be confirmed.
"""

import threading
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from app.bookings.repository import BookingRepository
from app.bookings.service import BookingService
from app.core.deps import CurrentUser
from app.core.enums import Role
from app.core.exceptions import BookingConflict
from app.core.interfaces import FacilityInfo
from app.facilities.models import Facility
from app.users.models import User
from tests.bookings.fakes import FakeLookup, FakePolicy, FakePublisher

NOW = datetime(2026, 11, 23, 8, 0)
SLOTS = 100


def _seed(factory: sessionmaker[Session]) -> FacilityInfo:
    with factory() as session:
        session.add_all(
            [
                User(id=1, name="A", email="a@example.com", role=Role.STUDENT, password_hash="x"),
                User(id=2, name="B", email="b@example.com", role=Role.STUDENT, password_hash="x"),
            ]
        )
        facility = Facility(name="Lab", capacity=30, requires_approval=False, active=True)
        session.add(facility)
        session.commit()
        return FacilityInfo(id=facility.id, capacity=30, requires_approval=False, active=True)


def _request(
    factory: sessionmaker[Session],
    facility: FacilityInfo,
    user: CurrentUser,
    start: datetime,
    barrier: threading.Barrier,
    results: list[str],
) -> None:
    barrier.wait()
    with factory() as session:
        service = BookingService(
            repository=BookingRepository(session),
            facilities=FakeLookup([facility]),
            policy_for=lambda _role: FakePolicy(),
            publisher=FakePublisher([]),
            now=lambda: NOW,
        )
        try:
            service.request_booking(user, facility.id, start, start + timedelta(hours=1))
            results.append("CONFIRMED")
        except BookingConflict:
            results.append("conflict")


def test_competing_requests_confirm_exactly_one_booking_per_slot(
    session_factory_file: sessionmaker[Session],
) -> None:
    facility = _seed(session_factory_file)
    users = [CurrentUser(id=1, role=Role.STUDENT), CurrentUser(id=2, role=Role.STUDENT)]
    outcomes = []

    for slot in range(SLOTS):
        start = datetime(2026, 11, 23, 10, 0) + timedelta(days=slot)
        barrier = threading.Barrier(2)
        results: list[str] = []
        threads = [
            threading.Thread(
                target=_request,
                args=(session_factory_file, facility, user, start, barrier, results),
            )
            for user in users
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
        outcomes.append(sorted(results))

    assert outcomes == [["CONFIRMED", "conflict"]] * SLOTS
    with session_factory_file() as session:
        confirmed = session.execute(
            text("SELECT COUNT(*) FROM bookings WHERE status = 'CONFIRMED'")
        ).scalar_one()
        overlapping_pairs = session.execute(
            text(
                "SELECT COUNT(*) FROM bookings a JOIN bookings b "
                "ON a.id < b.id AND a.facility_id = b.facility_id "
                "AND a.start_at < b.end_at AND b.start_at < a.end_at "
                "WHERE a.status = 'CONFIRMED' AND b.status = 'CONFIRMED'"
            )
        ).scalar_one()
    assert confirmed == SLOTS
    assert overlapping_pairs == 0
