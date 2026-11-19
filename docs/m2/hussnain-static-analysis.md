# Static analysis report (Muhammad Hussnain Abbas, M2 SE431)

Scope: the whole CFBS code base on `develop` at merge commit `e6a0c64` (19 Nov 2026), after all M2
module PRs (#4-#18) were merged. Tools: Pylint (lint and design checks) and Radon (cyclomatic
complexity, QR-06). Every finding is triaged below; significant ones are linked to CAPA entries.

## 1. Tools and commands

| Tool | Version | Command |
|---|---|---|
| Pylint | 4.1.4 (astroid 4.3.4, Python 3.12.16) | `python -m pylint app` |
| Pylint, suppression audit | same | `python -m pylint app --enable=suppressed-message,useless-suppression` |
| Pylint on tests | same | `python -m pylint tests --disable=missing-function-docstring` |
| Radon | 6.0.1 | `python -m radon cc app -s -a` |

Configuration: Pylint defaults (max line length 100, max arguments 5), plus one design rule in
`pyproject.toml` (section 4). CI (`.github/workflows/ci.yml`) runs `pylint app` on every push and
pull request and uploads `pylint-report.txt`. Test code is not linted in CI, so the tests run gives
real findings.

## 2. Summary of results

| Target | Result |
|---|---|
| `app` (production code) | **10.00/10**, 0 messages |
| `app`, suppression audit | 8 suppressed messages (section 4), **1 useless suppression** (fixed, section 3) |
| `tests` | **8.50/10**, 168 messages: 134 `redefined-outer-name`, 11 `unsubscriptable-object`, 7 `unused-argument`, 5 `too-few-public-methods`, 5 `line-too-long`, 4 `use-implicit-booleaness-not-comparison`, 1 `too-many-arguments`, 1 `too-many-positional-arguments` |
| Radon, `app` | 263 blocks analysed, **all grade A**, average complexity **1.41**; highest 4 (`AuthService.login`, `SqlFacilityLookup.is_within_hours`, `FacilityRepository.update`, `BookingService._check_available`, `BookingService._get_visible`) |

Radon output (tail):

```
263 blocks (classes, functions, methods) analyzed.
Average complexity: A (1.414448669201521)
```

QR-06 (cyclomatic complexity <= 10 for booking and policy methods) is met with a wide margin.

## 3. Findings in production code (`app`)

| Id | Message | File:line | Severity | Decision |
|---|---|---|---|---|
| SA-01 | I0021 useless-suppression: `too-many-arguments` on `BookingService.__init__` never applies (the five collaborators are keyword-only) | `app/bookings/service.py:85` | Low | **Fixed** in `d0060d3`: suppression removed; Pylint still 10.00/10, 207 tests pass |
| SA-02 | R0903 too-few-public-methods on `BookingService` (only `request_booking` existed at step 2) | `app/bookings/service.py` at `e5fde83` | Low | **Fixed**: suppressed with a stated reason at `e5fde83`; suppression removed in `b6be6ef` when cancel and approval methods were added |
| SA-03 | Seven findings in the FR-06 policies (unused parameters, too-few-public-methods), recorded by Umer | `app/approvals/policies.py` | Low | **Fixed** in `252f1d9` (CAPA-02) |

## 4. Suppressions (each audited)

| Location | Suppressed check | Reason stated in code | Decision |
|---|---|---|---|
| `pyproject.toml` design rule | R0903 for classes derived from `DeclarativeBase` / `app.core.db.Base` | SQLAlchemy models are declarative records with no methods | Justified suppression |
| `app/core/interfaces.py:40` `BookingPolicy` | R0903 | one method by design (ISP) | Justified suppression |
| `app/notifications/subscriber.py:38` `TaskExecutor` | R0903 | one method by design (ISP) | Justified suppression |
| `app/users/service.py:21` `UserByEmail` | R0903 | one method by design (ISP) | Justified suppression |
| `app/users/service.py:44` `AuthService` | R0903 | login only, by design (SRP) | Justified suppression |
| `app/bookings/publisher.py:41` `publish` | W0718 broad-exception-caught | isolate subscribers: the booking is already committed, so one failing handler must not stop the others; the error is logged at ERROR with `logger.exception` | Justified suppression |
| `app/approvals/policies.py:33, 50, 67` `StudentPolicy`, `FacultyPolicy`, `AdminPolicy` | R0903 | **none written** (justification is in CAPA-02: single-method Strategy classes) | Justified suppression, but the inline reason required by the architecture contract is missing: **deferred to M3**, owner Umer (proposed CAPA-08) |

## 5. Findings in test code (`tests`)

Every message is listed, grouped where one cause produces many instances.

| Id | Message | File:line | Severity | Decision |
|---|---|---|---|---|
| SA-04 | W0621 redefined-outer-name, 134 instances: conftest 3, core 5, users 20, facilities 32, bookings 54, approvals 13, notifications 6, integration 1 | every test module that takes fixtures | Info | **False positive**: pytest injects fixtures by parameter name, so a test parameter always has the fixture's name. Proposed CAPA-06: disable W0621 for `tests/` in the Pylint configuration in M3 |
| SA-05 | E1136 unsubscriptable-object: `sessionmaker[Session]`, 11 instances | `tests/conftest.py:87`; `tests/bookings/test_concurrency.py:29, 44, 68`; `tests/integration/test_wiring.py:32, 69`; `tests/notifications/test_subscriber.py:79, 85, 98, 118, 132` | Info | **False positive**: `sessionmaker` is a generic class in SQLAlchemy 2.x and is subscriptable at run time (all 207 tests run); astroid cannot infer it. Covered by CAPA-06 (configure or annotate) |
| SA-06 | W0613 unused-argument `facility_id`, `start`, `end` (6 instances) | `tests/bookings/fakes.py:116, 119` (`FakeLookup.is_within_hours`, `overlaps_block`) | Info | **False positive**: a fake must keep the `FacilityLookup` signature to be substitutable (LSP); it returns a fixed answer |
| SA-07 | W0613 unused-argument `client` | `tests/approvals/test_approval_api.py:30` | Info | **False positive**: the fixture requests `client` so that its dependency override is installed after the client fixture (and cleared by its teardown) |
| SA-08 | R0903 too-few-public-methods (5) | `tests/bookings/fakes.py:123` (`FakePolicy`), `:138` (`RecordingPolicyFor`); `tests/bookings/test_booking_service.py:42` (`Env`); `tests/notifications/test_subscriber.py:43`; `tests/users/test_auth_service.py:16` | Info | **False positive**: single-purpose test doubles and fixtures |
| SA-09 | R0913 too-many-arguments, R0917 too-many-positional-arguments (6/5) | `tests/bookings/test_concurrency.py:43` (`_request`) | Low | **Deferred to M3** (owner Hussnain): the thread target takes all its inputs explicitly so each thread is independent; bundling them in a small dataclass would satisfy the check |
| SA-10 | C0301 line-too-long (101-102/100), 5 instances | `tests/conftest.py:32, 88` and `tests/notifications/test_subscriber.py:1, 53` (owner Danish); `tests/integration/test_wiring.py:87` (owner Bilal) | Low | **Deferred to M3**: real style defects in files owned by other members; owners informed (proposed CAPA-07) |
| SA-11 | C1803 use-implicit-booleaness-not-comparison (`x == []`), 4 instances | `tests/bookings/test_publisher.py:30`; `tests/facilities/test_schedule_api.py:106, 194`; `tests/users/test_seed.py:28` | Info | **False positive**: in a test, `== []` asserts the value is an empty list; `not x` would also pass for `None` |

## 6. Links to the CAPA log

| CAPA | Finding | Action | Owner | Status |
|---|---|---|---|---|
| CAPA-02 (existing) | SA-03 | Policy findings fixed in `252f1d9` | Muhammad Umer | Closed |
| CAPA-06 (proposed) | SA-04, SA-05 | Pylint configuration for `tests/`: disable W0621; annotate or configure `sessionmaker` typing; then lint tests in CI | Muhammad Hussnain Abbas | Open, M3 |
| CAPA-07 (proposed) | SA-10 | Wrap the five long lines in test files | Danish Ahmed, Muhammad Bilal | Open, M3 |
| CAPA-08 (proposed) | Section 4, `policies.py` suppressions | Add the stated reason to the three inline suppressions | Muhammad Umer | Open, M3 |
| (new, closed) | SA-01 | Useless suppression removed in `d0060d3` | Muhammad Hussnain Abbas | Closed |

The proposed entries are for Umer to add to `docs/m2/capa-log.md`.
