"""HTTP routes for Approval and Policies (FR-06, FR-08). Endpoints are added by the module owner."""

from fastapi import APIRouter

router = APIRouter(prefix="/approvals", tags=["approvals"])
