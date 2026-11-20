
# CFBS Milestone 2 - Requirements Traceability Matrix (RTM v2)

**Prepared by:** Muhammad Umer
**Course:** SE431 - Software Quality Assurance
**Date:** 19 November 2026
**Status:** Working draft - update after integration

## 1. Purpose

This matrix updates the M1 requirements traceability matrix
using actual M2 development evidence.

It covers:
- Functional requirements FR-01 to FR-10.
- Quality requirements QR-01 to QR-08.
- Implementation ownership and code locations.
- Test references and expected verification activities.
- Current implementation status and Git evidence.

Status definitions:
- **Implemented and passing:** Feature implemented and tests
  verified on the relevant integrated build.
- **Partial:** Implementation or verification incomplete,
  or feature not yet integrated into develop.
- **Planned M3:** Not completed during M2.

A pushed feature branch does not count as verified integration.

## 2. Functional Requirements Traceability

| ID | Requirement | Owner / Code | Tests / Cases | M2 Status | Evidence |
|---|---|---|---|---|---|
| FR-01 | Role-based authentication and access | Danish; `app/users/`, `app/core/deps.py` | `tests/users/`; TC-01 | Implemented on develop; final acceptance pending | Users/authentication branch merged |
| FR-02 | Admin facility management | Bilal; `app/facilities/` | `tests/facilities/test_facility_api.py`; TC-02 | Implemented on develop; final acceptance pending | PR #10, merge `1ee09df` |
| FR-03 | View facility schedules and availability | Bilal/Hussnain; `app/facilities/`, `app/bookings/` | `tests/facilities/test_schedule_api.py`, booking schedule API; TC-03 | Partial | Facility schedule merged; booking API not yet confirmed |
| FR-04 | Submit a valid booking request | Hussnain; `app/bookings/service.py`, router | `tests/bookings/test_booking_service.py`, API tests; TC-04 | Partial | Booking service commit `e5fde83`; API implementation pending |
| FR-05 | Reject overlapping bookings and maintenance conflicts | Hussnain/Bilal; booking service and facility lookup | `tests/bookings/test_concurrency.py`, facility lookup tests; TC-05 | Partial | Booking service implemented on feature branch; concurrency test execution not yet confirmed |
| FR-06 | Enforce role-specific booking policies | Umer; `app/approvals/policies.py` | `tests/approvals/test_policies.py`; TC-06 | Partial - PR awaiting merge | PR #12, commit `252f1d9`, Pylint 10.00/10 |
| FR-07 | Authorized cancellation and rescheduling | Hussnain; `app/bookings/service.py` | Booking service/API tests; TC-07 | Partial | Cancellation implemented in `b6be6ef`; rescheduling planned M3 |
| FR-08 | Administrator approval of restricted bookings | Umer/Hussnain; `app/approvals/service.py`, booking service | `tests/approvals/test_approval_service.py`, planned approval API tests; TC-08 | Partial | Umer commit `53a84a6`; approval API and integration pending |
| FR-09 | Booking status and history | Hussnain; `app/bookings/` | Booking service/history API tests; TC-09 | Partial | Booking service implementation branch; API verification pending |
| FR-10 | In-app booking notifications | Danish; `app/notifications/` | `tests/notifications/`; TC-10 | Partial | Notifications PR #6 merged; booking-event integration pending |

## 3. Quality Requirements Traceability

| ID | Requirement / Acceptance Target | Owner | Verification | M2 Status |
|---|---|---|---|---|
| QR-01 | Functional rules satisfy FR-01-10 | All module owners | TC-01-TC-10, pytest and acceptance tests | Partial |
| QR-02 | 95% of availability queries within 2 seconds under 20 users | Bilal | QT-01: timed workload | Planned M3 |
| QR-03 | Zero overlapping confirmed bookings across 100 competing booking pairs, including approval races | Hussnain | QT-02: concurrency test and SQL overlap query | Partial; execution evidence pending |
| QR-04 | All tested unauthorized admin actions denied; no plaintext passwords | Danish/Umer | QT-03: authorization tests and password-storage review | Partial |
| QR-05 | At least 4/5 users complete booking without assistance | Team | QT-04: usability pilot | Planned M3 |
| QR-06 | Final core coverage at least 60%; booking/policy complexity at most 10 | All module owners | QT-05: pytest-cov, Pylint and Radon; local results: 137 passed, 96% coverage, ApprovalService 100%, Pylint 10/10 | Partial - final integration pending |
| QR-07 | Fresh supported Python setup within 15 minutes, excluding downloads | Bilal | QT-06: clean installation | Planned M3 |
| QR-08 | Zero event-contract mismatches in defined notification/history integration tests | Danish/Hussnain | QT-07: event-contract integration tests | Partial |

## 4. Umer's Individual Verification Evidence

### FR-06 - Booking Policies

Branch: `feature/approvals-policies`

Implementation:
- StudentPolicy: maximum 120 minutes.
- FacultyPolicy: maximum 240 minutes.
- AdminPolicy: no duration cap.
- Strategy selection through `policy_for()`.

Tests:
- 119, 120, 121 minutes for students.
- 239, 240, 241 minutes for faculty.
- Admin duration behavior.
- Policy selection.
- BookingPolicy interface compatibility.

Evidence:
- Implementation commit: `252f1d9`.
- Pylint: 10.00/10.
- PR #12 targets develop, review requested.
- Merge and final integration verification pending.

### FR-08 - Approval Service

Branch: `feature/approvals-workflow`

Implementation:
- Admin-only approval.
- Admin-only rejection.
- Admin-only pending booking listing.
- Domain exception propagation.
- Dependency inversion through PendingBookingActions.

Tests:
- Approval delegation.
- Rejection delegation.
- Pending booking listing.
- Unauthorized student/faculty operations.
- BookingConflict and NotFound propagation.

Evidence:
- Implementation commit: `53a84a6`.
- Full local test suite: 137 passed, 1 warning.
- Pylint: 10.00/10.
- Approval API and integration remain pending.

## 5. M2 Architecture Deviation

The M1 design proposed a HistorySubscriber for booking history.

M2 uses transactionally written booking-history records
because events do not include the actor or previous status.

This change is intended to keep the booking status and
history consistent within the same database transaction.

The implementation and event-contract evidence must be
verified during final integration.

## 6. Evidence Still Required Before M2 Submission

- Confirm merge of PR #12.
- Confirm merge and CI status of the Booking module.
- Finish and merge the Approval API.
- Collect Bilal's finalized black-box test case IDs.
- Obtain final pytest and coverage output from develop.
- Record actual concurrency test results.
- Record static-analysis and Radon results.
- Confirm the M2 baseline tag.
- Update implemented/partial statuses using merged evidence.
- Link open defects to the CAPA log.

## 7. References

- `.claude-local/m1-se431-report.tex` - RTM v1,
  QR-01-QR-08 and initial risks.
- `.claude-local/m1-se423-report.tex` - FR-01-FR-10.
- `docs/architecture-contract.md`.
- `docs/m2/team-plan.md`.
- `docs/m2/umer-vv-plan.md`.
- GitHub pull requests, commits and CI results.

**Note:** Test IDs TC-01-TC-10 are inherited from the M1
traceability plan. Replace or extend them with Bilal's
final detailed test-case IDs before submission.

## Final FR-06 / FR-08 Traceability Update - 19 November 2026

| Requirement | Implementation | Verification | Local status |
|---|---|---|---|
| FR-06 | app/approvals/policies.py | tests/approvals/test_policies.py | Implemented and tested |
| FR-08 Service | app/approvals/service.py | tests/approvals/test_approval_service.py | Implemented and tested |
| FR-08 API | app/approvals/router.py | tests/approvals/test_approval_api.py | Implemented and tested |

Final local regression: 207 passed, 0 failed; Pylint 10.00/10.
GitHub merge/review completion is tracked separately from local verification.
