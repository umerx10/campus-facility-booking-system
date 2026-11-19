
# CFBS Milestone 2 — Updated Risk Register

**Prepared by:** Muhammad Umer
**Course:** SE431 — Software Quality Assurance
**Date:** 19 November 2026
**Status:** Working draft; update after final M2 integration

## 1. Purpose

This register updates the seven risks identified in the M1
SE431 report (R1–R7), incorporating available M2 implementation,
testing and repository evidence.

New risks R8 and R9 address problems discovered during M2.

## 2. Risk Assessment Method

Probability (P) and Impact (I):
- Low = 1
- Medium = 2
- High = 3

Priority = Probability × Impact.

- 1–2: Low
- 3–4: Medium
- 6–9: High

Residual risk is the estimated remaining risk after implemented
or planned mitigation. It is not proof that the risk is resolved.

## 3. Updated Risk Register

| ID | Risk | P | I | Priority | Owner | M2 Status | Residual Risk |
|---|---|---|---|---|---|---|---|
| R1 | Double booking under concurrent requests | 2 | 3 | 6 High | Hussnain Abbas | Mitigation implemented in booking branch; concurrency execution pending | 2 Low (target; unverified) |
| R2 | Unauthorized approval or data access | 2 | 3 | 6 High | Danish Ahmed | Authentication merged; approval authorization implemented on feature branch | 2 Low (target; unverified) |
| R3 | Insufficient TDD evidence or coverage | 2 | 3 | 6 High | Muhammad Umer | Separate test/implementation commits exist; final coverage pending | 2 Low (target; unverified) |
| R4 | Database inconsistency on failure | 2 | 3 | 6 High | Hussnain Abbas | Transaction strategy and history implementation exist; integration verification pending | 2 Low (target; unverified) |
| R5 | Unclear requirements or scope growth | 2 | 2 | 4 Medium | Muhammad Bilal | Architecture contract and M2 team plan established | 2 Low (target; unverified) |
| R6 | Integration or merge conflicts | 2 | 2 | 4 Medium | Muhammad Umer | Feature branches and PR reviews used; several modules remain unmerged | 1 Low (target; unverified) |
| R7 | Missing SQA artifacts near deadline | 2 | 3 | 6 High | Muhammad Umer | V&V plan and RTM drafted; remaining reports and evidence pending | 2 Low (target; unverified) |
| R8 | Delayed implementation and integration of dependent modules | 3 | 3 | 9 High | Muhammad Bilal | Booking API and approval integration pending at latest observed checkpoint | 4 Medium (estimated after mitigation) |
| R9 | Differences between local and CI development environments | 2 | 2 | 4 Medium | Muhammad Umer | Local SQLAlchemy DLL blocking resolved through source installation; CI validation still needed | 2 Low (estimated after mitigation) |

## 4. Mitigation and M2 Evidence

| Risk | Mitigation / Corrective Action | Available Evidence | Remaining Action |
|---|---|---|---|
| R1 | Atomic database transactions and concurrent booking tests | `app/core/db.py`; booking concurrency tests committed in `c2bff47` | Confirm 100 competing pairs and zero overlaps |
| R2 | Role-based guards, authorization tests and review | Authentication merged; approval service commit `53a84a6` | Complete Approval API authorization tests |
| R3 | Separate Red-Green commits and CI coverage checks | FR-06 PR #12; FR-08 service test and implementation commits | Collect final coverage report |
| R4 | Foreign-key constraints, atomic status/history writes and failure tests | Database skeleton and booking implementation | Verify rollback and history consistency |
| R5 | Requirements baseline, RTM updates and change review | `docs/architecture-contract.md`, `docs/m2/team-plan.md` | Review final changes against M1 |
| R6 | Small PRs, peer review, merge commits and CI gates | Facilities PR #10 merged; Policies PR #12 open at latest check | Merge and verify remaining modules |
| R7 | Named document owners and regular evidence checks | `umer-vv-plan.md`, `rtm-v2.md` drafted | Finish CAPA, white-box and SE423 section |
| R8 | Prioritize essential features and integrate dependencies in order | Booking implementation progressing on feature branch | Complete Booking API, Approval API and integration |
| R9 | Match supported Python environment and record reproducible installation steps | Python 3.12.10; SQLAlchemy source installation; 137 local tests passed | Validate on CI and document environment issue |

## 5. Evidence-Based Changes from M1

### R1 — Concurrent Double Booking

The M1 mitigation proposed atomic transactions and concurrent
integration tests.

M2 introduced a SQLite transaction strategy using BEGIN IMMEDIATE.

At the latest observed checkpoint, concurrency tests had been
committed, but their successful execution was not verified.

Therefore, R1 remains open.

### R2 — Unauthorized Access

Authentication has been merged into develop.

Umer implemented administrator checks in ApprovalService,
with tests covering non-admin attempts.

Full API-level authorization and integration verification
remain necessary before closing this risk.

### R3 — TDD Evidence and Coverage

Separate test and implementation commits exist for the
FR-06 and FR-08 service work.

The latest locally reported complete test suite passed
137 tests with one warning.

This verifies local regression-test success, but does not
establish the final coverage percentage.

R3 ownership is assigned to Muhammad Umer instead of
the ambiguous M1 designation "All members".

### R4 — Database Consistency

M2 uses transactional booking changes and history writes
instead of the originally proposed asynchronous
HistorySubscriber.

The change aims to ensure booking status and history are
updated atomically.

Failure-injection and integration evidence are still required.

### R5 and R6 — Requirements and Integration

The team established architecture contracts, named
module ownership, feature branches and pull requests.

These controls reduce ambiguity but do not eliminate
merge or integration risk.

### R7 — SQA Artifact Completion

Documentation responsibilities are allocated.

The V&V plan and RTM v2 have been drafted, but static
analysis, inspection evidence, CAPA updates and final
report integration must still be completed.

## 6. New Risks Discovered During M2

### R8 — Late Module Integration

**Cause:** Dependent booking and approval modules are being
implemented close to the submission deadline.

**Impact:** Incomplete end-to-end functionality, delayed
testing or missing integration evidence.

**Mitigation:** Prioritize must-have features, merge in the
agreed dependency order and keep CI green.

**Owner:** Muhammad Bilal.

### R9 — Local Environment Differences

**Cause:** Developer machines may use different Python
versions or enforce different Windows application policies.

**Observed issue:** SQLAlchemy's compiled extension was
blocked on one Windows machine.

**Mitigation:** Use Python 3.12 where possible, retain
pinned dependencies, document the source-install workaround,
and verify behavior through CI.

**Owner:** Muhammad Umer.

## 7. Risk Monitoring and Closure

Risk updates must be tied to observable evidence.

A risk may be closed only after its mitigation has been
implemented and verified, with an appropriate test,
review, CI run or inspection record.

Remaining risks will be reassessed for M3.

The CAPA log records concrete defects and corrective
actions; this risk register tracks possible future
failures and their consequences.

## 8. References

- `.claude-local/m1-se431-report.tex` — Original R1–R7
- `docs/architecture-contract.md`
- `docs/m2/team-plan.md`
- `docs/m2/rtm-v2.md`
- `docs/m2/umer-vv-plan.md`
- GitHub commits and pull requests
- Automated test and static-analysis results

**Final review required:** Update statuses, residual risks
and evidence after all M2 module merges and CI checks.
