# CampusOps — Slice 5B Registration, Ticketing & Attendance Security Audit Report

**Date:** 29 October 2026  
**Auditor:** Antigravity Autonomous Pair Programming Agent  
**Repository:** `D:\Antigravity_Projects\CampusOps`  
**Branch:** `main` | **HEAD:** `282311a`  
**Status:** **PASSED & HARDENED** — 251 passing backend tests, 2 passing frontend tests, clean frontend production build, 0 staged changes, 0 commits.

---

## 1. Executive Summary & Audit Baseline

In accordance with Prompt 20, an independent security, relational integrity, and authorization audit was conducted against the completed Slice 5B domain foundation before proceeding to Slice 5C REST APIs.

### 1.1 Baseline Verification
Prior to introducing audit tests and hardening changes:
- Dynamic Pytest collected and passed **230 items** across 25 test files in 11.85s.
- `python -m pip check` verified clean dependencies with zero broken requirements.
- Frontend test suite passed **2 tests** in 1.62s.
- Frontend production build (`tsc -b && vite build`) transformed 17 modules and built in 171ms.
- `git diff --check` reported zero trailing whitespace or line-ending defects.

### 1.2 Hardened Post-Audit Verification
Following targeted security hardening, partial unique index migration, and audit test authoring:
- **Backend Test Suite:** **251 passed**, 1 warning in 8.14s (20 new comprehensive audit tests in [`test_slice_5b_security_audit.py`](file:///D:/Antigravity_Projects/CampusOps/backend/tests/test_slice_5b_security_audit.py) + 1 migration lifecycle test in [`test_migrations.py`](file:///D:/Antigravity_Projects/CampusOps/backend/tests/test_migrations.py)).
- **Frontend Test Suite:** **2 passed** in 1.05s.
- **Frontend Production Build:** Clean build in 107ms.
- **Git Hygiene:** 0 files staged, 0 commits, clean `git diff --check`.

---

## 2. Confirmed Findings, Severity & Remediations

| ID | Category | Severity | Finding Summary | Remediation Applied |
| :--- | :--- | :--- | :--- | :--- |
| **SEC-5B-01** | Database Concurrency | **High** | `registrations.idempotency_key` had non-unique index `ix_registrations_idempotency` (`unique=False`). Concurrent submissions bypassing service checks could insert duplicate registrations for the same event with identical idempotency keys. | Created additive Alembic migration `c8d9e0f1a2b3` replacing `ix_registrations_idempotency` with partial unique index `uq_registrations_event_idempotency` (`['event_id', 'idempotency_key'] WHERE idempotency_key IS NOT NULL`). Tested with direct database collision insert. |
| **SEC-5B-02** | Credential Security | **Medium** | `event_registration_settings.registration_key_hash` had non-unique index `ix_event_reg_settings_key_hash`, allowing different events to potentially share public registration keys. Also, `update_registration_settings` lacked key rotation. | Added partial unique index `uq_event_reg_settings_key_hash` (`['registration_key_hash'] WHERE registration_key_hash IS NOT NULL`) in migration `c8d9e0f1a2b3`. Implemented `generate_registration_key()` and added `rotate_registration_key: bool = False` in `update_registration_settings`. |
| **SEC-5B-03** | Query Crash / Edge Case | **Medium** | In `check_in_participant` (manual search), `Ticket.status.in_(["issued", "used"])` using `.scalar_one_or_none()` could raise SQLAlchemy `MultipleResultsFound` if a participant had both a used ticket and a replacement ticket. | Hardened manual search query to prioritize active `status == 'issued'` ticket, falling back to `status == 'used'` only if attendee was already checked in. Verified in `test_manual_check_in_multi_ticket_safety_no_multiple_results_found`. |
| **SEC-5B-04** | Lifecycle / Pass Leak | **Low** | In `issue_replacement_ticket`, only tickets with `status == "issued"` were revoked. If an attendee's badge was compromised after initial check-in, previous `"used"` passes remained in `"used"` status. | Updated `issue_replacement_ticket` to revoke all non-cancelled (`issued`, `used`) prior passes for that participant with audit timestamp and reason before issuing the fresh ticket. |
| **SEC-5B-05** | Scope / Transitive Archival | **Medium** | `_validate_event_and_settings_for_registration` and `update_registration_settings` checked `event.archived_at` but did not check parent program archival when `event.program_id` was set. | Hardened event and settings validation to verify that parent programs (`Program.archived_at is None`) are not archived before permitting registrations or opening registration windows. |
| **SEC-5B-06** | Defense in Depth | **Low** | `verify_ticket_pass` verified `ticket.status in ('revoked', 'cancelled')` and tenant scope, but did not assert `participant.status != 'cancelled'`. | Added explicit participant cancellation check (`if participant.status == "cancelled": raise TicketInvalidError(...)`) in `verify_ticket_pass`. |
| **SEC-5B-07** | Operational Visibility | **Low** | No diagnostic query existed to reconcile `current_confirmed_count` and `current_attended_count` against underlying database records during technical audits or disaster recovery. | Implemented `reconcile_event_registration_counts(db, event_id, auto_fix=False)` which computes exact counts from confirmed/attended rows, detects drift, and optionally auto-corrects counters. |

---

## 3. Public Registration Key & Credential Security Analysis

### 3.1 Ticket Credential Security
- **Entropy:** Pass credentials generated via `generate_ticket_credential()` format: `CO-PASS-<HEX>` using `secrets.token_hex(16).upper()`. This supplies **128 bits of cryptographic entropy**, completely precluding brute-force or enumeration attacks.
- **Raw Token Storage:** Raw pass tokens are **strictly non-persisted**. The `tickets` database table stores only `pass_code_hash` (`String(64)`, SHA-256). Raw tokens exist only in memory during initial generation and are returned to the caller via `IssuedTicketDTO`.
- **String Representation (`__repr__`):** Verified that `Ticket.__repr__` outputs only the human-readable serial reference (`ticket_reference="TKT-XXXX"`), never printing raw credentials or pass hashes in logs or error traces.
- **Verification:** `verify_ticket_pass` uses `hmac.compare_digest` to perform constant-time hash comparisons, eliminating timing attack vectors.
- **Zero PII in Credentials:** Ticket pass codes are purely pseudo-random hex strings containing zero attendee names, emails, phone numbers, or academic affiliations.

### 3.2 Public Registration Key Threat Model
- **Nature of the Key:** `public_registration_key` is an unguessable capability identifier (e.g. `reg_3f9a7c...`) embedded in public URLs. It is not an administrative secret, but rather an unguessable slug that prevents unannounced, private, or draft event registrations from being discovered through sequential UUID or integer enumeration.
- **Storage Protection:** Storing only `registration_key_hash` (SHA-256) in `event_registration_settings` ensures that even a database dump or read-only backup leak does not reveal unannounced capability URLs.
- **Privilege Boundary:** The registration key grants **zero staff, management, or viewing access**. It permits only reading public event metadata (event name, registration window, capacity availability) and submitting attendee registrations. It never exposes attendee lists, ticket hashes, or task workflows.

---

## 4. Relational & Cross-Tenant Integrity Findings

Every foreign key and constraint in the Slice 5 relational schema was audited through direct database tests bypassing domain services:

### 4.1 Cross-Tenant Isolation
- **Registrations:** Composite foreign key `fk_registrations_event_org` on `(event_id, organization_id)` references `events(id, organization_id)`. Attempting to insert a registration referencing an event in another organization triggers a database-level `IntegrityError`. Verified in `test_direct_db_cross_tenant_isolation_constraints`.
- **Participants:** Composite foreign key `fk_participants_event_org` on `(event_id, organization_id)` references `events(id, organization_id)`. Mismatched organization IDs fail at the database level.
- **Settings:** Composite foreign key `fk_event_reg_settings_event_org` on `(event_id, organization_id)` prevents cross-tenant settings associations.

### 4.2 Cross-Event Relational Integrity
- **Registration Participants:** `registration_participants` defines composite foreign keys:
  - `(registration_id, event_id, organization_id)` -> `registrations(id, event_id, organization_id)`
  - `(participant_id, event_id, organization_id)` -> `participants(id, event_id, organization_id)`
  Because `event_id` is common across both foreign keys, linking a participant from Event A to a registration in Event B is **strictly prohibited at the database engine level**. Verified in `test_direct_db_cross_event_registration_participant_isolation`.
- **Tickets:** Composite foreign keys `(participant_id, event_id, organization_id)` and `(registration_id, event_id, organization_id)` prevent issuing tickets across different events. Verified in `test_direct_db_cross_event_ticket_and_checkin_isolation`.
- **Check-Ins:** Composite foreign keys `(participant_id, event_id, organization_id)` and `(ticket_id, event_id, organization_id)` prevent checking in attendees to the wrong event.

---

## 5. Participant Identity & Duplicate Registration Policy (FA-007)

1. **Shared Email Policy:**
   - In campus and academic environments, multiple students, lab partners, or family members may legitimately register using a shared group or mentor email address.
   - The database enforces a **non-unique** index `ix_participants_event_email`.
   - Distinct participants sharing an email receive distinct `Participant` records, separate UUIDs, separate tickets (`CO-PASS-...`), and independent check-in states.
   - Verified in `test_shared_email_policy_distinct_identities_and_attendance`: checking in Alice marks only Alice as attended; Bob (sharing Alice's email) remains registered and unchecked until his pass is scanned.
2. **Team Member Duplicate Prevention:**
   - Within a team submission, submitting duplicate members (identical name and email) is caught and rejected with `DuplicateRegistrationError`. Verified in `test_team_duplicate_member_rejection`.
   - In the database, `UniqueConstraint("registration_id", "participant_id")` prevents duplicate participant-registration join rows.
3. **Idempotency Keys:**
   - Idempotency keys are scoped strictly to their `event_id`.
   - The additive migration `c8d9e0f1a2b3` introduced partial unique index `uq_registrations_event_idempotency` (`['event_id', 'idempotency_key'] WHERE idempotency_key IS NOT NULL`).
   - Verified that different events can safely reuse identical client idempotency keys, while identical keys in the same event fail at the database engine level.

---

## 6. Capacity Accounting & Concurrency Verification (D-SLICE5-01)

1. **Individual Participant Capacity Metric:**
   - Capacity is measured strictly in human bodies (`len(participants)`), never in registration groups. Solo registrations consume 1 slot; a team of $N$ consumes $N$ slots.
2. **Atomic Conditional SQL Reservation:**
   - Evaluated using conditional update:
     $$\text{UPDATE } \texttt{event\_registration\_settings} \text{ SET } \texttt{current\_confirmed\_count} = \texttt{current\_confirmed\_count} + :slots \text{ WHERE } \texttt{event\_id} = :id \text{ AND } (\texttt{capacity\_limit IS NULL} \text{ OR } \texttt{current\_confirmed\_count} + :slots \le \texttt{capacity\_limit})$$
   - Prevents race conditions and overselling without coarse table locks.
3. **All-or-Nothing Team Invariant:**
   - Verified in `test_atomic_capacity_accounting_and_all_or_nothing`: when 3 slots remain, a team of 3 is confirmed; when 2 slots remain, a team of 3 is rejected entirely with `CapacityExhaustedError` (or waitlisted if enabled). No partial team admission occurs.
4. **Transaction Rollback on Fault Injection:**
   - Verified in `test_capacity_reservation_rollback_on_fault_injection`: simulated database crashes or aborts midway through registration atomically roll back `current_confirmed_count` and all child entities.
5. **Exact Cancellation Accounting:**
   - Verified in `test_cancellation_capacity_release_exactness`:
     - Confirmed registrations release capacity exactly once upon cancellation.
     - Waitlisted registrations do **NOT** release confirmed capacity they never consumed.
     - Repeated cancellations are idempotent and cannot drive counters negative (guarded by `func.max(0, ...)` and check constraint `ck_event_reg_settings_confirmed_nonneg`).
6. **Diagnostic Reconciliation:**
   - Verified `reconcile_event_registration_counts`: detects synthetic counter drift and auto-synchronizes counters back to verified active records.

---

## 7. Check-In, Duplicate Scans & Audit Corrections (D-SLICE5-04)

1. **Duplicate Scan Idempotency:**
   - Scanning an already checked-in ticket returns `(CheckIn, is_duplicate=True)`.
   - Does not increment `current_attended_count` or create duplicate check-in records.
   - Partial unique index `uq_check_in_event_participant` (`['event_id', 'participant_id'] WHERE check_in_status = 'valid'`) guarantees at most one valid check-in per attendee at the database engine level.
2. **Manager-Only Check-In Void Authority:**
   - Verified in `test_check_in_void_manager_authority_and_immutable_audit_trail`:
     - Regular desk volunteers holding `REGISTRATION_STAFF` (`ACTION_CHECK_IN`) cannot void check-ins (`PermissionDeniedError`).
     - Managers (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`) holding `ACTION_CORRECT_CHECK_IN` can void check-ins.
     - Voids require a mandatory explanation of at least 10 characters (enforced by `CheckInCorrectionError` and check constraint `ck_corrections_reason_min_length`).
     - Check-in records are **never hard-deleted**; status transitions to `'voided'` with `voided_at` and `voided_by_user_id` populated, and an append-only audit record is inserted into `check_in_corrections`.
     - Attempting to void an already voided check-in fails with `CheckInCorrectionError`.

---

## 8. Database-Enforced vs Service-Enforced Invariants

| Invariant | Database Engine Enforced | Domain Service Enforced | Mechanism |
| :--- | :---: | :---: | :--- |
| **Multi-Tenant Org Scope** | Yes | Yes | Composite foreign keys `(event_id, organization_id)` referencing `events(id, organization_id)` |
| **Cross-Event Registration Mismatch** | Yes | Yes | Composite foreign keys `(registration_id, event_id, organization_id)` and `(participant_id, event_id, organization_id)` |
| **Single Active Ticket per Participant** | Yes | Yes | Partial unique index `uq_ticket_participant_active` on `tickets(participant_id) WHERE status = 'issued'` |
| **Single Valid Check-In per Participant** | Yes | Yes | Partial unique index `uq_check_in_event_participant` on `check_ins(event_id, participant_id) WHERE check_in_status = 'valid'` |
| **Registration Idempotency Key Uniqueness** | Yes | Yes | Partial unique index `uq_registrations_event_idempotency` on `registrations(event_id, idempotency_key) WHERE idempotency_key IS NOT NULL` |
| **Public Registration Key Uniqueness** | Yes | Yes | Partial unique index `uq_event_reg_settings_key_hash` on `event_registration_settings(registration_key_hash) WHERE registration_key_hash IS NOT NULL` |
| **Void Integrity Check** | Yes | Yes | Check constraint `ck_check_ins_void_integrity`: voided requires `voided_at` & `voided_by_user_id`; valid requires both NULL |
| **Correction Reason Min Length** | Yes | Yes | Check constraint `ck_corrections_reason_min_length`: `length(trim(reason)) >= 10` |
| **Non-Negative Counts** | Yes | Yes | Check constraints `ck_event_reg_settings_confirmed_nonneg` and `ck_event_reg_settings_attended_nonneg` |
| **Atomic Capacity Reservation** | Yes | Yes | Conditional SQL update: `WHERE current_confirmed_count + :slots <= capacity_limit` |
| **Parent Program Archival Check** | No | Yes | Domain service check against `event.program.archived_at` |
| **Ticket Replacement Revocation** | No | Yes | Domain service `issue_replacement_ticket` revoking prior tickets |
| **Privacy Contact Masking** | No | Yes | Domain service `get_event_roster_participants` masking email/phone based on `ACTION_VIEW_ATTENDEE_CONTACT` |

---

## 9. Verification Commands & Actual Results

Every test and verification check below was directly executed against the current repository:

```text
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-9.2.0, pluggy-1.7.0
rootdir: D:\Antigravity_Projects\CampusOps\backend
configfile: pytest.ini
plugins: anyio-4.15.1
collected 251 items

backend\tests\test_api_auth_boundary.py .........                        [  3%]
backend\tests\test_api_blockers_notifications.py .....                   [  5%]
backend\tests\test_api_departments.py .......                            [  8%]
backend\tests\test_api_event_leads.py ......                             [ 10%]
backend\tests\test_api_events.py ..........                              [ 14%]
backend\tests\test_api_invitations.py .........                          [ 18%]
backend\tests\test_api_me.py ....                                        [ 19%]
backend\tests\test_api_organizations.py .........                        [ 23%]
backend\tests\test_api_programs.py ........                              [ 26%]
backend\tests\test_api_scoped_invitations.py .....                       [ 28%]
backend\tests\test_api_tasks.py .................                        [ 35%]
backend\tests\test_domain_models.py ......                               [ 37%]
backend\tests\test_health.py .                                           [ 38%]
backend\tests\test_invitation.py .............                           [ 43%]
backend\tests\test_migrations.py ....                                    [ 45%]
backend\tests\test_organization.py ........                              [ 48%]
backend\tests\test_permissions.py ........                               [ 51%]
backend\tests\test_slice_3a_domain.py .............                      [ 56%]
backend\tests\test_slice_3a_integrity_audit.py ..........                [ 60%]
backend\tests\test_slice_3b_event_dates_db.py .......                    [ 63%]
backend\tests\test_slice_3b_security_audit.py ...........                [ 67%]
backend\tests\test_slice_4a_security_audit.py ..............             [ 73%]
backend\tests\test_slice_4a_task_domain.py ..............                [ 78%]
backend\tests\test_slice_4b_security_audit.py ..............             [ 84%]
backend\tests\test_slice_5b_registration_domain.py ...................   [ 92%]
backend\tests\test_slice_5b_security_audit.py ....................       [100%]

======================= 251 passed, 1 warning in 8.14s ========================
```

- **`python -m pip check`:** `No broken requirements found.`
- **Frontend Vitest (`npm test`):** `2 passed (2) in 1.05s`
- **Frontend Build (`npm run build`):** Built cleanly in 107ms (`dist/assets/index-CNf_Nd2m.js 219.92 kB`)
- **Git Diff Hygiene (`git diff --check`):** Exit code 0, clean.

---

## 10. Repository File Accounting

### Modified Files:
- [`backend/app/models/registration.py`](file:///D:/Antigravity_Projects/CampusOps/backend/app/models/registration.py): Added partial unique indexes `uq_registrations_event_idempotency` and `uq_event_reg_settings_key_hash`.
- [`backend/app/services/registration.py`](file:///D:/Antigravity_Projects/CampusOps/backend/app/services/registration.py): Added key generation/rotation, parent program archival checks, cancelled participant pass check, multi-ticket manual search safety, thorough ticket revocation, and diagnostic reconciliation.
- [`backend/tests/test_migrations.py`](file:///D:/Antigravity_Projects/CampusOps/backend/tests/test_migrations.py): Added `test_slice_5b_integrity_hardening_migration_lifecycle`.
- [`docs/implementation/IMPLEMENTATION_STATUS.md`](file:///D:/Antigravity_Projects/CampusOps/docs/implementation/IMPLEMENTATION_STATUS.md): Governance and technical gate tracking.

### Added Files:
- [`backend/alembic/versions/c8d9e0f1a2b3_slice_5b_integrity_hardening.py`](file:///D:/Antigravity_Projects/CampusOps/backend/alembic/versions/c8d9e0f1a2b3_slice_5b_integrity_hardening.py): Additive migration introducing partial unique indexes for idempotency and registration keys.
- [`backend/tests/test_slice_5b_security_audit.py`](file:///D:/Antigravity_Projects/CampusOps/backend/tests/test_slice_5b_security_audit.py): 20 comprehensive security, relational integrity, capacity, and check-in audit regression tests.
- [`docs/implementation/SLICE_5B_SECURITY_AUDIT_REPORT.md`](file:///D:/Antigravity_Projects/CampusOps/docs/implementation/SLICE_5B_SECURITY_AUDIT_REPORT.md): This authoritative engineering audit report.

### Deleted Files:
- None.

---

## 11. Final Git State Confirmation

Per strict instructions:
- **Zero changes staged** (`git add` was not executed).
- **Zero commits made** (`git commit` was not executed).
- All changes exist cleanly as uncommitted modifications in the working tree:

```text
 M backend/app/api/v1/endpoints/blockers.py
 M backend/app/models/__init__.py
 M backend/app/models/registration.py
 M backend/app/models/task.py
 M backend/app/services/errors.py
 M backend/app/services/permissions.py
 M backend/app/services/registration.py
 M backend/app/services/task.py
 M backend/tests/test_migrations.py
 M docs/implementation/IMPLEMENTATION_STATUS.md
?? "Consolidated Documentation/CampusOps_Decision_Log_v1.7_Addendum.md"
?? backend/alembic/versions/b7c8d9e0f1a2_slice_5_registration_ticketing_and_attendance.py
?? backend/alembic/versions/c8d9e0f1a2b3_slice_5b_integrity_hardening.py
?? backend/tests/test_slice_4b_security_audit.py
?? backend/tests/test_slice_5b_registration_domain.py
?? backend/tests/test_slice_5b_security_audit.py
?? docs/implementation/SLICE_4B_SECURITY_AUDIT_REPORT.md
?? docs/implementation/SLICE_5B_DOMAIN_IMPLEMENTATION_REPORT.md
?? docs/implementation/SLICE_5B_SECURITY_AUDIT_REPORT.md
?? docs/implementation/SLICE_5_ACCEPTANCE_TEST_PLAN.md
?? docs/implementation/SLICE_5_API_CONTRACT_DRAFT.md
?? docs/implementation/SLICE_5_SCHEMA_RELATIONSHIP_PLAN.md
?? docs/implementation/SLICE_5_SCOPE_AND_ARCHITECTURE_PLAN.md
```

---

## 12. Remaining Technical Gates & Next Steps

1. **TG-02 (Authentication Spike / Live Provider):** Remained blocked on container / hosted infrastructure; cryptographic validation complete.
2. **TG-03 (Database & Migrations):** **PASSED (Slice 5B Hardened Baseline)** through migration `c8d9e0f1a2b3`.
3. **TG-05 (Test Framework Baseline):** **PASSED** with 251 passing backend tests and 2 passing frontend tests.
4. **TG-06 (Evidence Storage):** Deferred to private storage adapter slice.
5. **TG-07 (Production Pilot):** **NO-GO** pending pilot checklist completion.
6. **Next Authorized Increment:** Proceed to **Slice 5C — Participant Registration, Ticketing & Attendance REST APIs**.

