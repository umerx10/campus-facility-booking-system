
# M2 SE431 - White-Box Testing and Control Flow Analysis

**Prepared by:** Muhammad Umer
**Module:** Approvals and Policies (FR-08)
**Method:** ApprovalService.approve()
**Source:** app/approvals/service.py
**Milestone:** M2

## 1. Purpose

This white-box analysis examines administrator
authorization and booking approval delegation.

The analysis includes:
- Control Flow Graph (CFG)
- Cyclomatic complexity
- Independent basis paths
- Derived test cases
- Corresponding automated tests

The analysis uses the actual M2 implementation.

## 2. Method Under Analysis

```python
@staticmethod
def _require_admin(actor: CurrentUser) -> None:
    if actor.role != Role.ADMIN:
        raise UnauthorizedOperation(
            "Only administrators can manage booking approvals"
        )

def approve(self, booking_id: int, actor: CurrentUser) -> Booking:
    self._require_admin(actor)
    return self._booking_actions.confirm_pending(booking_id, actor)
```

The approve method delegates approval to the
booking service only after verifying administrator access.

The booking service owns the booking-state transition,
conflict checks, and database operations.

## 3. Control Flow Graph

The following is an interprocedural conceptual CFG:
it includes the call to _require_admin.

```mermaid
flowchart TD
    A([Start approve]) --> B[Call _require_admin]
    B --> C{Actor role is ADMIN?}
    C -->|No| D[Raise UnauthorizedOperation]
    C -->|Yes| E[Call confirm_pending]
    E --> F[Return booking]
    D --> G([Exit])
    F --> G
```

The decision is whether the actor has the ADMIN role.

For a non-admin user, execution terminates through
UnauthorizedOperation.

For an admin user, the request is delegated to the
booking service.

Any BookingConflict or NotFound raised by the
booking service propagates to the caller unchanged.


## 4. Cyclomatic Complexity

Cyclomatic complexity measures the number of linearly
independent execution paths through a method.

McCabe's formula:

V(G) = E - N + 2P

For the combined conceptual CFG of approval and authorization:

- Nodes (N): 7
- Edges (E): 7
- Connected components (P): 1
- Exit nodes: 1

V(G) = 7 - 7 + 2 = 2

Alternatively:

V(G) = Number of decision points + 1
     = 1 + 1
     = 2

The decision is whether the actor has the ADMIN role.

### Actual Radon Results

Command executed:

    python -m radon cc app/approvals/service.py -s

| Component | Radon Complexity | Grade |
|---|---|---|
| ApprovalService.approve | 1 | A |
| ApprovalService._require_admin | 2 | A |
| ApprovalService.reject | 1 | A |
| ApprovalService.list_pending | 1 | A |
| ApprovalService (class average) | 2 | A |

The approve method itself contains no decision, so
its individual cyclomatic complexity is 1.

The _require_admin method contains one conditional,
giving cyclomatic complexity 2.

The combined conceptual authorization and approval
flow has two independent basis paths.

All methods meet the project complexity limit of 10.


## 5. Independent Basis Paths

### Path P1 - Authorized administrator

Start -> Authorization check -> ADMIN ->
confirm_pending -> Return booking -> Exit

Expected result:
The booking action is invoked once and the returned
booking is forwarded to the caller.

### Path P2 - Unauthorized actor

Start -> Authorization check -> Non-ADMIN ->
UnauthorizedOperation -> Exit

Expected result:
The request is rejected before confirm_pending is called.

These two paths cover both outcomes of the authorization
decision.

## 6. Derived Basis-Path Test Cases

| Test ID | Path | Input | Expected Result | Automated Test |
|---|---|---|---|---|
| WB-UM-01 | P1 | ADMIN, booking_id=10 | confirm_pending called once; result returned | test_admin_can_approve_booking |
| WB-UM-02 | P2 | STUDENT, booking_id=10 | UnauthorizedOperation; no delegation | test_non_admin_cannot_approve |
| WB-UM-03 | P2 | FACULTY, booking_id=10 | UnauthorizedOperation; no delegation | test_non_admin_cannot_approve |

Additional exception-propagation tests:

| Test ID | Input | Expected Result | Automated Test |
|---|---|---|---|
| WB-UM-04 | ADMIN; fake action raises BookingConflict | Original BookingConflict propagates | test_approve_propagates_domain_errors |
| WB-UM-05 | ADMIN; fake action raises NotFound | Original NotFound propagates | test_approve_propagates_domain_errors |

The last two cases verify exception propagation.
They do not create additional independent branches
inside ApprovalService.approve().

## 7. Test Implementation

Test file:

tests/approvals/test_approval_service.py

The tests use fake booking operations created with
unittest.mock.Mock.

This isolates approval authorization from the database
and allows the booking service to return controlled
values or raise domain exceptions.

The tests verify:
- Correct delegation for administrators.
- Rejection of unauthorized actors.
- No downstream operation after access denial.
- Propagation of domain exceptions.

## 8. SOLID and Design Analysis

### Single Responsibility Principle

ApprovalService coordinates approval authorization
and delegates booking changes to BookingService.

It does not directly modify the database.

### Dependency Inversion Principle

ApprovalService depends on PendingBookingActions,
a typing.Protocol rather than a concrete
BookingService implementation.

This allows fake dependencies during unit testing.

### Interface Segregation Principle

PendingBookingActions exposes only the three booking
operations required by the approval module:
confirm_pending, reject_pending, and list_pending.

## 9. Verification Evidence

Implementation:
- app/approvals/service.py
- Branch: feature/approvals-workflow
- Implementation commit: 53a84a6

Locally observed evidence:
- Full test suite: 137 passed, 1 warning
- Pylint: 10.00/10

These results were recorded after the approval
service implementation.

The actual Radon output and final integration
results must be added after running the commands
below and after the module is integrated.

## 10. Conclusion

The approval authorization logic has two
independent execution paths.

The existing unit tests exercise the allowed
and rejected authorization outcomes.

ApprovalService delegates booking-state changes
instead of duplicating BookingService logic,
supporting modularity and maintainability.

Full FR-08 validation additionally requires
approval API and integrated booking-state tests.
