# Milestone 2 team plan

Prepared by Danish Ahmed (M2 SE431 lead) and shared with the team on 18 Nov 2026. Deadline for both
courses: Thursday 19 Nov 2026, 23:59 PKT. The Fagan inspection with the paired team takes place
after this date, at the instructor's direction.

## 1. Ownership and M2 deliverables

| Member | SE423 module | SE431 M2 deliverable | M2 role |
|---|---|---|---|
| Danish Ahmed | User and Access (FR-01), Notifications (FR-10), shared skeleton | Inspection organisation and moderation; SE431 report assembly | M2 SE431 lead |
| Muhammad Bilal | Facility Management (FR-02, FR-03) | Black-box test design (EP, BVA) traced to the RTM | M2 SE423 lead: merges, CI, integration, SE423 report |
| Muhammad Hussnain Abbas | Booking and Scheduling (FR-03, FR-04, FR-05, FR-07, FR-09), concurrency test, `BookingEventPublisher` | Static analysis report (Pylint), findings triaged | |
| Muhammad Umer | Approval and Policies (FR-06, FR-08), Strategy pattern | V&V plan (IEEE 1012); RTM v2, risk register and CAPA update | |

Every member also delivers a white-box analysis (CFG, cyclomatic complexity, basis paths) of one
key method of their own module, a section file in `docs/m2/`, and their rows in
`docs/ai-usage-log.md`.

## 2. Interfaces between modules

Services depend on the Protocols in `app/core/interfaces.py`, so each module is developed and unit
tested against fakes, in parallel, and connected at integration.

| Provided by | Interface | Used by |
|---|---|---|
| Facilities (Bilal) | `SqlFacilityLookup` implements `FacilityLookup` | Bookings |
| Approvals (Umer) | `StudentPolicy`, `FacultyPolicy`, `AdminPolicy`, `policy_for(role)` implement `BookingPolicy` (Strategy) | Bookings |
| Bookings (Hussnain) | `BookingEventPublisher` implements `EventPublisher` (Observer source) | Notifications, integration |
| Bookings (Hussnain) | `confirm_pending`, `reject_pending`, `list_pending` | Approvals (through its own `PendingBookingActions` Protocol) |
| Notifications (Danish) | `NotificationSubscriber` (Observer listener), `register_notifications(publisher, session_factory, executor)` | Integration (`app/main.py`) |
| User and Access (Danish) | `get_current_user`, `require_role` (Bearer tokens) | All routers |

Agreed behaviour: student bookings at most 2 h, faculty at most 4 h, administrators no duration
cap but no bypass of overlap, hours or block checks (M1 assumptions). Requests for restricted
facilities are stored as PENDING and do not reserve the slot; approval rechecks availability in
the same transaction as the status change. Every status change writes a `booking_history` row in
that same transaction, and booking events are published only after the commit.

## 3. Branches and merge order

All work is on `feature/<module>-<topic>` branches from `develop`, merged by pull request with a
merge commit (never squash), after review by the member's review partner.

Review ring: Danish reviews Umer; Umer reviews Hussnain; Hussnain reviews Bilal; Bilal reviews
Danish.

| Order | Branch | Owner |
|---|---|---|
| 1 | `feature/users-auth`, `feature/notifications` | Danish |
| 2 | `feature/facilities-management`, `feature/approvals-policies` | Bilal, Umer |
| 3 | `feature/bookings-core` | Hussnain |
| 4 | `feature/approvals-workflow`, `feature/integration-wiring` | Umer, Bilal |
| 5 | documentation branches (`docs/m2/` files, AI-log rows) | each member |
| 6 | `develop` -> `main`, tagged `m2-baseline` | Bilal |

## 4. Timeline (PKT)

| When | Milestone |
|---|---|
| Wed 18 Nov, night | Every member set up, branch created, first `test:` commit pushed |
| Thu 19 Nov, 13:00 | Facilities and policies merged |
| Thu 19 Nov, 17:30 | Bookings merged |
| Thu 19 Nov, 19:00 | Approvals workflow and integration wiring merged; static analysis run on `develop` |
| Thu 19 Nov, 20:30 | All `docs/m2/` files and AI-log rows merged |
| Thu 19 Nov, 21:00 | `m2-baseline` tag on `main` |
| Thu 19 Nov, 23:30 | Both reports submitted on Teams |

## 5. Definition of done for M2

- Tests committed before the implementation they drive (`test:` then `feat:` commits), all
  green on CI, coverage measured with pytest-cov.
- `python -m pylint app` clean or each suppression justified inline; Radon complexity 10 or less.
- Module boundaries as in the M1 design; any deviation stated and justified in the owner's
  section file.
- Pull request reviewed by the review partner with at least one real comment, merged with a
  merge commit.
- Owner can explain every line of their module and every claim in their section file.
- AI use recorded in `docs/ai-usage-log.md` by the member who used it.
