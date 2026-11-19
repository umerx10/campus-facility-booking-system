"""API tests for facility management (FR-02).

Validation cases are boundary values (BVA) on the two numeric/length inputs:
name length 0 (invalid), 1 and 100 (valid), 101 (invalid); capacity 0 and -1 (invalid), 1 (valid).
"""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.core.enums import Role
from app.facilities.models import Facility

NEW_FACILITY = {"name": "Seminar Room A", "capacity": 40, "requires_approval": False}


@pytest.fixture
def facilities(db_session: Session) -> dict[str, Facility]:
    """One active lab, one active restricted hall and one inactive room."""
    lab = Facility(name="Computer Lab 1", capacity=30, requires_approval=False, active=True)
    hall = Facility(name="Main Auditorium", capacity=300, requires_approval=True, active=True)
    old = Facility(name="Old Store Room", capacity=5, requires_approval=False, active=False)
    db_session.add_all([lab, hall, old])
    db_session.commit()
    return {"lab": lab, "hall": hall, "old": old}


def _facility_count(db_session: Session) -> int:
    return db_session.scalar(select(func.count()).select_from(Facility)) or 0


# ---- create (POST /facilities) ----


def test_admin_creates_facility_returns_201_with_id(
    client: TestClient, as_user: Callable[..., CurrentUser], db_session: Session
) -> None:
    as_user(Role.ADMIN)

    response = client.post("/facilities", json=NEW_FACILITY)

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["name"] == "Seminar Room A"
    assert body["capacity"] == 40
    assert body["requires_approval"] is False
    assert body["active"] is True
    stored = db_session.get(Facility, body["id"])
    assert stored is not None
    assert stored.name == "Seminar Room A"


def test_requires_approval_defaults_to_false(
    client: TestClient, as_user: Callable[..., CurrentUser]
) -> None:
    as_user(Role.ADMIN)

    response = client.post("/facilities", json={"name": "Room B", "capacity": 10})

    assert response.status_code == 201
    assert response.json()["requires_approval"] is False


@pytest.mark.parametrize("role", [Role.STUDENT, Role.FACULTY])
def test_non_admin_cannot_create_facility(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    db_session: Session,
    role: Role,
) -> None:
    as_user(role)

    response = client.post("/facilities", json=NEW_FACILITY)

    assert response.status_code == 403
    assert response.json()["error"] == "UnauthorizedOperation"
    assert _facility_count(db_session) == 0


@pytest.mark.parametrize(
    ("payload", "case"),
    [
        ({"name": "", "capacity": 10}, "empty name (length 0)"),
        ({"name": "x" * 101, "capacity": 10}, "name length 101"),
        ({"name": "Room", "capacity": 0}, "capacity 0"),
        ({"name": "Room", "capacity": -5}, "negative capacity"),
        ({"capacity": 10}, "missing name"),
        ({"name": "Room"}, "missing capacity"),
    ],
)
def test_invalid_facility_input_returns_422(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    db_session: Session,
    payload: dict[str, object],
    case: str,
) -> None:
    as_user(Role.ADMIN)

    response = client.post("/facilities", json=payload)

    assert response.status_code == 422, case
    assert _facility_count(db_session) == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "x", "capacity": 10},
        {"name": "x" * 100, "capacity": 10},
        {"name": "Room", "capacity": 1},
    ],
    ids=["name length 1", "name length 100", "capacity 1"],
)
def test_boundary_valid_facility_input_is_accepted(
    client: TestClient, as_user: Callable[..., CurrentUser], payload: dict[str, object]
) -> None:
    as_user(Role.ADMIN)

    response = client.post("/facilities", json=payload)

    assert response.status_code == 201


# ---- read (GET /facilities, GET /facilities/{id}) ----


@pytest.mark.parametrize("role", [Role.STUDENT, Role.FACULTY, Role.ADMIN])
def test_list_returns_only_active_facilities(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    facilities: dict[str, Facility],
    role: Role,
) -> None:
    as_user(role)

    response = client.get("/facilities")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert ids == {facilities["lab"].id, facilities["hall"].id}


def test_get_facility_by_id(
    client: TestClient, as_user: Callable[..., CurrentUser], facilities: dict[str, Facility]
) -> None:
    as_user(Role.STUDENT)

    response = client.get(f"/facilities/{facilities['hall'].id}")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Main Auditorium"
    assert body["capacity"] == 300
    assert body["requires_approval"] is True
    assert body["active"] is True


@pytest.mark.usefixtures("facilities")
def test_get_unknown_facility_returns_404(
    client: TestClient, as_user: Callable[..., CurrentUser]
) -> None:
    as_user(Role.STUDENT)

    response = client.get("/facilities/9999")

    assert response.status_code == 404
    assert response.json()["error"] == "NotFound"


# ---- update (PATCH /facilities/{id}) ----


def test_admin_updates_facility_fields(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    facilities: dict[str, Facility],
    db_session: Session,
) -> None:
    as_user(Role.ADMIN)
    lab_id = facilities["lab"].id

    response = client.patch(
        f"/facilities/{lab_id}",
        json={"name": "Computer Lab 1 (renovated)", "capacity": 35, "requires_approval": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Computer Lab 1 (renovated)"
    assert body["capacity"] == 35
    assert body["requires_approval"] is True
    db_session.refresh(facilities["lab"])
    assert facilities["lab"].capacity == 35


def test_partial_update_keeps_other_fields(
    client: TestClient, as_user: Callable[..., CurrentUser], facilities: dict[str, Facility]
) -> None:
    as_user(Role.ADMIN)

    response = client.patch(f"/facilities/{facilities['lab'].id}", json={"capacity": 25})

    assert response.status_code == 200
    body = response.json()
    assert body["capacity"] == 25
    assert body["name"] == "Computer Lab 1"
    assert body["requires_approval"] is False


def test_update_with_invalid_capacity_returns_422(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    facilities: dict[str, Facility],
    db_session: Session,
) -> None:
    as_user(Role.ADMIN)

    response = client.patch(f"/facilities/{facilities['lab'].id}", json={"capacity": 0})

    assert response.status_code == 422
    db_session.refresh(facilities["lab"])
    assert facilities["lab"].capacity == 30


def test_student_cannot_update_facility(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    facilities: dict[str, Facility],
    db_session: Session,
) -> None:
    as_user(Role.STUDENT)

    response = client.patch(f"/facilities/{facilities['lab'].id}", json={"capacity": 99})

    assert response.status_code == 403
    db_session.refresh(facilities["lab"])
    assert facilities["lab"].capacity == 30


@pytest.mark.usefixtures("facilities")
def test_update_unknown_facility_returns_404(
    client: TestClient, as_user: Callable[..., CurrentUser]
) -> None:
    as_user(Role.ADMIN)

    response = client.patch("/facilities/9999", json={"capacity": 10})

    assert response.status_code == 404
    assert response.json()["error"] == "NotFound"


# ---- deactivate (POST /facilities/{id}/deactivate) ----


def test_admin_deactivates_facility_still_readable_but_not_listed(
    client: TestClient, as_user: Callable[..., CurrentUser], facilities: dict[str, Facility]
) -> None:
    as_user(Role.ADMIN)
    lab_id = facilities["lab"].id

    response = client.post(f"/facilities/{lab_id}/deactivate")

    assert response.status_code == 200
    assert response.json()["active"] is False
    by_id = client.get(f"/facilities/{lab_id}")
    assert by_id.status_code == 200
    assert by_id.json()["active"] is False
    listed = {item["id"] for item in client.get("/facilities").json()}
    assert lab_id not in listed


def test_student_cannot_deactivate_facility(
    client: TestClient,
    as_user: Callable[..., CurrentUser],
    facilities: dict[str, Facility],
    db_session: Session,
) -> None:
    as_user(Role.STUDENT)

    response = client.post(f"/facilities/{facilities['lab'].id}/deactivate")

    assert response.status_code == 403
    db_session.refresh(facilities["lab"])
    assert facilities["lab"].active is True


@pytest.mark.usefixtures("facilities")
def test_deactivate_unknown_facility_returns_404(
    client: TestClient, as_user: Callable[..., CurrentUser]
) -> None:
    as_user(Role.ADMIN)

    response = client.post("/facilities/9999/deactivate")

    assert response.status_code == 404
    assert response.json()["error"] == "NotFound"


# ---- authentication ----


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/facilities"), ("get", "/facilities/1"), ("post", "/facilities")],
)
def test_requests_without_authentication_return_401(
    client: TestClient, method: str, path: str
) -> None:
    response = client.request(method.upper(), path, json=NEW_FACILITY)

    assert response.status_code == 401
    assert response.json()["error"] == "AuthenticationFailed"
