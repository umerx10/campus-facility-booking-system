# M2 SE423 section: Danish Ahmed (2023172)

Scope: the shared skeleton, User and Access (FR-01) and Notifications (FR-10). Every claim below
names the file or commit that shows it. Branches: `feature/core-skeleton` (PR #4, merged into
`develop` by Bilal as merge commit `ae3f03b`), `feature/users-auth` (PR B), `feature/notifications`
(PR C), stacked so each could be reviewed while the next was built.

## 1. Shared skeleton (`app/core`, models, fixtures, CI)

On 18 Nov 2026 the repository still had no code, and every module depends on a common base, so I
wrote the skeleton (agreed with the team as the one exception to "own package only"). Commits:
`1fb8576` (tests) and `d4b503f` (code).

| Part | File | Why |
|---|---|---|
| Layering router → service → repository → model | each module package | Routers only validate and call a service; SQL only in `repository.py` (M1 Figure 1) |
| Narrow interfaces as `typing.Protocol` | `app/core/interfaces.py` | `FacilityLookup`, `BookingPolicy`, `EventPublisher`: modules depend on these, not on each other's classes (DIP, ISP) |
| Domain exceptions with their own HTTP status | `app/core/exceptions.py` | `DomainError` subclasses carry `status_code`; one handler in `app/main.py` maps all of them and logs at WARNING |
| Booking events | `app/core/events.py` | Frozen dataclasses sharing `BookingEvent`, so subscribers cannot alter them |
| Identity and role guard | `app/core/deps.py` | `get_current_user`, `require_role(*roles)`, `CurrentUser` |
| Thread-safety recipe | `app/core/db.py` | `make_engine` sets `isolation_level = None` on connect and runs `BEGIN IMMEDIATE` on every `begin` |
| 7 M1 tables | `app/*/models.py`, gathered by `app/models_registry.py` | Each model in its owner's package; the registry avoids a db ↔ models import cycle |
| Shared fixtures | `tests/conftest.py` | `client`, `db_session`, `as_user`, `file_engine`, `session_factory_file` |
| CI | `.github/workflows/ci.yml` | Pylint report and pytest with coverage on every push and PR, artifacts uploaded |

The concurrency recipe has its own tests in `tests/core/test_skeleton.py`: a transaction is open
right after `begin()`, and a second connection is refused "database is locked" before the first
transaction has run any query, which shows the write lock is taken at the start.

## 2. User and Access (FR-01)

Commits: `85124bd` → `1083316` (hashing, tokens), `fbdb8f3` → `36f0115` (login, current user, guard).

- `app/users/security.py`: PBKDF2-HMAC-SHA256, 16-byte random salt, 600000 iterations, stored as
  `pbkdf2_sha256$iterations$salt$hash`, compared with `hmac.compare_digest`. JWT (PyJWT, HS256) with
  `sub`, `role`, `exp`; 60-minute lifetime; secret from `CFBS_SECRET`.
- `app/users/service.py`: `AuthService.login` gives one message, "Invalid email or password", for
  every failure. For an unknown email it still checks a dummy hash, so response time does not reveal
  which emails exist. `UserService` serves the profile and the admin list.
- `app/users/router.py`: `POST /auth/login`, `GET /users/me`, `GET /users` (ADMIN only).
- `app/core/deps.py`: `get_current_user` now decodes the Bearer token. It kept its name and return
  type, so no other module changed.
- `app/users/seed.py`: `python -m app.users.seed` creates one admin, faculty and student demo user,
  only if missing.

## 3. Notifications (FR-10)

Commits: `400daa2` → `7caa349` (factory), `e3f526a` → `1199ffe` (subscriber, endpoints).

- `app/notifications/factory.py`: `NotificationFactory` and the notice types (section 4).
- `app/notifications/subscriber.py`: `NotificationSubscriber`, the Observer listener (section 5).
- `app/notifications/service.py`, `router.py`: `GET /notifications` (own notifications, newest first)
  and `PATCH /notifications/{id}/read`. Another user's id gives the same 404 as a missing one.
- `app/notifications/setup.py`: `register_notifications(publisher, session_factory, executor=None)`
  for the integration lead to call once the booking publisher exists. `app/main.py` is unchanged.

## 4. Factory pattern: `NotificationFactory`

- Problem: each booking event (confirmed, rejected, cancelled) needs a different notice. Building
  the text inside the booking code would mix two responsibilities and change the booking code for
  every new notice type.
- Classes: abstract frozen `Notice` with abstract classmethod `from_event`; `ConfirmationNotice`,
  `RejectionNotice`, `CancellationNotice` each write their own message; `NotificationFactory` holds a
  per-instance registry (event class → notice class) with `create(event)` and `register(...)`;
  `UnsupportedEventError` for an unknown event type.
- Benefit: a new notice type is added by `register()`, without editing the factory (Open/Closed).
  `test_register_adds_a_new_event_type_without_changing_the_factory` proves this.
- Rejected alternative (M1 section 6): an if/elif chain on the event type inside `BookingService`.

## 5. Observer listener and asynchronous delivery

`NotificationSubscriber(factory, session_factory, executor)` subscribes `handle` to the three
booking events through the `EventPublisher` Protocol (`register`). The thread-safety strategy, as
implemented in `app/notifications/subscriber.py`:

1. `handle(event)` only submits `_deliver(event)` to an executor and returns. The request that
   published the event never waits for a notification.
2. `_deliver` runs on a worker thread and opens its own session; sessions are never shared between
   threads.
3. Concurrent writes are serialized by SQLite's write lock, taken at the start of each transaction
   by the `BEGIN IMMEDIATE` recipe in `app/core/db.py`.
4. The publisher calls subscribers after the booking commits (Booking module contract), so a
   notification failure cannot roll a booking back.
5. On `SQLAlchemyError` the delivery rolls back and logs with `logger.exception`; it never
   re-raises.

Evidence: `test_handle_returns_before_delivery_finishes` blocks delivery on a `threading.Event`,
asserts `handle` has already returned with no row stored, then releases and finds the row (real
`ThreadPoolExecutor`, file database). It passed 10 out of 10 repeated runs.
`test_a_failed_save_is_logged_at_error_and_does_not_raise` uses a real foreign-key violation.

## 6. Defensive programming

| Where | Check | On failure |
|---|---|---|
| `app/users/schemas.py` `LoginRequest` | non-empty fields, simple email pattern, length limits | 422 before any service runs |
| `app/core/deps.py` `get_current_user` | Bearer present, signature, expiry, known role | `AuthenticationFailed` 401 (`TokenError`/`ValueError` chained with `from`) |
| `app/core/deps.py` `require_role` | role allowed | `UnauthorizedOperation` 403 |
| `app/users/security.py` `verify_password` | 4 parts, known algorithm; catches only `ValueError`, `binascii.Error` | returns `False`, never raises |
| `app/users/service.py` `AuthService.login` | user exists and password matches | `AuthenticationFailed`; logged at INFO with the email, never the password |
| `app/users/service.py`, `app/notifications/service.py` | record exists and belongs to the caller | `NotFound` 404 |
| `app/notifications/subscriber.py` `_deliver` | event type supported; save succeeded | rollback, `logger.exception`, not re-raised |
| `app/main.py` `handle_domain_error` | every `DomainError` | JSON `{"error", "detail"}` with the class's status, logged at WARNING |

No bare `except Exception` exists in my code; every handler names the exceptions it expects.

## 7. SOLID in this code

- SRP: `security.py` (crypto), `service.py` (rules), `router.py` (HTTP), `repository.py` (SQL);
  `AuthService` (login) is separate from `UserService` (profile, listing).
- OCP: `NotificationFactory.register`; one exception handler driven by each class's `status_code`.
- LSP: the three notices are interchangeable wherever a `Notice` is expected; `FakeUserRepository`,
  `FakePublisher` and `ImmediateExecutor` stand in for the real classes in tests.
- ISP: one-method Protocols where one method is all a client needs (`UserByEmail`, `TaskExecutor`,
  `BookingPolicy`).
- DIP: services receive their repository; the subscriber receives its factory, session factory and
  executor; all through constructors.

## 8. Test-first evidence

Each `test:` commit was run and failed for the stated reason before the matching `feat:` commit.

| Step | Red (`test:`) | Reason it failed | Green (`feat:`) |
|---|---|---|---|
| Skeleton | `1fb8576` | `No module named 'app'` | `d4b503f` (15 passed) |
| Hashing, tokens | `85124bd` | `No module named 'app.users.security'` | `1083316` (29 passed) |
| Login, guard, seed | `fbdb8f3` | service/seed modules missing; 12 API tests 404 | `36f0115` (46 passed) |
| Factory | `400daa2` | `No module named 'app.notifications.factory'` | `7caa349` (53 passed) |
| Subscriber, endpoints | `e3f526a` | subscriber module missing; 5 API tests 404 | `1199ffe` (62 passed) |

No refactor commits were made: after each green step there was no change worth a separate commit.

## 9. Measured quality (18 Nov 2026, `python -m pytest --cov=app --cov-report=term-missing`)

62 tests passed. Total coverage **94%** (541 statements, 32 missed). By package: `app/users` 95%
(188 statements, 10 missed: the seed script's `main`, and line 53 of `security.py`);
`app/notifications` 91% (160, 15 missed: `setup.py` 0% because nothing calls it until the booking
publisher exists, and the `UnsupportedEventError` branch of the subscriber); `app/core` 96% (111, 4
missed: the production `get_session`). Pylint `app`: 10.00/10. Radon: every block A; highest is 4
(`verify_password`, `AuthService.login`, `seed.main`).

## 10. Deviations from M1

- `users` gained `name` and `password_hash`; `notifications` gained `message` (login and stored text
  need them).
- Access tokens are JWTs (PyJWT). They are stateless, so a deleted user keeps access until expiry
  (60 minutes); accepted for this scope.
- Added `uvicorn` (`d82d5df`) so the app can be served for the demo.
