
"""Tests for role-based booking policies (FR-06, Strategy pattern)."""

from datetime import datetime, timedelta

import pytest

from app.approvals.policies import (
    AdminPolicy,
    FacultyPolicy,
    StudentPolicy,
    policy_for,
)
from app.core.deps import CurrentUser
from app.core.enums import Role
from app.core.exceptions import PolicyViolation
from app.core.interfaces import BookingPolicy, FacilityInfo


START = datetime(2026, 11, 20, 10, 0)
FACILITY = FacilityInfo(
    id=1,
    capacity=30,
    requires_approval=False,
    active=True,
)


def user_for(role: Role) -> CurrentUser:
    """Create a user with the specified role."""
    return CurrentUser(id=1, role=role)


@pytest.mark.parametrize("minutes", [119, 120])
def test_student_accepts_allowed_duration(minutes: int) -> None:
    """Students can book for up to two hours."""
    StudentPolicy().validate(
        user_for(Role.STUDENT),
        FACILITY,
        START,
        START + timedelta(minutes=minutes),
    )


def test_student_rejects_121_minutes() -> None:
    """Students cannot exceed the two-hour limit."""
    with pytest.raises(PolicyViolation, match=r"2\s*h"):
        StudentPolicy().validate(
            user_for(Role.STUDENT),
            FACILITY,
            START,
            START + timedelta(minutes=121),
        )


@pytest.mark.parametrize("minutes", [239, 240])
def test_faculty_accepts_allowed_duration(minutes: int) -> None:
    """Faculty can book for up to four hours."""
    FacultyPolicy().validate(
        user_for(Role.FACULTY),
        FACILITY,
        START,
        START + timedelta(minutes=minutes),
    )


def test_faculty_rejects_241_minutes() -> None:
    """Faculty cannot exceed the four-hour limit."""
    with pytest.raises(PolicyViolation, match=r"4\s*h"):
        FacultyPolicy().validate(
            user_for(Role.FACULTY),
            FACILITY,
            START,
            START + timedelta(minutes=241),
        )


def test_admin_accepts_ten_hours() -> None:
    """Admins have no duration cap."""
    AdminPolicy().validate(
        user_for(Role.ADMIN),
        FACILITY,
        START,
        START + timedelta(hours=10),
    )


@pytest.mark.parametrize(
    ("role", "expected_policy"),
    [
        (Role.STUDENT, StudentPolicy),
        (Role.FACULTY, FacultyPolicy),
        (Role.ADMIN, AdminPolicy),
    ],
)
def test_policy_factory_selects_correct_strategy(
    role: Role, expected_policy: type
) -> None:
    """Factory selects the correct policy for each role."""
    assert isinstance(policy_for(role), expected_policy)


@pytest.mark.parametrize(
    ("policy_class", "role"),
    [
        (StudentPolicy, Role.STUDENT),
        (FacultyPolicy, Role.FACULTY),
        (AdminPolicy, Role.ADMIN),
    ],
)
def test_each_policy_satisfies_booking_policy(
    policy_class: type, role: Role
) -> None:
    """Every strategy implements the same BookingPolicy contract."""
    policy = policy_class()
    assert isinstance(policy, BookingPolicy)
    policy.validate(
        user_for(role),
        FACILITY,
        START,
        START + timedelta(minutes=30),
    )
