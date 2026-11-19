"""API tests for operating hours, maintenance blocks and the daily schedule (FR-02, FR-03)."""

from collections.abc import Callable
from datetime import datetime, time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.core.enums import Role
from app.facilities.models import Facility, FacilityBlock, FacilityOperatingHours

WEEKDAY_HOURS = [
    {"weekday": day, "opens_at": "08:00", "closes_at": "20:00"} for day in range(5)
]
BLOCK = {"start_at": "2026-11-23T10:00:00", "end_at": "2026-11-23T12:00:00", "reason": "Repair"}


@pytest.fixture
def hall(db_session: Session) -> Facility:
    """An active facility with no hours and no blocks."""
    facility = Facility(name="Main Hall", capacity=200, requires_approval=False, active=True)
    db_session.add(facility)
    db_session.commit()
    return facility


def _hours_rows(db_session: Session, facility_id: int) -> list[FacilityOperatingHours]:
    query = select(FacilityOperatingHours).where(
        FacilityOperatingHours.facility_id == facility_id
    )
    return list(db_session.scalars(query))


def _block_rows(db_session: Session, facility_id: int) -> list[FacilityBlock]:
    query = select(FacilityBlock).where(FacilityBlock.facility_id == facility_id)
    return list(db_session.scalars(query))


# ---- PUT /facilities/{id}/hours ----


def test_admin_sets_weekly_hours(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    hall: Facility,
    db_session: Session,
) -> None:
    as_user(Role.ADMIN)

    response = client.put(f"/facilities/{hall.id}/hours", json=WEEKDAY_HOURS)

    assert response.status_code == 200
    body = response.json()
    assert [row["weekday"] for row in body] == [0, 1, 2, 3, 4]
    assert body[0]["opens_at"] == "08:00:00"
    assert body[0]["closes_at"] == "20:00:00"
    assert len(_hours_rows(db_session, hall.id)) == 5


def test_setting_hours_again_replaces_the_week(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    hall: Facility,
    db_session: Session,
) -> None:
    as_user(Role.ADMIN)
    client.put(f"/facilities/{hall.id}/hours", json=WEEKDAY_HOURS)

    response = client.put(
        f"/facilities/{hall.id}/hours",
        json=[{"weekday": 5, "opens_at": "09:00", "closes_at": "13:00"}],
    )

    assert response.status_code == 200
    rows = _hours_rows(db_session, hall.id)
    assert [(r.weekday, r.opens_at, r.closes_at) for r in rows] == [
        (5, time(9, 0), time(13, 0))
    ]


@pytest.mark.parametrize(
    "row",
    [
        {"weekday": -1, "opens_at": "08:00", "closes_at": "20:00"},
        {"weekday": 7, "opens_at": "08:00", "closes_at": "20:00"},
        {"weekday": 0, "opens_at": "10:00", "closes_at": "10:00"},
        {"weekday": 0, "opens_at": "20:00", "closes_at": "08:00"},
    ],
    ids=["weekday -1", "weekday 7", "opens_at == closes_at", "opens_at after closes_at"],
)
def test_invalid_hours_return_422(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    hall: Facility,
    db_session: Session,
    row: dict[str, object],
) -> None:
    as_user(Role.ADMIN)

    response = client.put(f"/facilities/{hall.id}/hours", json=[row])

    assert response.status_code == 422
    assert _hours_rows(db_session, hall.id) == []


def test_student_cannot_set_hours(
    client: TestClient, as_user: Callable[..., CurrentUser], hall: Facility
) -> None:
    as_user(Role.STUDENT)

    response = client.put(f"/facilities/{hall.id}/hours", json=WEEKDAY_HOURS)

    assert response.status_code == 403


def test_set_hours_for_unknown_facility_returns_404(
    client: TestClient, as_user: Callable[..., CurrentUser]
) -> None:
    as_user(Role.ADMIN)

    response = client.put("/facilities/9999/hours", json=WEEKDAY_HOURS)

    assert response.status_code == 404
    assert response.json()["error"] == "NotFound"


# ---- POST /facilities/{id}/blocks ----


def test_admin_adds_maintenance_block(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    hall: Facility,
    db_session: Session,
) -> None:
    as_user(Role.ADMIN)

    response = client.post(f"/facilities/{hall.id}/blocks", json=BLOCK)

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["start_at"] == "2026-11-23T10:00:00"
    assert body["end_at"] == "2026-11-23T12:00:00"
    assert body["reason"] == "Repair"
    assert len(_block_rows(db_session, hall.id)) == 1


def test_timezone_aware_block_is_stored_as_naive_utc(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    hall: Facility,
    db_session: Session,
) -> None:
    as_user(Role.ADMIN)

    response = client.post(
        f"/facilities/{hall.id}/blocks",
        json={
            "start_at": "2026-11-23T15:00:00+05:00",
            "end_at": "2026-11-23T17:00:00+05:00",
            "reason": "Repair",
        },
    )

    assert response.status_code == 201
    stored = _block_rows(db_session, hall.id)[0]
    assert stored.start_at == datetime(2026, 11, 23, 10, 0)
    assert stored.end_at == datetime(2026, 11, 23, 12, 0)


@pytest.mark.parametrize(
    "end_at",
    ["2026-11-23T10:00:00", "2026-11-23T09:00:00"],
    ids=["start_at == end_at", "end_at before start_at"],
)
def test_invalid_block_interval_returns_422(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    hall: Facility,
    db_session: Session,
    end_at: str,
) -> None:
    as_user(Role.ADMIN)

    response = client.post(
        f"/facilities/{hall.id}/blocks", json={**BLOCK, "end_at": end_at}
    )

    assert response.status_code == 422
    assert _block_rows(db_session, hall.id) == []


def test_student_cannot_add_block(
    client: TestClient, as_user: Callable[..., CurrentUser], hall: Facility
) -> None:
    as_user(Role.STUDENT)

    response = client.post(f"/facilities/{hall.id}/blocks", json=BLOCK)

    assert response.status_code == 403


def test_add_block_to_unknown_facility_returns_404(
    client: TestClient, as_user: Callable[..., CurrentUser]
) -> None:
    as_user(Role.ADMIN)

    response = client.post("/facilities/9999/blocks", json=BLOCK)

    assert response.status_code == 404
    assert response.json()["error"] == "NotFound"


# ---- GET /facilities/{id}/schedule?date= ----


@pytest.fixture
def scheduled_hall(db_session: Session, hall: Facility) -> Facility:
    """Main Hall open Monday 08:00-20:00, with one block on Mon 23 Nov and one on Tue 24 Nov."""
    db_session.add_all(
        [
            FacilityOperatingHours(
                facility_id=hall.id, weekday=0, opens_at=time(8, 0), closes_at=time(20, 0)
            ),
            FacilityBlock(
                facility_id=hall.id,
                start_at=datetime(2026, 11, 23, 10, 0),
                end_at=datetime(2026, 11, 23, 12, 0),
                reason="Projector repair",
            ),
            FacilityBlock(
                facility_id=hall.id,
                start_at=datetime(2026, 11, 24, 10, 0),
                end_at=datetime(2026, 11, 24, 12, 0),
                reason="Cleaning",
            ),
        ]
    )
    db_session.commit()
    return hall


def test_schedule_returns_that_days_hours_and_blocks(
    client: TestClient, as_user: Callable[..., CurrentUser], scheduled_hall: Facility
) -> None:
    as_user(Role.STUDENT)

    response = client.get(f"/facilities/{scheduled_hall.id}/schedule?date=2026-11-23")

    assert response.status_code == 200
    body = response.json()
    assert body["facility_id"] == scheduled_hall.id
    assert body["date"] == "2026-11-23"
    assert body["hours"] == {"opens_at": "08:00:00", "closes_at": "20:00:00"}
    assert [block["reason"] for block in body["blocks"]] == ["Projector repair"]


def test_schedule_on_a_closed_day_has_no_hours(
    client: TestClient, as_user: Callable[..., CurrentUser], scheduled_hall: Facility
) -> None:
    as_user(Role.STUDENT)

    response = client.get(f"/facilities/{scheduled_hall.id}/schedule?date=2026-11-24")

    assert response.status_code == 200
    body = response.json()
    assert body["hours"] is None
    assert [block["reason"] for block in body["blocks"]] == ["Cleaning"]


def test_schedule_for_unknown_facility_returns_404(
    client: TestClient, as_user: Callable[..., CurrentUser]
) -> None:
    as_user(Role.STUDENT)

    response = client.get("/facilities/9999/schedule?date=2026-11-23")

    assert response.status_code == 404


def test_schedule_without_date_returns_422(
    client: TestClient, as_user: Callable[..., CurrentUser], hall: Facility
) -> None:
    as_user(Role.STUDENT)

    response = client.get(f"/facilities/{hall.id}/schedule")

    assert response.status_code == 422


def test_schedule_without_authentication_returns_401(
    client: TestClient, hall: Facility
) -> None:
    response = client.get(f"/facilities/{hall.id}/schedule?date=2026-11-23")

    assert response.status_code == 401
