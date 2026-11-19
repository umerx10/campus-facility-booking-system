
# M2 SE431: Verification and Validation Plan (IEEE 1012)

**Prepared by:** Muhammad Umer  
**Project:** Campus Facility Booking System (CFBS)  
**Milestone:** M2 — SE431 Software Quality Assurance  
**Date:** 19 November 2026  
**Status:** Working plan; final evidence to be updated after M2 integration

## 1. Purpose and Scope

This Verification and Validation (V&V) plan defines how the CFBS
team will assess whether the implemented system satisfies its
functional and quality requirements.

The plan follows the principles of IEEE 1012 and uses the
requirements established in the M1 SE431 report:

- Functional requirements: FR-01 to FR-10
- Quality requirements: QR-01 to QR-08

The M2 focus is on architecture, design patterns, automated
testing, concurrency, static analysis, inspection, and SCM
evidence.

Remaining validation and final quality measurements are planned
for M3.

## 2. System Integrity Level

CFBS is an academic facility-booking application rather than
a safety-critical system.

For this project, a relatively low integrity level is proposed,
with risk-based strengthening of verification for authorization,
double-booking prevention, and booking-state consistency.

This is a project-specific integrity assessment, not a formally
certified IEEE 1012 integrity-level determination.

The highest-priority concerns are:

- Double booking under simultaneous requests (R1).
- Unauthorized access or approval (R2).
- Insufficient TDD evidence or coverage (R3).
- Database inconsistency during failures (R4).

These areas require stronger negative, integration, and
concurrency testing than ordinary display operations.

## 3. Verification vs Validation

**Verification:** Are we building the system correctly?

Verification checks whether the code and design conform to
requirements, architecture contracts, coding rules, and
technical specifications.

**Validation:** Are we building the right system?

Validation checks whether the running application meets the
needs of students, faculty, and administrators.

Both activities are required because passing unit tests does
not by itself prove that the system meets user expectations.

## 4. Verification Activities

| ID | Activity | Requirements | Owner | Timing | Evidence |
|---|---|---|---|---|---|
| V-01 | Architecture and interface review | FR-01–10, QR-06 | All module owners | M2 | `docs/architecture-contract.md`, PR reviews |
| V-02 | Test-first unit testing | FR-01, FR-02, FR-04, FR-06, FR-08, FR-10; QR-01 | Respective module owners | M2 | `tests/`, separate test and implementation commits |
| V-03 | Database and API integration testing | FR-02–05, FR-07–10; QR-01, QR-04 | Bilal, Hussnain, Umer | M2/M3 | pytest integration and API test results |
| V-04 | Concurrency verification | FR-05, FR-08; QR-03 | Hussnain | M2 | `tests/bookings/test_concurrency.py`, database overlap query |
| V-05 | Static code analysis | QR-06 | Hussnain | M2 | `docs/m2/hussnain-static-analysis.md`, Pylint, Radon |
| V-06 | White-box analysis and basis paths | FR-02, FR-04, FR-06, FR-08; QR-06 | All module owners | M2 | Individual `docs/m2/*-whitebox.md` files |
| V-07 | Formal Fagan-style inspection | QR-01, QR-04, QR-06 | Danish coordinates | Instructor-scheduled | Inspection report, defect log, CAPA |
| V-08 | Requirements traceability audit | FR-01–10, QR-01–08 | Umer | M2/M3 | `docs/m2/rtm-v2.md` |
| V-09 | CI, code review, and baseline audit | QR-01, QR-06 | Bilal and reviewers | M2 | GitHub PRs, CI runs, `m2-baseline` tag |
| V-10 | Coverage and maintainability measurement | QR-06 | Module owners, Hussnain | M2/M3 | pytest-cov output, Radon report |

### 4.1 Test-Driven Development

The development process follows Red-Green-Refactor:

1. Write tests for the requirement.
2. Run the tests and observe the expected failure.
3. Commit the tests separately.
4. Implement the minimum required functionality.
5. Run the complete test suite.
6. Perform static analysis and commit the implementation.

For FR-06, Umer created role-policy boundary tests before
implementing the three strategies.

Evidence:
- Branch: `feature/approvals-policies`
- Implementation commit: `252f1d9`
- Pylint result: 10.00/10

For FR-08, Umer created approval service tests before the
implementation.

Evidence:
- Branch: `feature/approvals-workflow`
- Implementation commit: `53a84a6`
- Observed full-suite result: 137 passed, 1 warning
- Pylint result: 10.00/10

These are development-branch observations, not proof that all
M2 integration and acceptance criteria are complete.

### 4.2 Verification Exit Criteria

Verification is considered acceptable for the M2 baseline when:

- Implemented core functionality has passing automated tests.
- No known critical defect is left without an explicit disposition.
- Static analysis findings are resolved or justified.
- Required design patterns and interface contracts are reviewed.
- Module PRs pass the agreed quality checks.
- The RTM identifies implemented, partial, and planned work.
- Test results and code claims are supported by actual evidence.

## 5. Validation Activities

| ID | Validation activity | Requirements | Owner | Timing | Evidence |
|---|---|---|---|---|---|
| VAL-01 | Student and faculty login and access scenarios | FR-01; QR-01, QR-04 | Danish | M2/M3 | Authentication API tests, demonstration |
| VAL-02 | Facility creation, update, and viewing | FR-02, FR-03; QR-01 | Bilal | M2/M3 | Facility API tests and demo |
| VAL-03 | Valid booking, invalid intervals, and conflicts | FR-04, FR-05; QR-01, QR-03 | Hussnain | M2/M3 | Booking API and concurrency tests |
| VAL-04 | Booking duration limits by role | FR-06; QR-01 | Umer | M2 | Policy boundary tests |
| VAL-05 | Cancellation and rescheduling scenarios | FR-07; QR-01 | Hussnain | M2/M3 | Booking API tests; incomplete features tracked in RTM |
| VAL-06 | Restricted-facility approval and rejection | FR-08; QR-01, QR-04 | Umer, Hussnain | M2/M3 | Approval service/API and booking conflict tests |
| VAL-07 | Booking history and status visibility | FR-09; QR-01 | Hussnain | M2/M3 | History API and repository tests |
| VAL-08 | Notification delivery after state changes | FR-10; QR-08 | Danish, Bilal | M2/M3 | Notification integration tests |
| VAL-09 | Five-user booking usability pilot | QR-05 | Team, coordinated by Danish | Planned M3 | Scripted task observation |
| VAL-10 | Timed availability workload | QR-02 | Bilal | Planned M3 | Performance test results |
| VAL-11 | Fresh-install and operation check | QR-07 | Bilal and team | Planned M3 | Installation checklist |

### 5.1 Usability Acceptance Criterion

The M1 QR-05 target is that at least 4 out of 5 pilot users
complete a booking without help during a scripted trial.

This usability pilot is planned for M3. No completed pilot
result is claimed in this M2 working plan.

### 5.2 Additional Quality Acceptance Criteria

The following targets originate from the M1 baseline:

| Requirement | Acceptance criterion |
|---|---|
| QR-02 | At least 95% of availability queries complete within 2 seconds in the defined 20-user local test |
| QR-03 | Zero overlapping confirmed bookings across 100 competing booking-pair scenarios, including approval races |
| QR-04 | All tested unauthorized admin actions denied; passwords not stored in plaintext |
| QR-05 | At least 4 of 5 pilot users complete booking without help |
| QR-06 | At least 60% core business-logic coverage at final submission; booking/policy method cyclomatic complexity no greater than 10 |
| QR-07 | Fresh supported Python setup within 15 minutes, excluding dependency downloads |
| QR-08 | Zero event-contract mismatches in defined notification/history integration tests |

These are acceptance targets, not automatically achieved results.
Actual measurements must be recorded in the relevant evidence.

## 6. Responsibilities

| Member | Responsibility |
|---|---|
| Danish Ahmed | Users/authentication, notifications, SE431 coordination and inspection |
| Muhammad Bilal | Facilities, black-box test design, CI and integration, SE423 lead |
| Muhammad Hussnain Abbas | Booking operations, concurrency testing, static-analysis report |
| Muhammad Umer | Approval policies and workflow, V&V plan, RTM v2, risk register, CAPA |

Each member also performs white-box analysis, reviews assigned
pull requests, and maintains individually attributable evidence.

## 7. Defect Handling and Corrective Action

Defects may be identified through:

- Automated test failures.
- Static analysis.
- Code review.
- Integration checks.
- Formal inspection.

Each significant defect is recorded in
`docs/m2/capa-log.md` with an identifier, source, severity,
owner, corrective action, and status.

Critical and high-severity defects require correction or an
explicit documented disposition before baseline approval.

Formal inspection findings will be added when the instructor-
scheduled inspection has actually occurred.

## 8. Configuration Management and Evidence

The team uses Git feature branches and pull requests.

- Development is performed on feature branches.
- Pull requests target `develop`.
- Reviews and CI provide quality-gate evidence.
- Bilal merges approved PRs using merge commits.
- The M2 baseline is created from the integrated build.
- The baseline tag is `m2-baseline`.

Documentation must reference actual test output, commit
hashes, pull requests, and integration evidence.

A pushed feature branch is not equivalent to a merged and
verified integration baseline.

## 9. Remaining M3 Verification and Validation

The remaining milestone activities include:

- Completing and validating any partial FR-01–10 functionality.
- Running the full acceptance test suite.
- Executing the QR-02 performance workload.
- Conducting the QR-05 usability pilot.
- Performing the QR-07 clean-install assessment.
- Measuring final coverage and complexity against QR-06.
- Resolving or dispositioning open CAPA findings.
- Updating the final RTM and IEEE 730 SQAP.

## 10. References and Evidence Sources

1. `guidelines.txt` — SE423/SE431 joint project guidelines.
2. `m1-se431-report.tex` — M1 quality requirements, RTM v1, risks.
3. `m1-se423-report.tex` — M1 architecture and functional scope.
4. `docs/architecture-contract.md` — Binding M2 architecture.
5. `docs/m2/team-plan.md` — M2 team ownership and schedule.
6. `tests/` — Executable verification evidence.
7. GitHub branches, PRs and CI — SCM and review evidence.

**Evidence update required:** Review this plan after the
team's M2 pull requests merge. Verify all referenced test
files, actual results and baseline artifacts before submission.

## Final Verification Update � 19 November 2026

- Full integrated test suite: 207 passed, 0 failed, 1 warning (11.91 seconds).
- Static analysis: Pylint 10.00/10.
- FR-06 role policies verified through unit tests.
- FR-08 approval service and API verified through service and HTTP tests.
- Approval endpoints: GET /approvals/pending, POST /approvals/{booking_id}/approve, POST /approvals/{booking_id}/reject.
- Earlier test counts in this document represent intermediate milestones; 207 is the final verified local count.
