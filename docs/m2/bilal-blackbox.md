# Black-box test design: equivalence partitioning and boundary values (Muhammad Bilal, M2 SE431)

Scope: the inputs named in the M2 team plan for FR-01, FR-02, FR-04, FR-05, FR-06 and FR-08, plus
the operating-hours input of FR-03 that my module implements. For each input: the equivalence
classes (V = valid, I = invalid), the boundary values, then the derived test cases. Test case IDs
are `TC-<FR>-<n>`; Umer uses the same IDs in RTM v2.

Implementing tests are named as `file::test[parameter id]`. First written on 18 Nov 2026 against
`develop` at `1ee09df` (after PR #10); updated on 19 Nov 2026 with the tests of the approvals
policies PR (#12) and the bookings PR (`feature/bookings-core`). A case marked **planned for M3**
has no test in M2.

Assumptions (M1 and team plan): booking intervals are half-open `[start, end)`; student bookings at
most 120 minutes, faculty at most 240, admin no cap; datetimes are naive UTC.

## 1. FR-01 Login (`POST /auth/login`)

| Input | Equivalence classes | Boundary values |
|---|---|---|
| email | V1 well-formed and registered; I1 empty; I2 malformed (no `@`/domain); I3 well-formed but unknown | length 0 (I1) |
| password | V2 matches the stored hash; I4 empty; I5 non-empty but wrong | length 0 (I4) |

| TC | Input | Expected | Req | Implementing test |
|---|---|---|---|---|
| TC-01-01 | known email, right password (V1, V2) | 200, bearer token for that user | FR-01 | `tests/users/test_auth_api.py::test_login_with_valid_credentials_returns_a_bearer_token` |
| TC-01-02 | empty email (I1) | 422 | FR-01 | `tests/users/test_auth_api.py::test_login_with_empty_or_malformed_input_returns_422[-correct-horse]` |
| TC-01-03 | `not-an-email` (I2) | 422 | FR-01 | `tests/users/test_auth_api.py::test_login_with_empty_or_malformed_input_returns_422[not-an-email-correct-horse]` |
| TC-01-04 | unknown well-formed email (I3) | 401, same message as TC-01-06 | FR-01, QR-04 | `tests/users/test_auth_api.py::test_wrong_password_and_unknown_email_get_the_same_401` |
| TC-01-05 | empty password (I4) | 422 | FR-01 | `tests/users/test_auth_api.py::test_login_with_empty_or_malformed_input_returns_422[student@example.com-]` |
| TC-01-06 | known email, wrong password (I5) | 401 | FR-01, QR-04 | `tests/users/test_auth_api.py::test_wrong_password_and_unknown_email_get_the_same_401` |

## 2. FR-02 Facility input (`POST /facilities`, `PATCH /facilities/{id}`)

| Input | Equivalence classes | Boundary values |
|---|---|---|
| name | V3 1-100 characters; I6 empty; I7 over 100 characters; I8 missing | 0, 1, 100, 101 |
| capacity | V4 integer >= 1; I9 0; I10 negative; I11 missing | 0, 1, large (no upper limit in M2) |
| caller role | V5 ADMIN; I12 STUDENT or FACULTY; I13 not authenticated | - |

| TC | Input | Expected | Req | Implementing test |
|---|---|---|---|---|
| TC-02-01 | name length 0 | 422, nothing stored | FR-02 | `tests/facilities/test_facility_api.py::test_invalid_facility_input_returns_422[payload0-empty name (length 0)]` |
| TC-02-02 | name length 1 | 201 | FR-02 | `tests/facilities/test_facility_api.py::test_boundary_valid_facility_input_is_accepted[name length 1]` |
| TC-02-03 | name length 100 | 201 | FR-02 | `tests/facilities/test_facility_api.py::test_boundary_valid_facility_input_is_accepted[name length 100]` |
| TC-02-04 | name length 101 | 422 | FR-02 | `tests/facilities/test_facility_api.py::test_invalid_facility_input_returns_422[payload1-name length 101]` |
| TC-02-05 | capacity 0 | 422 | FR-02 | `tests/facilities/test_facility_api.py::test_invalid_facility_input_returns_422[payload2-capacity 0]` |
| TC-02-06 | capacity 1 | 201 | FR-02 | `tests/facilities/test_facility_api.py::test_boundary_valid_facility_input_is_accepted[capacity 1]` |
| TC-02-07 | capacity -5 | 422 | FR-02 | `tests/facilities/test_facility_api.py::test_invalid_facility_input_returns_422[payload3-negative capacity]` |
| TC-02-08 | capacity 10000 (large) | 201 | FR-02 | planned for M3 |
| TC-02-09 | name or capacity missing | 422 | FR-02 | `tests/facilities/test_facility_api.py::test_invalid_facility_input_returns_422[payload4-missing name]`, `[payload5-missing capacity]` |
| TC-02-10 | PATCH capacity 0 | 422, record unchanged | FR-02 | `tests/facilities/test_facility_api.py::test_update_with_invalid_capacity_returns_422` |
| TC-02-11 | valid body as STUDENT / FACULTY | 403, nothing stored | FR-02, QR-04 | `tests/facilities/test_facility_api.py::test_non_admin_cannot_create_facility[STUDENT]`, `[FACULTY]` |
| TC-02-12 | no token | 401 | FR-02, QR-04 | `tests/facilities/test_facility_api.py::test_requests_without_authentication_return_401[post-/facilities]` |

## 3. FR-03 Operating hours (`SqlFacilityLookup.is_within_hours`)

Facility open Monday 08:00-20:00, no row for Tuesday.

| Input | Equivalence classes | Boundary values |
|---|---|---|
| start time | V6 >= opens_at; I14 before opens_at | 08:00 (= opens_at), 07:59 |
| end time | V7 <= closes_at; I15 after closes_at | 20:00 (= closes_at), 20:01 |
| weekday | V8 has an hours row; I16 no row (closed) | - |
| days spanned | V9 start and end on the same date; I17 different dates | - |

| TC | Input (Mon 23 Nov 2026 unless stated) | Expected | Req | Implementing test |
|---|---|---|---|---|
| TC-03-01 | 08:00-09:00 | True | FR-03 | `tests/facilities/test_lookup.py::test_is_within_hours[start == opens_at]` |
| TC-03-02 | 07:59-09:00 | False | FR-03 | `tests/facilities/test_lookup.py::test_is_within_hours[start one minute before opening]` |
| TC-03-03 | 19:00-20:00 | True | FR-03 | `tests/facilities/test_lookup.py::test_is_within_hours[end == closes_at]` |
| TC-03-04 | 19:00-20:01 | False | FR-03 | `tests/facilities/test_lookup.py::test_is_within_hours[end one minute after closing]` |
| TC-03-05 | Tue 09:00-10:00 | False | FR-03 | `tests/facilities/test_lookup.py::test_is_within_hours[no hours row for that weekday]` |
| TC-03-06 | Mon 19:00 - Tue 09:00 | False | FR-03 | `tests/facilities/test_lookup.py::test_is_within_hours[start and end on different days]` |
| TC-03-07 | hours row with weekday 7 or -1 | 422 | FR-03 | `tests/facilities/test_schedule_api.py::test_invalid_hours_return_422[weekday 7]`, `[weekday -1]` |
| TC-03-08 | hours row with opens_at == closes_at | 422 | FR-03 | `tests/facilities/test_schedule_api.py::test_invalid_hours_return_422[opens_at == closes_at]` |

## 4. FR-04 Booking interval (`POST /bookings`, `BookingService.request_booking`)

Clock fixed at "now" by the injected clock.

| Input | Equivalence classes | Boundary values |
|---|---|---|
| end relative to start | V10 end > start; I18 end == start; I19 end < start | duration 0 min (I18), 1 min (V10) |
| start relative to now | V11 start >= now; I20 start < now | now, now - 1 min |

| TC | Input | Expected | Req | Implementing test |
|---|---|---|---|---|
| TC-04-01 | end one hour before start | `InvalidBookingTime` / 422 | FR-04 | `tests/bookings/test_booking_service.py::test_end_not_after_start_is_invalid[end before start]` |
| TC-04-02 | end == start | `InvalidBookingTime` / 422 | FR-04 | `tests/bookings/test_booking_service.py::test_end_not_after_start_is_invalid[end == start]` |
| TC-04-03 | 1-minute booking, free slot, inside hours | accepted (CONFIRMED) | FR-04 | planned for M3 |
| TC-04-04 | start in the past | `InvalidBookingTime` / 422 | FR-04 | `tests/bookings/test_booking_service.py::test_start_in_the_past_is_invalid` |

## 5. FR-05 Overlap with bookings and maintenance blocks (half-open)

Existing interval (a CONFIRMED booking or a maintenance block) `[10:00, 12:00)`.

| Input | Equivalence classes | Boundary values |
|---|---|---|
| request vs existing interval | V12 disjoint or back to back; I21 overlapping (partial or containing) | end == 10:00, start == 12:00 (V12); start 11:59 (I21) |
| facility | V13 another facility's interval is ignored | - |

| TC | Input | Expected | Req | Implementing test |
|---|---|---|---|---|
| TC-05-01 | block, request 12:00-13:00 | no overlap | FR-05 | `tests/facilities/test_lookup.py::test_overlaps_block[back to back after the block]` |
| TC-05-02 | block, request 09:00-10:00 | no overlap | FR-05 | `tests/facilities/test_lookup.py::test_overlaps_block[back to back before the block]` |
| TC-05-03 | block, request 11:59-12:30 | overlap | FR-05 | `tests/facilities/test_lookup.py::test_overlaps_block[starts one minute before the block ends]` |
| TC-05-04 | block, request 09:00-13:00 | overlap | FR-05 | `tests/facilities/test_lookup.py::test_overlaps_block[contains the block]` |
| TC-05-05 | block on another facility | no overlap | FR-05 | `tests/facilities/test_lookup.py::test_block_on_another_facility_does_not_overlap` |
| TC-05-06 | CONFIRMED booking, request overlapping it | `BookingConflict` / 409 | FR-05 | `tests/bookings/test_booking_service.py::test_overlapping_a_confirmed_booking_conflicts_and_publishes_nothing` |
| TC-05-07 | CONFIRMED booking, request back to back | CONFIRMED | FR-05 | `tests/bookings/test_booking_service.py::test_back_to_back_with_a_confirmed_booking_is_allowed` |
| TC-05-08 | request overlapping a block | `FacilityUnavailable` / 409 | FR-05 | `tests/bookings/test_booking_service.py::test_overlapping_a_maintenance_block_is_unavailable` |

## 6. FR-06 Duration by role

| Input | Equivalence classes | Boundary values |
|---|---|---|
| student duration | V14 <= 120 min; I22 > 120 min | 119, 120, 121 |
| faculty duration | V15 <= 240 min; I23 > 240 min | 239, 240, 241 |
| admin duration | V16 any length (no cap) | 600 min |

| TC | Input | Expected | Req | Implementing test |
|---|---|---|---|---|
| TC-06-01 | student 119 min | allowed | FR-06 | `tests/approvals/test_policies.py::test_student_accepts_allowed_duration[119]` |
| TC-06-02 | student 120 min | allowed | FR-06 | `tests/approvals/test_policies.py::test_student_accepts_allowed_duration[120]` |
| TC-06-03 | student 121 min | `PolicyViolation` / 422 | FR-06 | `tests/approvals/test_policies.py::test_student_rejects_121_minutes` |
| TC-06-04 | faculty 239 min | allowed | FR-06 | `tests/approvals/test_policies.py::test_faculty_accepts_allowed_duration[239]` |
| TC-06-05 | faculty 240 min | allowed | FR-06 | `tests/approvals/test_policies.py::test_faculty_accepts_allowed_duration[240]` |
| TC-06-06 | faculty 241 min | `PolicyViolation` / 422 | FR-06 | `tests/approvals/test_policies.py::test_faculty_rejects_241_minutes` |
| TC-06-07 | admin 600 min | allowed | FR-06 | `tests/approvals/test_policies.py::test_admin_accepts_ten_hours` |

## 7. FR-08 Approval state

| Input | Equivalence classes |
|---|---|
| booking status at decision time | V17 PENDING; I24 CONFIRMED, REJECTED or CANCELLED |
| decision | approve, reject |

| TC | Input | Expected | Req | Implementing test |
|---|---|---|---|---|
| TC-08-01 | approve a PENDING booking, slot free | CONFIRMED, history row, `BookingConfirmed` | FR-08 | `tests/bookings/test_booking_service.py::test_confirm_pending_confirms_with_history_and_event_after_commit` |
| TC-08-02 | approve a CONFIRMED booking | `BookingConflict` / 409 | FR-08 | `tests/bookings/test_booking_service.py::test_confirm_a_booking_that_is_not_pending_conflicts` |
| TC-08-03 | reject a PENDING booking | REJECTED, history row, `BookingRejected` | FR-08 | `tests/bookings/test_booking_service.py::test_reject_pending_rejects_with_history_and_event_after_commit` |
| TC-08-04 | approve a PENDING booking that now overlaps a CONFIRMED one | `BookingConflict` / 409 | FR-08, FR-05 | `tests/bookings/test_booking_service.py::test_confirm_pending_that_now_overlaps_a_confirmed_booking_conflicts` |

## 8. Summary

49 test cases: 47 implemented by pytest tests (TC-01 to TC-08 except the two below) and 2 planned
for M3 (TC-02-08 large capacity, TC-04-03 one-minute booking). Tests come from four members'
modules: users (Danish), facilities (Bilal), bookings (Hussnain) and approvals (Umer).
