"""FastAPI application: includes every module's router and maps domain errors to HTTP responses."""

import logging
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.approvals.router import router as approvals_router
from app.bookings.publisher import booking_events
from app.bookings.router import router as bookings_router
from app.core.db import engine, session_factory
from app.core.exceptions import DomainError
from app.facilities.router import router as facilities_router
from app.models_registry import create_all_tables
from app.notifications.router import router as notifications_router
from app.notifications.setup import register_notifications
from app.users.router import router as users_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Start-up: create missing tables and subscribe notifications to booking events.

    Notifications are written on a small worker pool (Observer, asynchronous delivery). On shutdown
    the pool is closed with wait=True, so queued notifications are written before the server stops.
    """
    create_all_tables(engine)
    executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="notify")
    register_notifications(booking_events, session_factory, executor)
    try:
        yield
    finally:
        executor.shutdown(wait=True)


app = FastAPI(title="Campus Facility Booking System", lifespan=lifespan)

for module_router in (
    users_router,
    facilities_router,
    bookings_router,
    approvals_router,
    notifications_router,
):
    app.include_router(module_router)


@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, exc: DomainError) -> JSONResponse:
    """The one place where domain errors become HTTP responses, using each class's status_code."""
    logger.warning(
        "%s on %s %s: %s", type(exc).__name__, request.method, request.url.path, exc
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": type(exc).__name__, "detail": str(exc)},
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check for the demo and CI."""
    return {"status": "ok"}
