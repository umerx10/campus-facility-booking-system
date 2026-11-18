# M2 SE423 section: Muhammad Bilal

Scope: Facility Management (FR-02, and the facility half of FR-03), the `SqlFacilityLookup` that the
Booking module uses, and the M2 SE423 lead duties. Every claim below names the file or commit that
shows it. Branch `feature/facilities-management`, PR #10, reviewed and merged into `develop` by
Hussnain with merge commit `1ee09df`.

## 1. What I built

| Part | File | What it does |
|---|---|---|
| Schemas | `app/facilities/schemas.py` | Pydantic input limits (name 1-100 characters, capacity >= 1, weekday 0-6, opens_at < closes_at, start_at < end_at); timezone-aware datetimes converted to naive UTC |
| Repository | `app/facilities/repository.py` | All facility SQL: facilities, operating hours, maintenance blocks, the half-open block-overlap query |
| Service | `app/facilities/service.py` | `FacilityService`: create, list active, get, update, deactivate, set weekly hours, add block, daily schedule; raises `NotFound` |
| Router | `app/facilities/router.py` | 8 endpoints; changes need `require_role(Role.ADMIN)`, reads need any authenticated user |
| Lookup | `app/facilities/lookup.py` | `SqlFacilityLookup(session)` implements the `FacilityLookup` Protocol; `get_facility_lookup` FastAPI dependency |

Endpoints: `POST /facilities`, `GET /facilities` (active only), `GET /facilities/{id}`,
`PATCH /facilities/{id}`, `POST /facilities/{id}/deactivate`, `PUT /facilities/{id}/hours`,
`POST /facilities/{id}/blocks`, `GET /facilities/{id}/schedule?date=YYYY-MM-DD`.

Facilities are never deleted: deactivation keeps the row (and readable by id) so old bookings still
refer to it, and the list shows only active facilities (FR-02).

## 2. The `FacilityLookup` abstraction (Dependency Inversion)

- Problem: the booking service must know whether a facility exists, is active, is open at that time
  and is free of maintenance blocks. If it imported the `Facility` model or my repository, every
  change in my module could break bookings, and its unit tests would need a database.
- Design: the Booking module depends on the `FacilityLookup` Protocol in `app/core/interfaces.py`
  (three methods) and receives `FacilityInfo`, a frozen dataclass, never a model object.
  `SqlFacilityLookup` is the only class that implements it with SQL, through `FacilityRepository`.
- Benefit: Hussnain's `BookingService` is unit tested with a fake lookup and gets the real one only
  in `get_booking_service`; both modules were built in parallel against the same three method
  names.
- Rejected alternative: the booking repository querying the facility tables directly. That would
  put facility SQL in two packages and break the ownership rule in `docs/architecture-contract.md`.

## 3. Validation and exceptions

| Where | Check | On failure |
|---|---|---|
| `schemas.py` `FacilityCreate`, `FacilityUpdate` | name length 1-100, capacity >= 1 | 422 before any service runs |
| `schemas.py` `OperatingHoursIn` | weekday 0-6; `opens_at < closes_at` (model validator) | 422 |
| `schemas.py` `BlockIn` | `start_at < end_at`; reason 1-255 characters; aware datetimes to naive UTC | 422 |
| `router.py` | `require_role(Role.ADMIN)` on every change; `get_current_user` on every read | 403 / 401 |
| `service.py` `FacilityService.get` (used by every operation on one facility) | facility exists | `NotFound` 404 |
| `lookup.py` `SqlFacilityLookup.get_facility` | facility exists | `NotFound` (the booking service turns it into 404) |

`FacilityUpdate` treats a field sent as null as "not sent", so a PATCH cannot write a null into a
NOT NULL column. Deactivating an inactive facility changes nothing (idempotent). My code has no
`try`/`except`: there is no error it can recover from, so domain errors and database errors
propagate to the one handler in `app/main.py`.

## 4. SOLID in this code

- SRP: `schemas.py` validates, `router.py` speaks HTTP, `service.py` holds the rules,
  `repository.py` holds the SQL, `lookup.py` answers the booking module's questions.
- OCP: a new facility rule for bookings is a new `FacilityLookup` method implemented here; the
  booking service does not change for changes in how hours or blocks are stored.
- LSP: `SqlFacilityLookup` and the booking tests' fake lookup are interchangeable wherever a
  `FacilityLookup` is expected.
- ISP: the booking module sees only the three lookup methods, not the eight-operation
  `FacilityService`.
- DIP: `FacilityService` receives a `FacilityStore` Protocol through its constructor;
  `BookingService` receives a `FacilityLookup`.

## 5. Test-first evidence

Each `test:` commit was run and failed for the stated reason before the matching `feat:` commit.

| Step | Red (`test:`) | Reason it failed | Green (`feat:`) |
|---|---|---|---|
| Facility management API | `8a5aae5` | 29 new tests failed: routes missing (404); 62 earlier tests passed | `073a630` (91 passed) |
| Hours, blocks, lookup | `4a2b9c7` | `No module named 'app.facilities.lookup'`; hours, blocks and schedule routes 404 | `e8b1959` (124 passed) |

No refactor commits were made. Pylint `app` was 10.00/10 after each `feat:` commit.

## 6. Measured quality (18 Nov 2026, `develop` at `1ee09df`)

`python -m pytest --cov=app --cov-report=term-missing`: 124 passed, total coverage 96% (820
statements, 33 missed). `app/facilities`: 270 statements, 1 missed (99%): line 60 of `lookup.py`,
the `get_facility_lookup` dependency, which runs once the booking router uses it. With
`--cov-branch`, `app/facilities` is 99% (2 partial branches: a PATCH that omits `capacity` while
changing other fields, and deactivating an already inactive facility). Pylint `app`: 10.00/10.
Radon: every block in `app/facilities` is A; the highest is 4 (`SqlFacilityLookup.is_within_hours`,
analysed in `docs/m2/bilal-whitebox.md`, and `FacilityRepository.update`).

## 7. Deviations from M1 and assumptions

- No schema change: the three facility tables are used as written in the skeleton.
- Operating hours are compared in naive UTC, the same time base as bookings (M2 assumption). A
  booking must start and end on the same day inside that weekday's window; a weekday with no row is
  closed.
- `PUT /facilities/{id}/hours` replaces the whole week in one request, which keeps the stored week
  consistent instead of editing day by day.
- FR-03 is served in two halves: `GET /facilities/{id}/schedule` (hours and blocks, mine) and
  `GET /bookings/schedule` (confirmed bookings, Booking module).

## 8. SE423 lead duties (as of 18 Nov 2026, evening)

- Merged PR #5 (users-auth) and PR #6 (notifications) with "Create a merge commit". PR #6 was merged
  first and already contained PR #5's commits, so GitHub closed #5 as merged with no merge commit of
  its own; merge commit `57862dc` brings both into `develop`.
- Integration wiring (`feature/integration-wiring`), the `develop` -> `main` baseline tagged
  `m2-baseline` and the assembled SE423 report follow once the bookings and approvals PRs are
  merged (team plan, section 3).
