
"""Role-based booking policies using the Strategy pattern (FR-06).

Each role has its own policy strategy instead of an if/elif chain
inside BookingService.

This follows the Open/Closed Principle (OCP), allowing new role
policies to be introduced without modifying booking logic.
"""

from datetime import datetime, timedelta

from app.core.deps import CurrentUser
from app.core.enums import Role
from app.core.exceptions import PolicyViolation
from app.core.interfaces import BookingPolicy, FacilityInfo


def _check_duration(
    start: datetime,
    end: datetime,
    limit: timedelta,
    label: str,
) -> None:
    """Raise PolicyViolation when a booking exceeds its duration limit."""
    if end - start > limit:
        hours = int(limit.total_seconds() / 3600)
        raise PolicyViolation(
            f"{label} may book at most {hours} h"
        )


class StudentPolicy:  # pylint: disable=too-few-public-methods
    """Strategy that limits student bookings to two hours."""

    def validate(
        self,
        user: CurrentUser,
        facility: FacilityInfo,
        start: datetime,
        end: datetime,
    ) -> None:
        """Validate the maximum student booking duration."""
        del user, facility  # Required by the shared BookingPolicy interface.
        _check_duration(
            start, end, timedelta(hours=2), "Students"
        )


class FacultyPolicy:  # pylint: disable=too-few-public-methods
    """Strategy that limits faculty bookings to four hours."""

    def validate(
        self,
        user: CurrentUser,
        facility: FacilityInfo,
        start: datetime,
        end: datetime,
    ) -> None:
        """Validate the maximum faculty booking duration."""
        del user, facility  # Required by the shared BookingPolicy interface.
        _check_duration(
            start, end, timedelta(hours=4), "Faculty"
        )


class AdminPolicy:  # pylint: disable=too-few-public-methods
    """Strategy allowing admins to book without a duration limit."""

    def validate(
        self,
        user: CurrentUser,
        facility: FacilityInfo,
        start: datetime,
        end: datetime,
    ) -> None:
        """Allow any duration; shared facility checks still apply."""
        del user, facility, start, end  # No duration rule for admins.


_POLICIES: dict[Role, BookingPolicy] = {
    Role.STUDENT: StudentPolicy(),
    Role.FACULTY: FacultyPolicy(),
    Role.ADMIN: AdminPolicy(),
}


def policy_for(role: Role) -> BookingPolicy:
    """Return the booking policy strategy corresponding to a role."""
    return _POLICIES[role]
