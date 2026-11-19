"""Unit tests for BookingService.request_booking (FR-04, FR-05, FR-06, FR-08), with fakes.

The clock is fixed at Monday 23 Nov 2026 08:00 (naive UTC). Intervals are half-open [start, end).
"""

from datetime import datetime

import pytest

from app.bookings.service import BookingService
from app.core.deps import CurrentUser
from app.core.enums import BookingStatus, Role
from app.core.events import BookingCancelled, BookingConfirmed, BookingRejected
from app.core.exceptions import (
    BookingConflict,
    FacilityUnavailable,
    InvalidBookingTime,
    NotFound,
    PolicyViolation,
)
from app.core.interfaces import FacilityInfo
from tests.bookings.fakes import (
    FakeLookup,
    FakePolicy,
    FakePublisher,
    FakeStore,
    RecordingPolicyFor,
)

NOW = datetime(2026, 11, 23, 8, 0)
STUDENT = CurrentUser(id=7, role=Role.STUDENT)
LAB = FacilityInfo(id=1, capacity=30, requires_approval=False, active=True)
HALL = FacilityInfo(id=2, capacity=300, requires_approval=True, active=True)
CLOSED_ROOM = FacilityInfo(id=3, capacity=10, requires_approval=False, active=False)


def at(hour: int, minute: int = 0) -> datetime:
    """A time on Monday 23 Nov 2026."""
    return datetime(2026, 11, 23, hour, minute)


class Env:
    """A BookingService wired to fakes, with the fakes exposed for assertions."""

    def __init__(self) -> None:
        self.log: list[str] = []
        self.store = FakeStore(self.log)
        self.lookup = FakeLookup([LAB, HALL, CLOSED_ROOM])
        self.policy = FakePolicy()
        self.policy_for = RecordingPolicyFor(self.policy)
        self.publisher = FakePublisher(self.log)
        self.service = BookingService(
            repository=self.store,
            facilities=self.lookup,
            policy_for=self.policy_for,
            publisher=self.publisher,
            now=lambda: NOW,
        )


@pytest.fixture
def env() -> Env:
    return Env()


# ---- interval checks (FR-04) ----


@pytest.mark.parametrize(
    ("start", "end"),
    [(at(11), at(10)), (at(10), at(10))],
    ids=["end before start", "end == start"],
)
def test_end_not_after_start_is_invalid(env: Env, start: datetime, end: datetime) -> None:
    with pytest.raises(InvalidBookingTime):
        env.service.request_booking(STUDENT, LAB.id, start, end)

    assert env.store.bookings == {}


def test_start_in_the_past_is_invalid(env: Env) -> None:
    with pytest.raises(InvalidBookingTime):
        env.service.request_booking(STUDENT, LAB.id, at(7, 59), at(9))

    assert env.store.bookings == {}


# ---- facility checks (FR-03, FR-05) ----


def test_unknown_facility_raises_not_found(env: Env) -> None:
    with pytest.raises(NotFound):
        env.service.request_booking(STUDENT, 99, at(10), at(11))


def test_inactive_facility_is_unavailable(env: Env) -> None:
    with pytest.raises(FacilityUnavailable):
        env.service.request_booking(STUDENT, CLOSED_ROOM.id, at(10), at(11))


def test_outside_operating_hours_is_unavailable(env: Env) -> None:
    env.lookup.open = False

    with pytest.raises(FacilityUnavailable):
        env.service.request_booking(STUDENT, LAB.id, at(10), at(11))

    assert env.store.bookings == {}


def test_overlapping_a_maintenance_block_is_unavailable(env: Env) -> None:
    env.lookup.blocked = True

    with pytest.raises(FacilityUnavailable):
        env.service.request_booking(STUDENT, LAB.id, at(10), at(11))

    assert env.store.bookings == {}


# ---- role policy (FR-06) ----


def test_policy_for_the_users_role_is_called(env: Env) -> None:
    env.service.request_booking(STUDENT, LAB.id, at(10), at(11))

    assert env.policy_for.roles == [Role.STUDENT]
    assert env.policy.calls == [(STUDENT, LAB, at(10), at(11))]


def test_policy_violation_propagates_and_nothing_is_stored(env: Env) -> None:
    env.policy.violation = "Students may book at most 2 h"

    with pytest.raises(PolicyViolation):
        env.service.request_booking(STUDENT, LAB.id, at(10), at(13))

    assert env.store.bookings == {}
    assert env.publisher.events == []


# ---- non-restricted facility (FR-04, FR-05, FR-09) ----


def test_free_slot_is_confirmed_with_history_and_event_after_commit(env: Env) -> None:
    booking = env.service.request_booking(STUDENT, LAB.id, at(10), at(11))

    assert booking.status == BookingStatus.CONFIRMED
    assert (booking.user_id, booking.facility_id) == (STUDENT.id, LAB.id)
    assert (booking.start_at, booking.end_at) == (at(10), at(11))
    assert [(h.old_status, h.new_status, h.actor_id, h.changed_at) for h in env.store.history] == [
        (None, BookingStatus.CONFIRMED, STUDENT.id, NOW)
    ]
    assert env.publisher.events == [
        BookingConfirmed(
            booking_id=booking.id, user_id=STUDENT.id, facility_id=LAB.id, occurred_at=NOW
        )
    ]
    assert env.log == ["commit", "publish:BookingConfirmed"]


def test_overlapping_a_confirmed_booking_conflicts_and_publishes_nothing(env: Env) -> None:
    env.service.request_booking(STUDENT, LAB.id, at(10), at(12))
    env.log.clear()
    env.publisher.events.clear()
    other = CurrentUser(id=8, role=Role.FACULTY)

    with pytest.raises(BookingConflict):
        env.service.request_booking(other, LAB.id, at(11, 59), at(13))

    assert len(env.store.bookings) == 1
    assert env.publisher.events == []
    assert env.log == []


def test_back_to_back_with_a_confirmed_booking_is_allowed(env: Env) -> None:
    env.service.request_booking(STUDENT, LAB.id, at(10), at(12))
    other = CurrentUser(id=8, role=Role.FACULTY)

    booking = env.service.request_booking(other, LAB.id, at(12), at(13))

    assert booking.status == BookingStatus.CONFIRMED


# ---- restricted facility (FR-08) ----


def test_restricted_facility_creates_pending_with_history_and_no_event(env: Env) -> None:
    booking = env.service.request_booking(STUDENT, HALL.id, at(10), at(11))

    assert booking.status == BookingStatus.PENDING
    assert [(h.old_status, h.new_status, h.actor_id) for h in env.store.history] == [
        (None, BookingStatus.PENDING, STUDENT.id)
    ]
    assert env.publisher.events == []
    assert env.log == ["commit"]


def test_pending_requests_do_not_reserve_the_slot(env: Env) -> None:
    first = env.service.request_booking(STUDENT, HALL.id, at(10), at(11))
    other = CurrentUser(id=8, role=Role.FACULTY)

    second = env.service.request_booking(other, HALL.id, at(10), at(11))

    assert (first.status, second.status) == (BookingStatus.PENDING, BookingStatus.PENDING)


# ======== Step 3: cancellation, approval decisions (FR-07, FR-08, FR-09) ========

ADMIN = CurrentUser(id=1, role=Role.ADMIN)
OTHER_STUDENT = CurrentUser(id=8, role=Role.STUDENT)


def _reset_records(env: Env) -> None:
    env.log.clear()
    env.publisher.events.clear()
    env.store.history.clear()


# ---- cancel ----


@pytest.mark.parametrize("facility", [LAB, HALL], ids=["confirmed", "pending"])
def test_owner_cancels_own_booking_with_history_and_event_after_commit(
    env: Env, facility: FacilityInfo
) -> None:
    booking = env.service.request_booking(STUDENT, facility.id, at(10), at(11))
    old_status = booking.status
    _reset_records(env)

    cancelled = env.service.cancel(booking.id, STUDENT)

    assert cancelled.status == BookingStatus.CANCELLED
    assert [(h.old_status, h.new_status, h.actor_id) for h in env.store.history] == [
        (old_status, BookingStatus.CANCELLED, STUDENT.id)
    ]
    assert env.publisher.events == [
        BookingCancelled(
            booking_id=booking.id, user_id=STUDENT.id, facility_id=facility.id, occurred_at=NOW
        )
    ]
    assert env.log == ["commit", "publish:BookingCancelled"]


def test_cancelling_another_users_booking_looks_like_not_found(env: Env) -> None:
    booking = env.service.request_booking(STUDENT, LAB.id, at(10), at(11))
    _reset_records(env)

    with pytest.raises(NotFound):
        env.service.cancel(booking.id, OTHER_STUDENT)

    assert booking.status == BookingStatus.CONFIRMED
    assert env.publisher.events == []


def test_admin_may_cancel_any_booking(env: Env) -> None:
    booking = env.service.request_booking(STUDENT, LAB.id, at(10), at(11))
    _reset_records(env)

    cancelled = env.service.cancel(booking.id, ADMIN)

    assert cancelled.status == BookingStatus.CANCELLED
    assert env.store.history[0].actor_id == ADMIN.id


def test_cancelling_an_unknown_booking_raises_not_found(env: Env) -> None:
    with pytest.raises(NotFound):
        env.service.cancel(999, ADMIN)


@pytest.mark.parametrize("status", [BookingStatus.CANCELLED, BookingStatus.REJECTED])
def test_cancelling_a_closed_booking_conflicts(env: Env, status: BookingStatus) -> None:
    booking = env.service.request_booking(STUDENT, LAB.id, at(10), at(11))
    booking.status = status
    _reset_records(env)

    with pytest.raises(BookingConflict):
        env.service.cancel(booking.id, STUDENT)

    assert booking.status == status
    assert env.store.history == []
    assert env.publisher.events == []


# ---- confirm_pending ----


def test_confirm_pending_confirms_with_history_and_event_after_commit(env: Env) -> None:
    booking = env.service.request_booking(STUDENT, HALL.id, at(10), at(11))
    _reset_records(env)

    confirmed = env.service.confirm_pending(booking.id, ADMIN)

    assert confirmed.status == BookingStatus.CONFIRMED
    assert [(h.old_status, h.new_status, h.actor_id) for h in env.store.history] == [
        (BookingStatus.PENDING, BookingStatus.CONFIRMED, ADMIN.id)
    ]
    assert env.publisher.events == [
        BookingConfirmed(
            booking_id=booking.id, user_id=STUDENT.id, facility_id=HALL.id, occurred_at=NOW
        )
    ]
    assert env.log == ["commit", "publish:BookingConfirmed"]


def test_confirm_pending_that_now_overlaps_a_confirmed_booking_conflicts(env: Env) -> None:
    first = env.service.request_booking(STUDENT, HALL.id, at(10), at(12))
    second = env.service.request_booking(OTHER_STUDENT, HALL.id, at(11), at(13))
    env.service.confirm_pending(first.id, ADMIN)
    _reset_records(env)

    with pytest.raises(BookingConflict):
        env.service.confirm_pending(second.id, ADMIN)

    assert second.status == BookingStatus.PENDING
    assert env.store.history == []
    assert env.publisher.events == []


def test_confirm_pending_on_a_deactivated_facility_is_unavailable(env: Env) -> None:
    booking = env.service.request_booking(STUDENT, HALL.id, at(10), at(11))
    env.lookup.facilities[HALL.id] = FacilityInfo(
        id=HALL.id, capacity=300, requires_approval=True, active=False
    )

    with pytest.raises(FacilityUnavailable):
        env.service.confirm_pending(booking.id, ADMIN)

    assert booking.status == BookingStatus.PENDING


def test_confirm_pending_on_a_blocked_facility_is_unavailable(env: Env) -> None:
    booking = env.service.request_booking(STUDENT, HALL.id, at(10), at(11))
    env.lookup.blocked = True

    with pytest.raises(FacilityUnavailable):
        env.service.confirm_pending(booking.id, ADMIN)

    assert booking.status == BookingStatus.PENDING


def test_confirm_a_booking_that_is_not_pending_conflicts(env: Env) -> None:
    booking = env.service.request_booking(STUDENT, LAB.id, at(10), at(11))

    with pytest.raises(BookingConflict):
        env.service.confirm_pending(booking.id, ADMIN)


def test_confirm_an_unknown_booking_raises_not_found(env: Env) -> None:
    with pytest.raises(NotFound):
        env.service.confirm_pending(999, ADMIN)


# ---- reject_pending ----


def test_reject_pending_rejects_with_history_and_event_after_commit(env: Env) -> None:
    booking = env.service.request_booking(STUDENT, HALL.id, at(10), at(11))
    _reset_records(env)

    rejected = env.service.reject_pending(booking.id, ADMIN)

    assert rejected.status == BookingStatus.REJECTED
    assert [(h.old_status, h.new_status, h.actor_id) for h in env.store.history] == [
        (BookingStatus.PENDING, BookingStatus.REJECTED, ADMIN.id)
    ]
    assert env.publisher.events == [
        BookingRejected(
            booking_id=booking.id, user_id=STUDENT.id, facility_id=HALL.id, occurred_at=NOW
        )
    ]
    assert env.log == ["commit", "publish:BookingRejected"]


def test_reject_a_booking_that_is_not_pending_conflicts(env: Env) -> None:
    booking = env.service.request_booking(STUDENT, LAB.id, at(10), at(11))

    with pytest.raises(BookingConflict):
        env.service.reject_pending(booking.id, ADMIN)

    assert booking.status == BookingStatus.CONFIRMED


# ---- list_pending ----


def test_list_pending_returns_only_pending_bookings(env: Env) -> None:
    pending = env.service.request_booking(STUDENT, HALL.id, at(10), at(11))
    env.service.request_booking(STUDENT, LAB.id, at(10), at(11))

    assert [b.id for b in env.service.list_pending()] == [pending.id]
