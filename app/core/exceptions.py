"""Domain errors. Services raise these; one handler in app.main turns them into HTTP responses.

Each class carries its HTTP status in `status_code`, so the handler needs no if/else chain and a new
error type needs no change to the handler.
"""


class DomainError(Exception):
    """Base class for every business-rule failure in CFBS."""

    status_code: int = 400


class NotFound(DomainError):
    """The requested record does not exist, or the caller may not see it."""

    status_code = 404


class InvalidBookingTime(DomainError):
    """The booking interval is malformed (for example, end is not after start)."""

    status_code = 422


class FacilityUnavailable(DomainError):
    """The facility is inactive, closed at that time, or blocked for maintenance."""

    status_code = 409


class BookingConflict(DomainError):
    """The interval overlaps a confirmed booking (FR-05)."""

    status_code = 409


class PolicyViolation(DomainError):
    """A role policy rejects the request, for example a duration limit (FR-06)."""

    status_code = 422


class UnauthorizedOperation(DomainError):
    """The caller is authenticated but their role may not do this."""

    status_code = 403


class AuthenticationFailed(DomainError):
    """The caller could not be identified: missing, invalid or expired credentials."""

    status_code = 401
