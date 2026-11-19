"""API tests for bookings (FR-03, FR-04, FR-05, FR-07, FR-09).

get_booking_service is overridden with a service on the test session that uses the real
repository and SqlFacilityLookup, an allow-all policy (role policies are tested in the approvals
module) and a fixed clock: Monday 23 Nov 2026 08:00 UTC.
"""

from collections.abc import Callable, Iterator
from datetime import datetime, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bookings.models import Booking
from app.bookings.repository import BookingRepository
from app.bookings.router import get_booking_service
from app.bookings.service import BookingService
from app.core.deps import CurrentUser
from app.core.enums import Role
from app.facilities.lookup import SqlFacilityLookup
from app.facilities.models import Facility, FacilityOperatingHours
from app.main import app
from app.users.models import User
from tests.bookings.fakes import FakePolicy, FakePublisher

NOW = datetime(2026, 11, 23, 8, 0)
STUDENT_ID, OTHER_ID, ADMIN_ID = 1, 2, 3


@pytest.fixture
def world(db_session: Session) -> dict[str, Facility]:
    """Three users, a lab and a restricted hall, both open Monday 08:00-20:00."""
    db_session.add_all(
        [
            User(id=STUDENT_ID, name="S", email="s@example.com", role=Role.STUDENT,
                 password_hash="x"),
            User(id=OTHER_ID, name="O", email="o@example.com", role=Role.STUDENT,
                 password_hash="x"),
            User(id=ADMIN_ID, name="A", email="a@example.com", role=Role.ADMIN, password_hash="x"),
        ]
    )
    lab = Facility(name="Lab", capacity=30, requires_approval=False, active=True)
    hall = Facility(name="Hall", capacity=300, requires_approval=True, active=True)
    db_session.add_all([lab, hall])
    db_session.flush()
    db_session.add_all(
        [
            FacilityOperatingHours(
                facility_id=f.id, weekday=0, opens_at=time(8, 0), closes_at=time(20, 0)
            )
            for f in (lab, hall)
        ]
    )
    db_session.commit()
    return {"lab": lab, "hall": hall}


@pytest.fixture
def api(client: TestClient, db_session: Session) -> Iterator[TestClient]:
    """The client, with the booking service built on the test session."""

    def _service() -> BookingService:
        return BookingService(
            repository=BookingRepository(db_session),
            facilities=SqlFacilityLookup(db_session),
            policy_for=lambda _role: FakePolicy(),
            publisher=FakePublisher([]),
            now=lambda: NOW,
        )

    app.dependency_overrides[get_booking_service] = _service
    yield client


def _book(api: TestClient, facility: Facility, start: str, end: str):  # type: ignore[no-untyped-def]
    return api.post(
        "/bookings", json={"facility_id": facility.id, "start_at": start, "end_at": end}
    )


# ---- POST /bookings ----


def test_student_books_a_free_slot(
    api: TestClient, as_user: Callable[..., CurrentUser], world: dict[str, Facility]
) -> None:
    as_user(Role.STUDENT, STUDENT_ID)

    response = _book(api, world["lab"], "2026-11-23T10:00:00", "2026-11-23T11:00:00")

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["status"] == "CONFIRMED"
    assert body["user_id"] == STUDENT_ID
    assert body["facility_id"] == world["lab"].id
    assert body["start_at"] == "2026-11-23T10:00:00"
    assert body["end_at"] == "2026-11-23T11:00:00"


def test_restricted_facility_gives_pending(
    api: TestClient, as_user: Callable[..., CurrentUser], world: dict[str, Facility]
) -> None:
    as_user(Role.STUDENT, STUDENT_ID)

    response = _book(api, world["hall"], "2026-11-23T10:00:00", "2026-11-23T11:00:00")

    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"


def test_overlapping_request_returns_409(
    api: TestClient, as_user: Callable[..., CurrentUser], world: dict[str, Facility]
) -> None:
    as_user(Role.STUDENT, STUDENT_ID)
    _book(api, world["lab"], "2026-11-23T10:00:00", "2026-11-23T12:00:00")
    as_user(Role.STUDENT, OTHER_ID)

    response = _book(api, world["lab"], "2026-11-23T11:00:00", "2026-11-23T13:00:00")

    assert response.status_code == 409
    assert response.json()["error"] == "BookingConflict"


def test_outside_hours_returns_409(
    api: TestClient, as_user: Callable[..., CurrentUser], world: dict[str, Facility]
) -> None:
    as_user(Role.STUDENT, STUDENT_ID)

    response = _book(api, world["lab"], "2026-11-23T19:30:00", "2026-11-23T20:30:00")

    assert response.status_code == 409
    assert response.json()["error"] == "FacilityUnavailable"


def test_end_before_start_returns_422(
    api: TestClient, as_user: Callable[..., CurrentUser], world: dict[str, Facility]
) -> None:
    as_user(Role.STUDENT, STUDENT_ID)

    response = _book(api, world["lab"], "2026-11-23T11:00:00", "2026-11-23T10:00:00")

    assert response.status_code == 422


def test_timezone_aware_input_is_stored_as_naive_utc(
    api: TestClient,
    as_user: Callable[..., CurrentUser],
    world: dict[str, Facility],
    db_session: Session,
) -> None:
    as_user(Role.STUDENT, STUDENT_ID)

    response = _book(api, world["lab"], "2026-11-23T15:00:00+05:00", "2026-11-23T16:00:00+05:00")

    assert response.status_code == 201
    stored = db_session.get(Booking, response.json()["id"])
    assert stored is not None
    assert (stored.start_at, stored.end_at) == (
        datetime(2026, 11, 23, 10, 0),
        datetime(2026, 11, 23, 11, 0),
    )


@pytest.mark.usefixtures("world")
def test_booking_without_authentication_returns_401(api: TestClient) -> None:
    response = api.post(
        "/bookings",
        json={"facility_id": 1, "start_at": "2026-11-23T10:00:00", "end_at": "2026-11-23T11:00:00"},
    )

    assert response.status_code == 401


# ---- GET /bookings/me ----


def test_me_lists_only_my_bookings(
    api: TestClient, as_user: Callable[..., CurrentUser], world: dict[str, Facility]
) -> None:
    as_user(Role.STUDENT, STUDENT_ID)
    mine = _book(api, world["lab"], "2026-11-23T10:00:00", "2026-11-23T11:00:00").json()
    as_user(Role.STUDENT, OTHER_ID)
    _book(api, world["lab"], "2026-11-23T12:00:00", "2026-11-23T13:00:00")
    as_user(Role.STUDENT, STUDENT_ID)

    response = api.get("/bookings/me")

    assert response.status_code == 200
    assert [b["id"] for b in response.json()] == [mine["id"]]


# ---- POST /bookings/{id}/cancel and GET /bookings/{id}/history ----


def test_cancel_then_history_shows_both_changes(
    api: TestClient, as_user: Callable[..., CurrentUser], world: dict[str, Facility]
) -> None:
    as_user(Role.STUDENT, STUDENT_ID)
    booking = _book(api, world["lab"], "2026-11-23T10:00:00", "2026-11-23T11:00:00").json()

    cancelled = api.post(f"/bookings/{booking['id']}/cancel")
    history = api.get(f"/bookings/{booking['id']}/history")

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert history.status_code == 200
    assert [(h["old_status"], h["new_status"], h["actor_id"]) for h in history.json()] == [
        (None, "CONFIRMED", STUDENT_ID),
        ("CONFIRMED", "CANCELLED", STUDENT_ID),
    ]


def test_cancelling_twice_returns_409(
    api: TestClient, as_user: Callable[..., CurrentUser], world: dict[str, Facility]
) -> None:
    as_user(Role.STUDENT, STUDENT_ID)
    booking = _book(api, world["lab"], "2026-11-23T10:00:00", "2026-11-23T11:00:00").json()
    api.post(f"/bookings/{booking['id']}/cancel")

    response = api.post(f"/bookings/{booking['id']}/cancel")

    assert response.status_code == 409


def test_another_student_cannot_cancel_or_see_history(
    api: TestClient,
    as_user: Callable[..., CurrentUser],
    world: dict[str, Facility],
    db_session: Session,
) -> None:
    as_user(Role.STUDENT, STUDENT_ID)
    booking = _book(api, world["lab"], "2026-11-23T10:00:00", "2026-11-23T11:00:00").json()
    as_user(Role.STUDENT, OTHER_ID)

    cancel = api.post(f"/bookings/{booking['id']}/cancel")
    history = api.get(f"/bookings/{booking['id']}/history")

    assert (cancel.status_code, history.status_code) == (404, 404)
    stored = db_session.scalar(select(Booking).where(Booking.id == booking["id"]))
    assert stored is not None
    assert stored.status == "CONFIRMED"


def test_admin_sees_any_bookings_history(
    api: TestClient, as_user: Callable[..., CurrentUser], world: dict[str, Facility]
) -> None:
    as_user(Role.STUDENT, STUDENT_ID)
    booking = _book(api, world["lab"], "2026-11-23T10:00:00", "2026-11-23T11:00:00").json()
    as_user(Role.ADMIN, ADMIN_ID)

    response = api.get(f"/bookings/{booking['id']}/history")

    assert response.status_code == 200
    assert len(response.json()) == 1


# ---- GET /bookings/schedule ----


def test_schedule_lists_that_days_confirmed_bookings_only(
    api: TestClient, as_user: Callable[..., CurrentUser], world: dict[str, Facility]
) -> None:
    as_user(Role.STUDENT, STUDENT_ID)
    kept = _book(api, world["lab"], "2026-11-23T10:00:00", "2026-11-23T11:00:00").json()
    gone = _book(api, world["lab"], "2026-11-23T12:00:00", "2026-11-23T13:00:00").json()
    api.post(f"/bookings/{gone['id']}/cancel")
    _book(api, world["lab"], "2026-11-30T10:00:00", "2026-11-30T11:00:00")

    response = api.get(f"/bookings/schedule?facility_id={world['lab'].id}&date=2026-11-23")

    assert response.status_code == 200
    assert [b["id"] for b in response.json()] == [kept["id"]]
