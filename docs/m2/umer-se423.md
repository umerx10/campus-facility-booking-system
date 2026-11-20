
# M2 SE423 - Individual Contribution Report: Muhammad Umer

**Project:** Campus Facility Booking System (CFBS)
**Course:** SE423 - Software Construction and Development
**Milestone:** 2
**Prepared by:** Muhammad Umer (2023539)
**Date:** 19 November 2026
**Status:** Working report - integration evidence pending

## 1. Assigned Responsibilities

My primary responsibilities for M2 are:

- FR-06: Role-Based Booking Policies
- FR-08: Restricted Facility Approval Workflow
- Strategy design pattern implementation
- Unit testing using Test-Driven Development (TDD)
- SOLID compliance and defensive programming
- White-box testing of my own implementation

I own the `app/approvals/` package and corresponding
tests in `tests/approvals/`.

Two feature branches were used:

1. `feature/approvals-policies`
2. `feature/approvals-workflow`

## 2. FR-06 - Role-Based Booking Policies

### 2.1 Problem

CFBS supports three user roles with different maximum
booking durations:

| Role | Maximum Duration |
|---|---|
| Student | 2 hours |
| Faculty | 4 hours |
| Admin | No duration cap |

A booking exceeding the applicable duration must raise
a PolicyViolation.

### 2.2 Implementation

**File:** `app/approvals/policies.py`

Implemented:

- `StudentPolicy`
- `FacultyPolicy`
- `AdminPolicy`
- `policy_for(role)`
- `_check_duration()` helper

StudentPolicy rejects durations greater than 120 minutes.

FacultyPolicy rejects durations greater than 240 minutes.

AdminPolicy imposes no additional duration restriction.

Administrators are still subject to shared booking rules,
including operating hours, conflicts and maintenance blocks.
Those checks belong to the Booking and Facility modules.

### 2.3 Strategy Design Pattern

**Pattern:** Strategy (Behavioral)

**Problem:** Different user roles require different
booking-duration rules.

**Solution:** Implement one booking policy per role,
using the common BookingPolicy Protocol.

**Context:** The booking service calls the selected
policy's validate() method.

**Concrete strategies:**
- StudentPolicy
- FacultyPolicy
- AdminPolicy

**Strategy selector:** policy_for()

**Benefits:**
- Separates booking rules from booking orchestration.
- Reduces conditional logic in BookingService.
- Allows strategies to be tested independently.
- Makes role-specific policies easier to maintain.
- Supports extension through additional strategies.

**Rejected alternative:**

An if/elif chain inside BookingService, checking the
user's role before every booking.

This alternative was rejected because it would mix
role-specific duration rules with general booking logic
and increase coupling.

### 2.4 Boundary Value Testing

**Test file:** `tests/approvals/test_policies.py`

| Role | Test Duration | Expected Result |
|---|---|---|
| Student | 119 minutes | Allowed |
| Student | 120 minutes | Allowed |
| Student | 121 minutes | PolicyViolation |
| Faculty | 239 minutes | Allowed |
| Faculty | 240 minutes | Allowed |
| Faculty | 241 minutes | PolicyViolation |
| Admin | 10 hours | Allowed |

Additional tests verify:

- Correct selection through policy_for().
- Conformance to the BookingPolicy Protocol.
- Consistent exception behavior.

### 2.5 Git and Verification Evidence

Branch: `feature/approvals-policies`

Implementation commit: `252f1d9`

Pull Request: #12
https://github.com/umerx10/campus-facility-booking-system/pull/12

TDD process:

1. Wrote tests before implementation.
2. Confirmed the expected missing-module failure.
3. Committed and pushed tests separately.
4. Implemented the policy classes.
5. Resolved Pylint findings.
6. Committed and pushed implementation separately.

Observed Pylint result: 10.00/10.

PR review and merge evidence must be updated after
completion.

## 3. FR-08 - Restricted Facility Approval Workflow

### 3.1 Problem

Some facilities require an administrator's approval
before a requested booking becomes confirmed.

The approval module must permit administrators to:

- View pending booking requests.
- Approve pending bookings.
- Reject pending bookings.

Students and faculty must not perform these operations.

### 3.2 Approval Service Implementation

**File:** `app/approvals/service.py`

Implemented:

- PendingBookingActions Protocol
- ApprovalService
- approve()
- reject()
- list_pending()
- _require_admin()

ApprovalService uses administrator authorization checks
before delegating operations to the booking service.

It does not directly modify booking records or execute SQL.

### 3.3 Approval Workflow

**Approval:**

1. An administrator submits an approval request.
2. ApprovalService verifies the ADMIN role.
3. ApprovalService calls confirm_pending().
4. BookingService owns the booking-state transition and
   relevant availability/conflict checks.
5. The resulting booking is returned.

**Rejection:**

1. An administrator submits a rejection request.
2. ApprovalService verifies the ADMIN role.
3. ApprovalService calls reject_pending().
4. BookingService performs the state transition.
5. The resulting booking is returned.

**Pending list:**

Only an administrator may call list_pending() through
ApprovalService.

### 3.4 Dependency Inversion

ApprovalService depends on PendingBookingActions, a
typing.Protocol, rather than a concrete BookingService.

The interface defines:

- confirm_pending(booking_id, actor)
- reject_pending(booking_id, actor)
- list_pending()

This allows tests to inject fake booking operations.

The Booking module supplies the concrete implementation.

### 3.5 Defensive Programming

Unauthorized users cause UnauthorizedOperation to be
raised before the booking operation is called.

The service preserves domain errors received from the
booking module, including:

- BookingConflict
- NotFound

Errors are not silently caught or converted into
unstructured dictionaries.

API-level authorization and HTTP error mapping must
also be verified after the Approval API is implemented.

### 3.6 Unit Testing

**File:** `tests/approvals/test_approval_service.py`

The tests use unittest.mock.Mock to simulate booking
operations without connecting to a database.

Verified scenarios include:

- Administrator successfully delegates approval.
- Administrator successfully delegates rejection.
- Administrator retrieves pending bookings.
- Student and faculty approval attempts are rejected.
- Student and faculty rejection attempts are rejected.
- Unauthorized users cannot list pending bookings.
- BookingConflict propagates correctly.
- NotFound propagates correctly.

### 3.7 Git and Verification Evidence

Branch: `feature/approvals-workflow`

Implementation commit: `53a84a6`

TDD process:

1. Created approval-service unit tests.
2. Confirmed expected missing-module failure.
3. Committed and pushed tests separately.
4. Implemented ApprovalService.
5. Ran the project test suite.
6. Ran Pylint.
7. Committed and pushed implementation.

Observed complete test-suite result:

**137 passed, 1 warning in 12.40 seconds**

Observed Pylint result:

**10.00/10**

These results describe the local development branch at
the recorded checkpoint, not final integrated CI status.

### 3.8 Remaining FR-08 Integration

The following work remains:

- Implement GET /approvals/pending.
- Implement POST /approvals/{booking_id}/approve.
- Implement POST /approvals/{booking_id}/reject.
- Add API tests before implementation.
- Integrate with BookingService and its FastAPI dependency.
- Verify approval conflicts and HTTP authorization.
- Open the workflow PR and obtain review and merge.

The Approval Service is implemented, but FR-08 is not
yet fully integrated or complete.

## 4. SOLID Principles

| Principle | Application | Evidence |
|---|---|---|
| SRP | Policies enforce duration rules; ApprovalService coordinates approval operations | policies.py, service.py |
| OCP | Role policies are separate Strategy classes | StudentPolicy, FacultyPolicy, AdminPolicy |
| LSP | Policy implementations support the same BookingPolicy interface | test_policies.py |
| ISP | PendingBookingActions exposes only three required operations | service.py |
| DIP | ApprovalService depends on a Protocol rather than a concrete booking service | PendingBookingActions |

### 4.1 Single Responsibility Principle

Role policies handle duration-specific behavior.

ApprovalService handles administrator authorization
and approval delegation.

Database operations remain the responsibility of the
Booking module.

### 4.2 Open/Closed Principle

New duration strategies can be introduced without
modifying the core booking-service duration logic.

The strategy registry must also be updated when a new
role is introduced.

### 4.3 Liskov Substitution Principle

StudentPolicy, FacultyPolicy, and AdminPolicy implement
the common validate() method expected by BookingPolicy.

The same calling interface works across strategies.

### 4.4 Interface Segregation Principle

PendingBookingActions contains only the operations
needed by the approval service, instead of exposing
the complete BookingService interface.

### 4.5 Dependency Inversion Principle

ApprovalService receives booking operations through
constructor injection.

This supports modularity and isolated unit testing.

## 5. Code Quality and Static Analysis

Tool: Pylint

Command:

    python -m pylint app

Observed result:

    Your code has been rated at 10.00/10

The role-policy implementation initially received
warnings about unused parameters and classes with
one public method.

Unused parameters were handled while preserving the
required protocol signature.

The one-method Strategy classes use documented Pylint
suppressions because they intentionally expose a narrow
interface.

## 6. Cyclomatic Complexity

Tool: Radon

Command:

    python -m radon cc app/approvals/service.py -s

Measured results:

| Component | Complexity | Grade |
|---|---|---|
| ApprovalService.approve | 1 | A |
| ApprovalService._require_admin | 2 | A |
| ApprovalService.reject | 1 | A |
| ApprovalService.list_pending | 1 | A |

All methods satisfy the project's complexity limit of 10.

The detailed Control Flow Graph and basis-path analysis
are documented in:

`docs/m2/umer-whitebox.md`


## 7. Test Coverage

Coverage was measured using pytest-cov.

Command executed:

    python -m pytest --cov=app --cov-report=term-missing

Environment: Python 3.12.10, Windows

Results:
- Total tests: 137 passed
- Warnings: 1
- Execution time: 10.78 seconds
- Total application coverage: 96%
- Statements measured: 845
- Statements missed: 33
- ApprovalService coverage: 100%

Selected module coverage:

| Module | Coverage |
|---|---|
| app/approvals/service.py | 100% |
| app/facilities/lookup.py | 96% |
| app/core/db.py | 87% |
| app/notifications/subscriber.py | 92% |
| app/users/security.py | 98% |
| app/notifications/setup.py | 0% |

The notification setup module remains uncovered in
this local test run. Final integration tests should
exercise notification registration.

The measured total coverage exceeds the project's
60% final coverage requirement.

These results describe the current local development
branch, not the final integrated M2 baseline.

FR-06 policies are not included in this branch's
coverage report because the policies PR has not yet
been incorporated into the tested branch.


## 8. Concurrency and Module Boundaries

The approvals module does not directly manage
database transactions or locking.

BookingService is responsible for preventing
conflicting confirmations and preserving booking
state/history consistency.

The approvals module delegates these operations
instead of implementing a second concurrency mechanism.

Concurrency evidence belongs primarily to
Hussnain's booking module and its integration tests.

## 9. Changes and Deviations from M1

FR-06 retains the planned Strategy design pattern.

FR-08 separates administrator authorization and
approval delegation from booking-state transitions.

ApprovalService uses the agreed PendingBookingActions
interface to coordinate with the Booking module.

No separate SQL repository is required for the
ApprovalService because it delegates persistence
and transitions to BookingService.

No completed Approval API integration is claimed
at this checkpoint.

## 10. Individual Contribution Summary

My implemented work includes:

1. Role-based duration strategies (FR-06).
2. Boundary-value unit tests for duration limits.
3. Policy factory and shared interface compatibility.
4. ApprovalService with administrator authorization.
5. PendingBookingActions interface.
6. Unit tests for approval/rejection delegation,
   authorization and domain exception propagation.
7. Pylint corrections and complexity analysis.

Associated SE431 documentation includes:

- umer-vv-plan.md
- rtm-v2.md
- risk-register-m2.md
- capa-log.md
- umer-whitebox.md

## 11. Remaining Evidence Before Submission

- Confirm the FR-06 PR is reviewed and merged.
- Complete FR-08 API tests and implementation.
- Obtain the approval workflow PR review and merge.
- Collect actual coverage output.
- Verify final integration test results on develop.
- Record AI-assisted development in the AI usage log.
- Confirm final SCM baseline and CI checks.
- Update this report with actual final evidence.

## 12. References

- `app/approvals/policies.py`
- `app/approvals/service.py`
- `tests/approvals/test_policies.py`
- `tests/approvals/test_approval_service.py`
- `app/core/interfaces.py`
- `app/core/exceptions.py`
- `docs/architecture-contract.md`
- `docs/m2/team-plan.md`
- `docs/m2/umer-whitebox.md`
- M1 SE423 design report
- GitHub PR #12 and feature branch commit history

## Final Contribution and Integration Update - 19 November 2026

Completed FR-06 role-based approval policies and FR-08 approval service/API, including pending booking retrieval, approval, rejection, and administrator authorization.

Used test-first commits followed by implementation commits. Final approval API implementation commit: fb63bee.

Reviewed Hussnain's Booking Core PR #15 and posted an integration review comment.

Final local quality evidence: 207 tests passed (11.91 seconds), 0 failed, 1 warning; Pylint 10.00/10.

Approval Workflow PR submitted for review. Merge into develop remains subject to review and CI.
