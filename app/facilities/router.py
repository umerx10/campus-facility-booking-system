"""HTTP routes for Facility Management (FR-02): validate input, call a service, return a schema.

Every route needs an authenticated user; changes need the ADMIN role.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.core.deps import get_current_user, require_role
from app.core.enums import Role
from app.facilities.repository import FacilityRepository
from app.facilities.schemas import FacilityCreate, FacilityOut, FacilityUpdate
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
