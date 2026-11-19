
# CFBS Milestone 2 — CAPA Log

**Prepared by:** Muhammad Umer
**Course:** SE431 — Software Quality Assurance
**Date:** 19 November 2026
**Status:** Working log; inspection findings pending

## 1. Purpose

This Corrective and Preventive Action (CAPA) log tracks
actual defects, development issues and quality findings
identified during CFBS Milestone 2.

Each entry records the source, severity, action, owner,
status and verification evidence.

An identified risk is not automatically a confirmed defect.
Risks are tracked separately in risk-register-m2.md.

## 2. CAPA Register

| ID | Source | Finding / Issue | Severity | Corrective or Preventive Action | Owner | Status | Evidence |
|---|---|---|---|---|---|---|---|
| CAPA-01 | Local pytest execution | Windows Application Control blocked the SQLAlchemy compiled extension | Medium | Reinstalled the pinned SQLAlchemy version from source without binary extensions | Muhammad Umer | Resolved locally | Subsequent pytest run: 124 passed; later full suite: 137 passed |
| CAPA-02 | Pylint, FR-06 | Seven Pylint findings: unused parameters and too-few-public-methods | Low | Addressed unused parameters and justified single-method Strategy classes with inline suppressions | Muhammad Umer | Fixed locally | Pylint improved from 9.91/10 to 10.00/10; implementation commit 252f1d9 |
| CAPA-03 | Integration status review | Approval API depends on BookingService and its FastAPI dependency being integrated | Medium | Complete booking integration, add approval API tests first, then implement and verify the endpoints | Muhammad Umer / Hussnain Abbas | Open | Approval service commit 53a84a6; Booking API implementation not confirmed |
| CAPA-04 | SCM review | FR-06 PR initially targeted main instead of develop | Medium | Changed PR #12 base branch to develop; verify review and merge checks | Muhammad Umer | Corrected; merge pending | PR #12 |
| CAPA-05 | M2 quality evidence review | Final merged-build coverage and concurrency results not yet collected | Medium | Execute checks on integrated develop and record actual results in RTM and risk register | Muhammad Bilal / Muhammad Hussnain Abbas | Open | Final CI/test evidence pending |

## 3. Corrective Action Verification

CAPA-01:
The local Python environment subsequently ran the
existing project tests successfully. The workaround
does not establish compatibility on every machine.

CAPA-02:
Pylint reported 10.00/10 after the code changes.
The single-method policies intentionally implement
the shared BookingPolicy interface.

CAPA-03:
This integration dependency remains open. It should
be checked after Hussnain's Booking API is merged.

CAPA-04:
The PR base was corrected to develop. Merge status
and required review must still be confirmed.

CAPA-05:
Final evidence must come from executed tests and CI,
not estimated values.

## 4. Inspection Findings

The formal Fagan-style inspection is scheduled
separately by the instructor.

No inspection defects are recorded yet because
the inspection has not been performed.

After the inspection, add each confirmed finding
with its identifier, severity, owner, correction,
verification evidence and closure status.

## 5. Closure Criteria

An item may be marked closed when:

1. The corrective action is implemented.
2. The affected functionality has been verified.
3. Supporting evidence is recorded.
4. Any required reviewer confirms resolution.

Open or deferred items must retain an owner and
an explicit reason.

## 6. References

- docs/m2/risk-register-m2.md
- docs/m2/rtm-v2.md
- docs/m2/umer-vv-plan.md
- GitHub PR #12
- FR-06 implementation commit 252f1d9
- FR-08 service implementation commit 53a84a6
- Local pytest and Pylint output

**Final update required:** Reconcile this log with
Hussnain's static-analysis findings, review comments,
integration failures and later inspection findings.

## Final Verification Follow-up � 19 November 2026

The Approval API integration gap has been addressed through the three FR-08 endpoints, using the existing BookingService dependency and BookingOut schema.

Verification: 207 local tests passed, 0 failed; Pylint 10.00/10.

Remaining process action: obtain PR approval, successful CI checks, and merge into develop. This is a review/integration action, not an unresolved local test failure.
