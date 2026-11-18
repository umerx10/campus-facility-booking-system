"""Imports every model so Base.metadata knows all 7 tables before they are created.

Models live in their owners' packages; this module is the one place that gathers them, which keeps
app.core.db free of imports from the feature modules (no circular imports).
"""

from sqlalchemy import Engine

from app.bookings.models import Booking, BookingHistory
from app.core.db import Base
from app.facilities.models import Facility, FacilityBlock, FacilityOperatingHours
from app.notifications.models import Notification
from app.users.models import User

__all__ = [
    "Booking",
    "BookingHistory",
    "Facility",
    "FacilityBlock",
    "FacilityOperatingHours",
    "Notification",
    "User",
    "create_all_tables",
]


def create_all_tables(bind: Engine) -> None:
    """Create any missing tables on the given engine."""
    Base.metadata.create_all(bind)
