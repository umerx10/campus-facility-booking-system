"""FastAPI application: includes every module's router and maps domain errors to HTTP responses."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.approvals.router import router as approvals_router
from app.bookings.router import router as bookings_router
from app.core.db import engine
from app.core.exceptions import DomainError
from app.facilities.router import router as facilities_router
from app.models_registry import create_all_tables
from app.notifications.router import router as notifications_router
from app.users.router import router as users_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create missing tables when the server starts."""
    create_all_tables(engine)
    yield


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
