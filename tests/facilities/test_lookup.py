"""Tests for SqlFacilityLookup, the FacilityLookup implementation used by Booking (FR-03).

Boundary values (BVA): the facility is open Monday 08:00-20:00 and has a maintenance block on
Monday 23 Nov 2026 [10:00, 12:00). Intervals are half-open, so back-to-back is not an overlap.
"""

from datetime import datetime, time

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFound
from app.core.interfaces import FacilityInfo
from app.facilities.lookup import SqlFacilityLookup
from app.facilities.models import Facility, FacilityBlock, FacilityOperatingHours

MONDAY = 0


def _at(hour: int, minute: int = 0, day: int = 23) -> datetime:
    """A naive UTC datetime in the week of Monday 23 Nov 2026 (day 24 is Tuesday)."""
    return datetime(2026, 11, day, hour, minute)


@pytest.fixture
def facilities(db_session: Session) -> dict[str, Facility]:
    """A restricted hall open Monday 08:00-20:00 with a Monday block, and a second room."""
    hall = Facility(name="Main Hall", capacity=200, requires_approval=True, active=True)
    room = Facility(name="Room 2", capacity=20, requires_approval=False, active=False)
    db_session.add_all([hall, room])
    db_session.flush()
    db_session.add_all(
        [
            FacilityOperatingHours(
                facility_id=hall.id, weekday=MONDAY, opens_at=time(8, 0), closes_at=time(20, 0)
            ),
            FacilityBlock(
                facility_id=hall.id, start_at=_at(10), end_at=_at(12), reason="Projector repair"
            ),
        ]
    )
    db_session.commit()
    return {"hall": hall, "room": room}


@pytest.fixture
def lookup(db_session: Session) -> SqlFacilityLookup:
    """The lookup on the test session."""
    return SqlFacilityLookup(db_session)


# ---- get_facility ----


def test_get_facility_returns_facility_info(
    lookup: SqlFacilityLookup, facilities: dict[str, Facility]
) -> None:
    hall = facilities["hall"]

    info = lookup.get_facility(hall.id)

    assert info == FacilityInfo(id=hall.id, capacity=200, requires_approval=True, active=True)


def test_get_facility_returns_inactive_facility(
    lookup: SqlFacilityLookup, facilities: dict[str, Facility]
) -> None:
    info = lookup.get_facility(facilities["room"].id)

    assert info.active is False


@pytest.mark.usefixtures("facilities")
def test_get_unknown_facility_raises_not_found(lookup: SqlFacilityLookup) -> None:
    with pytest.raises(NotFound):
        lookup.get_facility(9999)


# ---- is_within_hours (BVA on opens_at / closes_at) ----


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (_at(8, 0), _at(9, 0), True),
        (_at(7, 59), _at(9, 0), False),
        (_at(19, 0), _at(20, 0), True),
        (_at(19, 0), _at(20, 1), False),
        (_at(9, 0, day=24), _at(10, 0, day=24), False),
        (_at(19, 0), _at(9, 0, day=24), False),
    ],
    ids=[
        "start == opens_at",
        "start one minute before opening",
        "end == closes_at",
        "end one minute after closing",
        "no hours row for that weekday",
        "start and end on different days",
    ],
)
def test_is_within_hours(
    lookup: SqlFacilityLookup,
    facilities: dict[str, Facility],
    start: datetime,
    end: datetime,
    expected: bool,
) -> None:
    assert lookup.is_within_hours(facilities["hall"].id, start, end) is expected


# ---- overlaps_block (half-open [start, end)) ----


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (_at(12, 0), _at(13, 0), False),
        (_at(9, 0), _at(10, 0), False),
        (_at(11, 59), _at(12, 30), True),
        (_at(9, 0), _at(13, 0), True),
    ],
    ids=[
        "back to back after the block",
        "back to back before the block",
        "starts one minute before the block ends",
        "contains the block",
    ],
)
def test_overlaps_block(
    lookup: SqlFacilityLookup,
    facilities: dict[str, Facility],
    start: datetime,
    end: datetime,
    expected: bool,
) -> None:
    assert lookup.overlaps_block(facilities["hall"].id, start, end) is expected


def test_block_on_another_facility_does_not_overlap(
    lookup: SqlFacilityLookup, facilities: dict[str, Facility]
) -> None:
    assert lookup.overlaps_block(facilities["room"].id, _at(10), _at(11)) is False
