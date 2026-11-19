"""HTTP routes for Booking and Scheduling. Endpoints are added by the module owner."""

from fastapi import APIRouter

router = APIRouter(prefix="/bookings", tags=["bookings"])
