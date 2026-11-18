"""HTTP routes for Facility Management (FR-02, FR-03): validate, call a service, return a schema.

Every route needs an authenticated user; changes need the ADMIN role.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.deps import get_current_user, require_role
from app.core.enums import Role
from app.facilities.repository import FacilityRepository
from app.facilities.schemas import (
    BlockIn,
    BlockOut,
    DayHours,
    FacilityCreate,
    FacilityOut,
    FacilityUpdate,
    OperatingHoursIn,
    OperatingHoursOut,
    ScheduleOut,
)
from app.facilities.service import FacilityService

router = APIRouter(prefix="/facilities", tags=["facilities"])

ADMIN_ONLY = [Depends(require_role(Role.ADMIN))]
AUTHENTICATED = [Depends(get_current_user)]


def get_facility_service(session: Annotated[Session, Depends(get_session)]) -> FacilityService:
    """Build the service on the request's session."""
    return FacilityService(FacilityRepository(session))


FacilityServiceDep = Annotated[FacilityService, Depends(get_facility_service)]


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=ADMIN_ONLY)
def create_facility(body: FacilityCreate, service: FacilityServiceDep) -> FacilityOut:
    """Create a facility. Administrators only."""
    facility = service.create(body.name, body.capacity, body.requires_approval)
    return FacilityOut.model_validate(facility)


@router.get("", dependencies=AUTHENTICATED)
def list_facilities(service: FacilityServiceDep) -> list[FacilityOut]:
    """Return the active facilities."""
    return [FacilityOut.model_validate(facility) for facility in service.list_active()]


@router.get("/{facility_id}", dependencies=AUTHENTICATED)
def read_facility(facility_id: int, service: FacilityServiceDep) -> FacilityOut:
    """Return one facility, active or not."""
    return FacilityOut.model_validate(service.get(facility_id))


@router.patch("/{facility_id}", dependencies=ADMIN_ONLY)
def update_facility(
    facility_id: int, body: FacilityUpdate, service: FacilityServiceDep
) -> FacilityOut:
    """Change a facility's name, capacity or approval flag. Administrators only."""
    facility = service.update(facility_id, body.name, body.capacity, body.requires_approval)
    return FacilityOut.model_validate(facility)


@router.post("/{facility_id}/deactivate", dependencies=ADMIN_ONLY)
def deactivate_facility(facility_id: int, service: FacilityServiceDep) -> FacilityOut:
    """Take a facility out of service; it stays readable by id. Administrators only."""
    return FacilityOut.model_validate(service.deactivate(facility_id))


@router.put("/{facility_id}/hours", dependencies=ADMIN_ONLY)
def set_operating_hours(
    facility_id: int, body: list[OperatingHoursIn], service: FacilityServiceDep
) -> list[OperatingHoursOut]:
    """Replace the facility's weekly opening hours. Administrators only."""
    week = [(row.weekday, row.opens_at, row.closes_at) for row in body]
    return [OperatingHoursOut.model_validate(row) for row in service.set_hours(facility_id, week)]


@router.post("/{facility_id}/blocks", status_code=status.HTTP_201_CREATED, dependencies=ADMIN_ONLY)
def add_maintenance_block(
    facility_id: int, body: BlockIn, service: FacilityServiceDep
) -> BlockOut:
    """Block the facility for maintenance over [start_at, end_at). Administrators only."""
    block = service.add_block(facility_id, body.start_at, body.end_at, body.reason)
    return BlockOut.model_validate(block)


@router.get("/{facility_id}/schedule", dependencies=AUTHENTICATED)
def read_schedule(
    facility_id: int,
    day: Annotated[date, Query(alias="date")],
    service: FacilityServiceDep,
) -> ScheduleOut:
    """Return the facility's opening hours and maintenance blocks on one day (YYYY-MM-DD)."""
    hours, blocks = service.schedule(facility_id, day)
    return ScheduleOut(
        facility_id=facility_id,
        date=day,
        hours=DayHours.model_validate(hours) if hours is not None else None,
        blocks=[BlockOut.model_validate(block) for block in blocks],
    )
