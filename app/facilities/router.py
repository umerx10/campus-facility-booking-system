"""HTTP routes for Facility Management (FR-02, FR-03). Endpoints are added by the module owner."""

from fastapi import APIRouter

router = APIRouter(prefix="/facilities", tags=["facilities"])
