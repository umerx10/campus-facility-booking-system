"""Tests for the shared skeleton: health route, schema, error mapping, roles, concurrency recipe."""

import logging
import sqlite3
from collections.abc import Callable, Iterator
from typing import Annotated, Any

import pytest
from fastapi import Depends
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.core.db import Base
from app.core.deps import CurrentUser, get_current_user, require_role
from app.core.enums import Role
from app.core.exceptions import (
    AuthenticationFailed,
    BookingConflict,
    DomainError,
    FacilityUnavailable,
    InvalidBookingTime,
    NotFound,
    PolicyViolation,
    UnauthorizedOperation,
)
from app.main import app

M1_TABLES = {
    "users",
    "facilities",
    "facility_operating_hours",
    "bookings",
    "facility_blocks",
    "booking_history",
    "notifications",
}


@pytest.fixture
def add_route() -> Iterator[Callable[..., None]]:
    """Register throwaway GET routes on the app and remove them after the test."""
    added: list[APIRoute] = []

    def _add(path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        app.add_api_route(path, endpoint, methods=["GET"], **kwargs)
        added.append(app.router.routes[-1])

    yield _add
    for route in added:
        app.router.routes.remove(route)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metadata_has_exactly_the_seven_m1_tables() -> None:
    assert set(Base.metadata.tables) == M1_TABLES


@pytest.mark.parametrize(
    ("error_cls", "expected_status"),
    [
        (NotFound, 404),
        (InvalidBookingTime, 422),
        (FacilityUnavailable, 409),
        (BookingConflict, 409),
        (PolicyViolation, 422),
        (UnauthorizedOperation, 403),
        (AuthenticationFailed, 401),
    ],
)
def test_domain_error_maps_to_http_status(
    client: TestClient,
    add_route: Callable[..., None],
    error_cls: type[DomainError],
    expected_status: int,
) -> None:
    def _raise() -> None:
        raise error_cls("something went wrong")

    add_route("/_test/raise", _raise)

    response = client.get("/_test/raise")

    assert issubclass(error_cls, DomainError)
    assert response.status_code == expected_status
    assert response.json() == {"error": error_cls.__name__, "detail": "something went wrong"}


def test_domain_error_is_logged_at_warning(
    client: TestClient, add_route: Callable[..., None], caplog: pytest.LogCaptureFixture
) -> None:
    def _raise() -> None:
        raise NotFound("booking 42 not found")

    add_route("/_test/raise", _raise)

    with caplog.at_level(logging.WARNING):
        client.get("/_test/raise")

    warnings = [r for r in caplog.records if r.name == "app.main" and r.levelno == logging.WARNING]
    assert warnings, "the DomainError handler in app.main must log at WARNING"


def _admin_only() -> dict[str, bool]:
    return {"ok": True}


def test_require_role_denies_a_student(
    client: TestClient, add_route: Callable[..., None], as_user: Callable[..., CurrentUser]
) -> None:
    add_route("/_test/admin-only", _admin_only, dependencies=[Depends(require_role(Role.ADMIN))])
    as_user(Role.STUDENT)

    response = client.get("/_test/admin-only")

    assert response.status_code == 403
    assert response.json()["error"] == "UnauthorizedOperation"


def test_require_role_allows_an_admin(
    client: TestClient, add_route: Callable[..., None], as_user: Callable[..., CurrentUser]
) -> None:
    add_route("/_test/admin-only", _admin_only, dependencies=[Depends(require_role(Role.ADMIN))])
    as_user(Role.ADMIN)

    response = client.get("/_test/admin-only")

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def _whoami(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, int]:
    return {"id": user.id}


def test_request_without_identity_returns_401(
    client: TestClient, add_route: Callable[..., None]
) -> None:
    add_route("/_test/whoami", _whoami)

    response = client.get("/_test/whoami")

    assert response.status_code == 401
    assert response.json()["error"] == "AuthenticationFailed"


def test_begin_starts_a_transaction_before_any_query(file_engine: Engine) -> None:
    """Default pysqlite delays BEGIN until the first write; the recipe must start it on begin()."""
    with file_engine.connect() as conn:
        conn.begin()
        raw = conn.connection.dbapi_connection

        assert raw is not None
        assert raw.in_transaction is True


def test_open_transaction_already_holds_the_write_lock(file_engine: Engine) -> None:
    """BEGIN IMMEDIATE takes the write lock at begin(), so a second writer is refused at once."""
    db_path = file_engine.url.database
    assert db_path is not None

    with file_engine.connect() as conn:
        conn.begin()
        other = sqlite3.connect(db_path, timeout=0, isolation_level=None)
        try:
            with pytest.raises(sqlite3.OperationalError, match="locked"):
                other.execute("BEGIN IMMEDIATE")
        finally:
            other.close()
