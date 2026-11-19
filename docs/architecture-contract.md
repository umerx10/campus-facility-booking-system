# Architecture contract: Campus Facility Booking System (CFBS)

Read this before writing any code. This is a joint SE423/SE431 university project. It is graded on the
repository history (who committed what, test-first order) and on each member explaining their own code.
Follow the M1 design below; anything that deviates from it must be justified in the report.

## Stack (fixed by the M1 report, do not change)

Python 3.11+ (CI uses 3.12), FastAPI, SQLAlchemy 2.x on SQLite, pytest + pytest-cov, Pylint, Radon,
GitHub Actions. Add a package only when needed, and pin it in `requirements.txt`.

## Layout and ownership

Only touch files in your own package. Changes to `app/core/` or `tests/conftest.py` go through a pull
request reviewed by the M2 SE423 lead (Bilal).

| Path | Owner | Module |
|---|---|---|
| `app/core/` | Bilal (M2 SE423 lead) reviews changes; initial skeleton written by Danish | Shared: db, enums, exceptions, interfaces, events, deps |
| `app/users/` | Danish | User and Access (FR-01) |
| `app/facilities/` | Bilal | Facility Management (FR-02, FR-03) |
| `app/bookings/` | Hussnain | Booking and Scheduling (FR-03, FR-04, FR-05, FR-07, FR-09) |
| `app/approvals/` | Umer | Approval and Policies (FR-06, FR-08) |
| `app/notifications/` | Danish | Notifications (FR-10) |
| `tests/<module>/` | same owner as the module | |
| `docs/m2/` | each member writes their own section file | |

Each module package contains, as needed: `models.py`, `schemas.py` (Pydantic), `repository.py`,
`service.py`, `router.py`.

## Layers (M1 Figure 1)

router -> service -> domain / policy -> repository -> SQLAlchemy models.

- Routers hold no business logic: they validate input (Pydantic), call a service, return a schema.
- Services receive repositories, policies and the publisher through their constructor (dependency
  inversion, so unit tests can pass fakes).
- No SQL outside `repository.py`.

## Shared contracts (`app/core/`)

- `enums.py`: `Role` = STUDENT, FACULTY, ADMIN. `BookingStatus` = PENDING, CONFIRMED, REJECTED, CANCELLED.
- `deps.py`:
  - `CurrentUser` dataclass (`id: int`, `role: Role`).
  - `get_current_user()` FastAPI dependency.
  - `require_role(*roles)` dependency factory.
  - Until User and Access is merged, `get_current_user` is a stub that reads the `X-User-Id` and
    `X-User-Role` headers. Tests must never rely on that: they use the `as_user` fixture, which overrides
    the dependency.
- `interfaces.py` (`typing.Protocol`):
  - `FacilityLookup`: `get_facility(facility_id) -> FacilityInfo` (id, capacity, requires_approval, active);
    `is_within_hours(facility_id, start, end) -> bool`; `overlaps_block(facility_id, start, end) -> bool`.
  - `BookingPolicy`: `validate(user: CurrentUser, facility: FacilityInfo, start, end) -> None`, raises
    `PolicyViolation`.
  - `EventPublisher`: `subscribe(event_type, handler)`, `publish(event)`.
- `events.py`: frozen dataclasses `BookingConfirmed`, `BookingRejected`, `BookingCancelled`, each with
  `booking_id`, `user_id`, `facility_id`, `occurred_at`.
- `exceptions.py`: base `DomainError`; subclasses `NotFound` (404), `InvalidBookingTime` (422),
  `FacilityUnavailable` (409), `BookingConflict` (409), `PolicyViolation` (422),
  `UnauthorizedOperation` (403), `AuthenticationFailed` (401). One handler in `app/main.py` maps them to
  these HTTP codes.
- Never write a bare `except Exception:` that swallows the error. Log with `logging.getLogger(__name__)`
  and re-raise a domain error.

## Database (7 tables, M1 section 8)

- `users`: id, name, email (unique), role, password_hash. Name and password_hash were added to the M1
  schema because login needs them; note this in the report.
- `facilities`: id, name, capacity, requires_approval, active.
- `facility_operating_hours`: id, facility_id, weekday, opens_at, closes_at.
- `bookings`: id, user_id, facility_id, start_at, end_at, status.
- `facility_blocks`: id, facility_id, start_at, end_at, reason.
- `booking_history`: id, booking_id, old_status, new_status, changed_at, actor_id.
- `notifications`: id, user_id, event_type, message, created_at, read_at. Message was added to the M1
  schema.

Store times as UTC datetimes. Booking intervals are half-open `[start, end)`: two intervals overlap when
`a.start < b.end and b.start < a.end`, so back-to-back bookings are allowed.

## Concurrency (M1 section 7)

- `app/core/db.py` applies the SQLAlchemy pysqlite recipe. On connect it sets
  `isolation_level = None`; on the `begin` event it runs `BEGIN IMMEDIATE`. Every transaction therefore
  takes the write lock before reading. This is the documented thread-safety strategy.
- Booking confirmation, approval and reschedule do the overlap check and the write in ONE transaction.
- Notifications are dispatched after commit, asynchronously. A notification failure is logged and never
  rolls back a booking.
- Concurrency tests use a temporary file database, not in-memory, so several connections compete for it.

## Test-first rule (graded, follow exactly)

1. Write the failing tests only. Run `pytest`, show that they fail for the right reason, then STOP. The
   human commits: `test: ...`
2. Write the minimum code to pass. Do not edit the tests. Run `pytest`, then STOP. The human commits:
   `feat: ...`
3. Optional cleanup, with tests still green. The human commits: `refactor: ...`

Never write an implementation and its tests in the same step. Never squash.

- Tests live in `tests/<module>/test_*.py`.
- Use the `tests/conftest.py` fixtures: `client`, `db_session`, `as_user(role, user_id=1)`.
- Unit tests for services use small fake classes for the Protocols, not the database.

## Git

- Branch `feature/<module>-<topic>` from `develop`.
- Open a pull request into `develop`; the merge uses a merge commit, never squash.
- Never commit to `main` or `develop` directly.
- Never push, force-push, or merge on the human's behalf.

## Style

- Type hints everywhere, and a docstring on every public class.
- Small functions: cyclomatic complexity of 10 or less (QR-06, checked with Radon).
- Pylint clean, or a justified inline disable that gives the reason.

## AI usage log (course rule)

After each significant session, add a row to `docs/ai-usage-log.md` with: member, date, tool and model,
purpose, prompt summary, what was kept, what was changed, how it was verified.
