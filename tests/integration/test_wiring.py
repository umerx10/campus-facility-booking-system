"""Integration test for the app wiring in app.main (Observer: bookings -> notifications, QR-08).

The real lifespan runs (TestClient used as a context manager) on a temporary file database, with a
fresh publisher so no subscription leaks into other tests. Leaving the context runs the lifespan's
shutdown, which must wait for the asynchronous notification to be written.
"""

from collections.abc import Iterator
from datetime import UTC, datetime, time, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

import app.bookings.router as bookings_router
import app.main as main_module
from app.bookings.publisher import BookingEventPublisher
from app.core.db import get_session
from app.core.deps import CurrentUser, get_current_user
from app.core.enums import Role
from app.facilities.models import Facility, FacilityOperatingHours
from app.main import app
from app.notifications.models import Notification
from app.users.models import User

STUDENT_ID = 1


@pytest.fixture
def wired_app(
    monkeypatch: pytest.MonkeyPatch, session_factory_file: sessionmaker[Session]
) -> Iterator[datetime]:
    """Point the app at the file database and a fresh publisher; return a bookable start time."""
    start = datetime.now(UTC).replace(tzinfo=None, hour=10, minute=0, second=0, microsecond=0)
    start += timedelta(days=2)
    with session_factory_file() as session:
        session.add(
            User(id=STUDENT_ID, name="S", email="s@example.com", role=Role.STUDENT,
                 password_hash="x")
        )
        facility = Facility(id=1, name="Lab", capacity=30, requires_approval=False, active=True)
        session.add(facility)
        session.flush()
        session.add(
            FacilityOperatingHours(
                facility_id=1, weekday=start.weekday(), opens_at=time(8, 0), closes_at=time(20, 0)
            )
        )
        session.commit()

    publisher = BookingEventPublisher()
    monkeypatch.setattr(main_module, "engine", session_factory_file.kw["bind"], raising=False)
    monkeypatch.setattr(main_module, "session_factory", session_factory_file, raising=False)
    monkeypatch.setattr(main_module, "booking_events", publisher, raising=False)
    monkeypatch.setattr(bookings_router, "booking_events", publisher)

    def _session() -> Iterator[Session]:
        with session_factory_file() as session:
            yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(STUDENT_ID, Role.STUDENT)
    yield start
    app.dependency_overrides.clear()


def test_confirmed_booking_produces_a_notification_for_the_user(
    wired_app: datetime, session_factory_file: sessionmaker[Session]
) -> None:
    start = wired_app

    with TestClient(app) as client:
        response = client.post(
            "/bookings",
            json={
                "facility_id": 1,
                "start_at": start.isoformat(),
                "end_at": (start + timedelta(hours=1)).isoformat(),
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "CONFIRMED"
    # Leaving the block ran the lifespan shutdown, which waits for queued notifications.

    with session_factory_file() as session:
        notes = list(session.scalars(select(Notification).where(Notification.user_id == STUDENT_ID)))
    assert [n.event_type for n in notes] == ["BOOKING_CONFIRMED"]
