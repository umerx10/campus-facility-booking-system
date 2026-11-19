"""Enumerations shared by every module. Values equal names, so they are stored as plain strings."""

from enum import StrEnum


class Role(StrEnum):
    """User roles from FR-01."""

    STUDENT = "STUDENT"
    FACULTY = "FACULTY"
    ADMIN = "ADMIN"


class BookingStatus(StrEnum):
    """Booking life cycle states (FR-09)."""

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
