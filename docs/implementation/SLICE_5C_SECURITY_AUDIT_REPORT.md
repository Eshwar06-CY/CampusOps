# CampusOps — Slice 5C Public API Security, Privacy & Transaction Audit Report

**Date:** 29 October 2026  
**Auditor:** Independent Security & Architecture Review  
**Repository:** `D:\Antigravity_Projects\CampusOps`  
**Target Slice:** Slice 5C — Native Participant Registration, Ticketing, Roster & Attendance Check-In REST APIs  
**Target Baseline:** 283 passing backend tests, 2 passing frontend tests (reproduced cleanly)  
**Final Post-Audit Suite:** **305 passing backend tests**, **2 passing frontend tests**, frontend production build verified clean  

---

## 1. Executive Summary & Verification Baseline

An independent security, privacy, transaction integrity, and architectural audit was conducted on the completed Slice 5C Participant Registration, Admission Ticketing, Roster Management, and Attendance Check-In REST APIs. 

### 1.1 Baseline Reproduction
Prior to any modifications or additions, the existing repository baseline was independently executed and reproduced:
- **Backend Tests:** 283 passed in 11.03s (`pytest backend/tests`).
- **Frontend Tests:** 2 passed in 1.95s (`npm test` in `frontend/`).
- **Frontend Production Build:** Succeeded (`tsc -b && vite build` completed in 281ms).
- **Database Migrations:** Linear Alembic chain verified with single head `c8d9e0f1a2b3`.

### 1.2 Audit Outcome & Hardening Summary
The audit confirmed the foundational strength of the audited Slice 5B domain layer and verified the adherence of Slice 5C REST endpoints to CampusOps security boundaries. In addition, targeted hardening was implemented and verified with 22 dedicated security audit tests:
1. **URL Credential Exposure Hardening:** Introduced secure body-based POST endpoints (`/passes/verify`, `/registrations/lookup`, `/registrations/cancel`) to prevent bearer credentials (`pass_code`, `confirmation_code`) from leaking into browser history, reverse proxy logs, referer headers, and telemetry.
2. **CSV Formula Injection Protection (CWE-1236):** Implemented `sanitize_csv_cell` across all user-controllable columns in roster exports, prefixing formula trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`) with a single quote (`'`).
3. **Registration Transaction Privacy:** Enforced tiered contact masking (`mask_email`, `mask_phone`) on `GET .../registrations` headers for callers lacking elevated `ACTION_VIEW_ATTENDEE_CONTACT` authority.
4. **Registration Key Rotation Usability:** Enhanced key rotation to transiently return the freshly generated unguessable `public_registration_key` to authorized managers in the response payload.
5. **Full Test Suite:** 305 backend tests now passing with zero regressions and zero broken requirements under `pip check`.

---

## 2. Public Capabilities & URL Credential Exposure Analysis

### 2.1 Threat Model: URL Bearer Credential Leakage
Under standard web architectures, URL path segments and query parameters are routinely captured in:
- Browser address bars, bookmarks, and local navigation histories.
- Reverse proxy access logs (e.g., Nginx, Envoy, Cloudflare).
- HTTP `Referer` headers transmitted to third-party assets or external links.
- Centralized SIEM and observability ingestion pipelines.

Exposing bearer admission pass tokens (`CO-PASS-...`) or registration confirmation codes (`REG-...`) in URL paths creates an unintended leakage surface.

### 2.2 Hardening Implementation
To resolve this risk while preserving backward compatibility for existing QR links:
- **Pass Verification:** Added `POST /api/v1/public/events/{registration_key}/passes/verify` accepting `PublicPassVerifyRequest(pass_code: str)` in the JSON body.
- **Registration Lookup:** Added `POST /api/v1/public/events/{registration_key}/registrations/lookup` accepting `PublicRegistrationLookupRequest(confirmation_code: str)` in the JSON body.
- **Registration Cancellation:** Added `POST /api/v1/public/events/{registration_key}/registrations/cancel` accepting `PublicRegistrationCancelBodyRequest(confirmation_code: str, contact_email: str, cancellation_reason: str)` in the JSON body.
- **Legacy Path Routes:** Maintained `GET .../passes/{pass_code}`, `GET .../registrations/{confirmation_code}`, and `POST .../registrations/{confirmation_code}/cancel` as backward-compatible aliases.

### 2.3 Registration Key Boundary
- The `public_registration_key` (`reg_<32-hex>`) grants authority strictly to discover published event metadata, verify tickets, look up registrations via capability codes, and submit self-service registrations.
- It possesses zero administrative authority. Passing a `registration_key` in an `Authorization` header to `/organizations/...` endpoints returns `401 Unauthorized` or `403 Forbidden`.
- Brute-force queries on non-existent pass codes, confirmation codes, or registration keys return uniform `404 Not Found` responses with uniform timing and zero internal state leakage.

---

## 3. Registration Idempotency & Capability Replay

### 3.1 Idempotency Key Scoping
- Native registration submissions accept an optional `idempotency_key` (max 128 characters).
- Uniqueness is strictly scoped per event (`Registration.event_id == event_id AND Registration.idempotency_key == idempotency_key`). Different events may reuse identical idempotency keys without cross-event collision.

### 3.2 Credential Redaction on Replays
- In CampusOps, admission pass raw tokens (`CO-PASS-...`) are high-entropy ephemeral tokens generated only in memory at issuance; only SHA-256 digests (`pass_code_hash`) are persisted in the database.
- When a client replays an identical payload with the same `idempotency_key`:
  - The existing registration is retrieved.
  - The raw pass token is safely returned as `<REDACTED_AFTER_ISSUANCE>`.
  - Capacity counters are **not** decremented again.
  - Additional tickets or participants are **not** created.
- If a client replays an `idempotency_key` with divergent payload data (different email, modified name, altered team size), the application rejects the request with `HTTP 409 Conflict`.

---

## 4. Participant Privacy, Masking & Public Enumeration

### 4.1 Zero Public Enumeration
- Public discovery endpoints (`/api/v1/public/events/{key}`) return event details, registration format, and a boolean `capacity_available`. Attendee counts, registrant names, and sequential participant IDs are never exposed.
- Pass display (`/passes/verify`) discloses only the attendee's name and verification status. Attendee contact emails, phone numbers, college names, and student IDs are strictly excluded.

### 4.2 Tiered Roster Masking
Staff access is partitioned by explicit permissions:
- **Registration Desk Volunteers (`REGISTRATION_STAFF`):**
  - Possess `ACTION_VIEW_REGISTRATIONS` and `ACTION_CHECK_IN`.
  - Lack `ACTION_VIEW_ATTENDEE_CONTACT`.
  - All email addresses are masked (e.g., `aarav.sharma@domain.edu` -> `a***a@domain.edu`).
  - All phone numbers are masked (e.g., `+91 9876543210` -> `+91 ******3210`).
  - Contact masking is enforced across `/participants` list, `/participants/{id}` detail, and `/registrations` headers list.
- **Event Leads & Managers (`EVENT_LEAD`, `PRIMARY_ADMIN`, `OFFICE_BEARER`):**
  - Possess `ACTION_VIEW_ATTENDEE_CONTACT`.
  - Receive full unmasked emails and phone numbers for legitimate operational contact.

---

## 5. Staff Authorization & Object-Level Access Control

### 5.1 Multi-Tenant & Cross-Event Isolation
- All staff routes validate workspace membership under `_ensure_org_and_event`. Users without an active membership in `organization_id` receive `404 Not Found`.
- Cross-tenant requests targeting alien organizations return `404 Not Found`, preventing tenant enumeration.
- Cross-event isolation: Attempting to check in a participant belonging to Event A via Event B's `/check-ins` endpoint raises `ScopeIntegrityError`, mapped to `HTTP 400/404`.

### 5.2 Role Boundary Separation
- **Walk-in Registrations:** Permitted for staff holding `ACTION_CHECK_IN`, recording `channel="walk_in"`.
- **Roster CSV Export:** Restricted to `ACTION_EXPORT_PARTICIPANTS` (Event Leads, Admins). Desk volunteers attempting export receive `403 Forbidden`.
- **Check-In Corrections / Voids:** Restricted to `ACTION_CORRECT_CHECK_IN` (Event Leads, Admins). Desk volunteers attempting to void a check-in receive `403 Forbidden`.

---

## 6. Capacity Accounting, State Transitions & Concurrency

### 6.1 Atomic Reservation & Rollback
- Capacity slots are conditionally deducted using atomic SQL updates:
  ```sql
  UPDATE event_registration_settings 
  SET current_confirmed_count = current_confirmed_count + :slots 
  WHERE event_id = :event_id 
    AND (capacity_limit IS NULL OR current_confirmed_count + :slots <= capacity_limit);
  ```
- If remaining capacity is insufficient to accommodate an entire team, the conditional update affects 0 rows, and `CapacityExhaustedError` is raised.
- Handlers run within nested savepoints (`with db.begin_nested():`). A capacity rejection rolls back all temporary participant rows cleanly, creating zero phantom rows or partial tickets.

### 6.2 Cancellation Capacity Release
- When an individual registration is cancelled, exactly 1 slot is released.
- When a team registration of $N$ participants is cancelled, exactly $N$ slots are released.
- Check-in status guard: registrations cannot be cancelled by attendees once any participant has already checked in.

### 6.3 Capacity Limit Reductions
- If an event manager reduces `capacity_limit` below `current_confirmed_count`, confirmed attendees are **not** evicted.
- `current_confirmed_count` remains intact, while subsequent registration attempts are rejected with `400 Bad Request`.

---

## 7. Ticket, Check-In and Correction Lifecycle

### 7.1 Single Active Ticket Invariant
- A participant can hold at most one active admission pass (`status="issued"`).
- When a manager reissues a pass (`POST .../participants/{id}/reissue-pass`), all prior issued tickets are transitioned to `status="revoked"` with an audit timestamp and reason.
- Verification or scanning of a revoked pass fails with `400 Bad Request` or `404 Not Found`.

### 7.2 Idempotent Check-In
- When an attendee pass is scanned at the check-in desk:
  - First scan: ticket transitions to `status="used"`, participant transitions to `status="attended"`, a `CheckIn` record is created, `current_attended_count` increments, and response status is `"verified"`.
  - Duplicate scan: returns HTTP 200 with `status="already_checked_in"`, the original `check_in_id`, and a descriptive message. `current_attended_count` is **not** incremented, and no duplicate `CheckIn` rows are created.

### 7.3 Manager Void Auditing
- Only managers holding `ACTION_CORRECT_CHECK_IN` can void a check-in.
- Void requests require a mandatory explanation (`reason`) of at least 10 characters (`ck_corrections_reason_min_length`). Submissions with shorter reasons fail schema validation with `422 Unprocessable Entity`.
- Upon valid void:
  - `CheckIn.check_in_status` becomes `"voided"`.
  - `Participant.status` reverts to `"registered"`.
  - `Ticket.status` reverts to `"issued"`.
  - `current_attended_count` decrements by 1.
  - An append-only audit row is inserted into `check_in_corrections` with `check_in_id`, `previous_status="valid"`, `new_status="voided"`, `corrected_by_user_id`, and `reason`.

---

## 8. Registration Settings, Key Rotation & Archival Cascading

### 8.1 Public Key Rotation
- Managers can rotate the public registration key via `PUT .../registration-settings` with `rotate_registration_key=True`.
- A new unguessable slug (`reg_<32-hex>`) is generated, hashed, and transiently returned in the response payload.
- The previous key immediately returns `404 Not Found` for all public endpoints.
- Previously issued admission passes and tickets remain valid for check-in.

### 8.2 Archival Cascading
- When an event is archived (`status="archived"`, `archived_at` set):
  - All public endpoints (`/public/events/{key}`) immediately return `404 Not Found`.
  - Staff operational endpoints return `404 Not Found`.
- When a parent program is archived (`prog.status="archived"`, `prog.archived_at` set):
  - Transitive checks in `_ensure_org_and_event` and `get_public_event_by_registration_key` immediately cause all child event public and staff endpoints to return `404 Not Found`.

---

## 9. Rate Limiting, Abuse Prevention & CSV Export Hardening

### 9.1 CSV Formula Injection Protection (CWE-1236)
Spreadsheet software (Microsoft Excel, Google Sheets, LibreOffice Calc) treats cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` as dynamic formulas or DDE macro commands. An attacker registering with a name like `=cmd|' /C calc'!A0` could compromise an administrator's machine upon export.
- **Remediation:** Added `sanitize_csv_cell(...)` in `app/services/registration.py`.
- **Application:** Applied to all attendee-supplied fields (`full_name`, `email_normalized`, `phone_number`, `college_name`, `student_id`, `team_name`) in `export_event_roster_csv`.
- **Behavior:** Prepends a single quote (`'`) to any string whose first character is one of `('=', '+', '-', '@', '\t', '\r')`, forcing spreadsheet software to treat the cell strictly as literal text.

### 9.2 Rate Limiting Boundary Specification
- **Application Layer:** Handles atomic capacity reservation, high-entropy cryptographic token validation, and uniform `404` rejection without state disclosure.
- **Gateway Layer:** In accordance with production architecture standards, volumetric rate limiting and IP-based DDoS mitigation are designated to the API Gateway / Reverse Proxy (Nginx / Cloudflare):
  - Public discovery & lookup: `60 req / min per IP`.
  - Public registration submission: `10 req / min per IP`.
  - Staff check-in scanning: `120 req / min per authenticated token`.

---

## 10. Database Schema & Migration Integrity

- **Alembic Revisions:** Verified linear revision sequence ending at head `c8d9e0f1a2b3`:
  - `880d8e4eb890`: Slice 1 foundational schema
  - `c92f1b4a3d10`: Slice 2A organization schema
  - `d81e3a5f2c90`: Slice 2B role schema
  - `e4f5a6b7c8d9`: Slice 3A event/program schema
  - `f5a6b7c8d9e0`: Slice 3B temporal integrity
  - `a6b7c8d9e0f1`: Slice 4A task management & blockers
  - `b7c8d9e0f1a2`: Slice 5 registration, ticketing & attendance
  - `c8d9e0f1a2b3`: Slice 5B integrity hardening
- **Relational Invariants:**
  - `CheckInCorrection` enforced by `ck_corrections_reason_min_length` (`length(trim(reason)) >= 10`).
  - `Event` enforced by `ck_events_status_archived`.
  - `Program` enforced by `ck_programs_status_archived`.
  - Foreign keys with `ON DELETE CASCADE` or `RESTRICT` properly indexed.

---

## 11. Dedicated Security Audit Test Suite

All security invariants and remediations are proven by `backend/tests/test_slice_5c_security_audit.py` (22 tests, all passing):

| Test Identifier | Tested Invariant | Result |
|---|---|:---:|
| `test_public_pass_verification_via_post_body` | Digital pass display via POST body; zero PII in payload | **PASS** |
| `test_public_pass_verification_invalid_token_returns_uniform_404` | Tampered/corrupted pass token returns generic 404 | **PASS** |
| `test_public_registration_lookup_via_post_body` | Registration status lookup via POST body; no contact PII disclosed | **PASS** |
| `test_public_registration_cancellation_via_post_body` | Self-service cancellation via POST body; requires email; releases slots | **PASS** |
| `test_public_capability_legacy_get_endpoints_backward_compatible` | Legacy GET routes remain backward-compatible | **PASS** |
| `test_registration_key_has_no_administrative_privileges` | `registration_key` cannot authorize staff/admin endpoints | **PASS** |
| `test_export_event_roster_csv_sanitizes_formula_triggers` | CWE-1236 formula triggers (`=`, `@`, `+`, `-`, `\t`, `\r`) sanitized with `'` | **PASS** |
| `test_idempotent_registration_replay_redacts_credentials` | Replay returns existing reg; redacts pass token; no double capacity | **PASS** |
| `test_idempotent_registration_conflict_on_altered_payload` | Idempotency key replay with altered payload returns 409 Conflict | **PASS** |
| `test_desk_volunteer_roster_receives_masked_contacts` | Desk volunteers see masked email and phone across participants and registrations | **PASS** |
| `test_event_lead_roster_receives_unmasked_contacts` | Managers holding `ACTION_VIEW_ATTENDEE_CONTACT` see unmasked data | **PASS** |
| `test_desk_volunteer_denied_csv_export` | Desk volunteers lacking `ACTION_EXPORT_PARTICIPANTS` receive 403 Forbidden | **PASS** |
| `test_cross_event_check_in_isolation` | Sibling-event check-in attempt rejected with 400/404 | **PASS** |
| `test_cross_tenant_isolation` | Cross-tenant access attempts return uniform 404 | **PASS** |
| `test_desk_volunteer_cannot_void_check_in` | Desk volunteer check-in void rejected with 403 Forbidden | **PASS** |
| `test_manager_void_check_in_validation_and_audit` | Manager void enforces >= 10 chars, decrements attended, creates audit record | **PASS** |
| `test_duplicate_check_in_rejection_and_idempotency` | Duplicate check-in returns `already_checked_in` without double counting | **PASS** |
| `test_team_registration_all_or_nothing_capacity_and_rollback` | Team overflow rejected with 400; rolls back completely without phantom rows | **PASS** |
| `test_manager_lowering_capacity_limit_does_not_evict_attendees` | Reducing capacity below confirmed count does not evict existing attendees | **PASS** |
| `test_registration_key_rotation_immediately_invalidates_old_key` | Rotating key invalidates old key immediately; passes remain valid | **PASS** |
| `test_archiving_event_or_parent_program_returns_404` | Archiving event or parent program immediately blocks public and staff access | **PASS** |
| `test_ticket_reissue_revokes_old_pass_and_maintains_single_active_ticket` | Pass reissue revokes old ticket; old token fails; new token checks in | **PASS** |

---

## 12. Verification Commands & Regression Checklist

All checks executed and verified in the live project environment:
```powershell
# 1. Full Backend Test Suite (305 passed in ~13s)
backend\.venv\Scripts\python.exe -m pytest

# 2. Dependency Check (Clean)
backend\.venv\Scripts\python.exe -m pip check

# 3. Frontend Test Suite (2 passed in ~1.9s)
Set-Location frontend; npm test

# 4. Frontend Production Build (Zero errors)
Set-Location frontend; npm run build
```

---

## 13. Audit Conclusion & Sign-Off

The Slice 5C Participant Registration, Admission Ticketing, Roster Management, and Attendance Check-In REST APIs are **approved and hardened**. All bearer capabilities have secure body-based transmission options, PII is protected under strict deny-by-default role boundaries, CSV exports are guarded against formula injection, and transactions guarantee complete atomicity.

The backend domain and REST layers for Slice 5 are complete, robust, and verified. The codebase is fully ready for frontend UI implementation.

