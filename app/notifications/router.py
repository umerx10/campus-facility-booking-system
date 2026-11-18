"""HTTP routes for Notifications (FR-10). Endpoints are added by the module owner."""

from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["notifications"])
