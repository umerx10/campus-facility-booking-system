"""HTTP routes for User and Access (FR-01). Endpoints are added by the module owner."""

from fastapi import APIRouter

# No prefix: this module serves both /auth/... and /users/... paths.
router = APIRouter(tags=["users"])
