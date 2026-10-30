# CampusOps — Slice 5 Acceptance Test Plan: Registration, Ticketing & Attendance

**Date:** 29 October 2026  
**Status:** Acceptance Test Plan (Slice 5A — Design Only)  
**Authoritative Baseline:** `Consolidated Documentation/CampusOps_PRD_v1.1.md` (CO-FR-008, CO-FR-009, CO-SEC-003, FA-005, FA-007, AT-004), `CampusOps_Technical_Specification_v1.1.md` Section 3.4, and `Consolidated Documentation/CampusOps_Role_and_Permission_Matrix_v0.1.md`.

---

## 1. Test Strategy & Acceptance Principles

Slice 5 acceptance testing ensures that native participant registration, non-payment admission pass issuance, and individual attendance check-ins behave deterministically and securely under both single-day and multi-event program workflows.

### 1.1 Core Verification Principles
1. **The Individual Attendance Rule (AT-004 / FA-005):** Every participant is checked in individually. Checking in a team lead or scanning a team pass must **never** check in other team members.
2. **Deterministic Concurrency Control:** Simultaneous registrations at the capacity limit must never exceed the configured maximum. Concurrent duplicate scans of the same pass must resolve idempotently without inflating attendance counts.
3. **Zero PII Exposure in Pass Credentials:** Passes and QR codes must contain only opaque, high-entropy tokens without participant contact information.
4. **Tenant & Sibling-Event Boundary Isolation:** Multi-event programs must strictly isolate rosters and check-in stations across sibling events. An Event Lead on Event 1 cannot check in attendees for Event 2.

---

## 2. Test Suite Structure & Traceability Matrix

| Test Suite Category | Module / Area | Test Count | Requirement Tracing |
| :--- | :--- | :---: | :--- |
| **Category 1: Public Registration Workflows** | `test_slice_5_public_registration.py` | 10 tests | CO-FR-008, FA-007, AT-001, AT-002 |
| **Category 2: Ticketing & Digital Admission Passes** | `test_slice_5_ticketing_and_passes.py` | 8 tests | CO-FR-008, CO-SEC-003, FA-005 |
| **Category 3: Individual Attendance Check-In** | `test_slice_5_check_in_operations.py` | 10 tests | CO-FR-009, FA-005, AT-004 |
| **Category 4: Check-In Voids & Audit Ledger** | `test_slice_5_check_in_corrections.py` | 6 tests | CO-FR-009, CO-SEC-004, FA-005 |
| **Category 5: Scope Boundaries & Sibling Isolation** | `test_slice_5_scope_isolation.py` | 6 tests | FA-002, AT-002, AT-005 |
| **Category 6: Privacy, Contact Masking & Exports** | `test_slice_5_privacy_and_exports.py` | 6 tests | CO-SEC-003, FA-003, AT-005 |
| **Category 7: Concurrency & Race Condition Protection**| `test_slice_5_concurrency_races.py` | 4 tests | CO-FR-008, CO-FR-009, AT-004 |
| **Category 8: Alembic Migration Lifecycle** | `test_migrations.py` | 2 tests | TG-03 |

---

## 3. Detailed Acceptance Test Specifications

### Category 1: Public Native Registration Workflows

#### `TC-REG-01: Public Solo Registration Happy Path`
- **Preconditions:** Event created with `registration_format = 'both'`, `capacity_limit = 50`, `is_open = True`.
- **Action:** POST to `/api/v1/public/events/{key}/registrations` with individual participant details (`full_name`, `email`).
- **Assertions:**
  - Response is `201 Created` with `confirmation_code` and `registration_status: "confirmed"`.
  - Exactly 1 `Registration` row created with `registration_type = 'individual'`.
  - Exactly 1 `Participant` row created with `status = 'registered'`.
  - Exactly 1 `Ticket` row created with `status = 'issued'` and valid `pass_code`.
  - `event_registration_settings.current_confirmed_count` increments from 0 to 1.

#### `TC-REG-02: Public Team Registration Happy Path`
- **Preconditions:** Event created with `registration_format = 'team_only'`, `team_size_min = 2`, `team_size_max = 4`, `capacity_limit = 100`.
- **Action:** POST to `/api/v1/public/events/{key}/registrations` with `registration_type = 'team'`, `team_name = 'DevTitans'`, and 3 distinct members (`is_primary_contact` designated).
- **Assertions:**
  - Response is `201 Created` containing 3 distinct admission passes.
  - Exactly 1 `Registration` row created with `team_name = 'DevTitans'`.
  - Exactly 3 `Participant` rows created.
  - Exactly 3 distinct `Ticket` rows created, each bound to a unique `participant_id`.
  - `event_registration_settings.current_confirmed_count` increments by 3.

#### `TC-REG-03: Team Sizing Validation (Min/Max Boundary Violations)`
- **Preconditions:** Event requires `team_size_min = 3`, `team_size_max = 5`.
- **Action A:** Submit team with 2 members.
  - **Assertion:** Returns `422 Unprocessable Entity` ("Team must have at least 3 members"). Zero DB rows created.
- **Action B:** Submit team with 6 members.
  - **Assertion:** Returns `422 Unprocessable Entity` ("Team cannot exceed 5 members"). Zero DB rows created.

#### `TC-REG-04: Duplicate Active Email Rejection in Same Event`
- **Preconditions:** Attendee "Aarav" registered with `email = "aarav@college.edu"`.
- **Action:** Second solo registration submitted for the same event with `email = "AARAV@college.edu"`.
- **Assertions:**
  - Returns `400 Bad Request` ("A registration with this email already exists for this event").
  - Partial unique index `uq_participants_event_email` remains intact.

#### `TC-REG-05: Registration Window Boundary (Early / Late Cutoff)`
- **Preconditions:** `registration_open_at` is tomorrow, or `registration_close_at` was yesterday.
- **Action:** POST to public registration endpoint.
- **Assertions:** Returns `400 Bad Request` ("Registration is currently closed for this event").

#### `TC-REG-06: Event Capacity Exhaustion Boundary`
- **Preconditions:** Event has `capacity_limit = 10`. Current confirmed count is 9.
- **Action A:** Submit team registration with 2 members (requires 2 slots, only 1 available).
  - **Assertion:** Returns `400 Bad Request` ("Event capacity has been reached"). No records created.
- **Action B:** Submit solo registration (requires 1 slot).
  - **Assertion:** Succeeds (`201 Created`). Confirmed count becomes 10/10.
- **Action C:** Next solo registration submitted.
  - **Assertion:** Returns `400 Bad Request` ("Event capacity has been reached").

#### `TC-REG-07: Staff-Assisted Walk-In Registration`
- **Preconditions:** Authorized registration staff (`ACTION_CHECK_IN`) at event desk.
- **Action:** POST `/api/v1/organizations/{org_id}/events/{event_id}/registrations/walk-in` with attendee details.
- **Assertions:**
  - Returns `201 Created`.
  - `Registration.registration_channel` is `'walk_in'`.
  - Participant and Ticket created. Capacity counter updated.

#### `TC-REG-08: Registration Cancellation Releases Capacity`
- **Preconditions:** Event with `capacity_limit = 20`. Confirmed count is 20 (full).
- **Action:** Authorized manager cancels Registration R (solo).
- **Assertions:**
  - Response is `200 OK`. `Registration.registration_status` becomes `'cancelled'`.
  - Associated `Ticket.status` transitions from `'issued'` to `'cancelled'`.
  - `event_registration_settings.current_confirmed_count` decrements from 20 to 19.
  - Next public registration succeeds.

---

### Category 2: Ticketing & Digital Admission Passes

#### `TC-TCK-01: Digital Pass Token High Entropy & PII Exclusion`
- **Preconditions:** Registration confirmed for attendee "John Doe", `email = "john@example.com"`, `phone = "+919876543210"`.
- **Action:** Inspect generated `Ticket` row and `GET /public/events/{key}/passes/{pass_code}` response.
- **Assertions:**
  - `pass_code` matches pattern `^CO-PASS-[0-9A-F]{32}$`.
  - `qr_payload` contains *only* the pass code string or opaque pass URL.
  - QR payload contains zero occurrences of "john@example.com" or "+919876543210".

#### `TC-TCK-02: Revoked Ticket Invalidation`
- **Preconditions:** Ticket T1 is issued. Attendee reports lost phone; manager reissues pass via `POST .../participants/{id}/reissue-pass`.
- **Assertions:**
  - Original Ticket T1 has `status = 'revoked'`, `revoked_at` populated.
  - New Ticket T2 created with `status = 'issued'` and a different `pass_code`.
  - Scanning T1 returns `400 Bad Request: Ticket has been revoked`.
  - Scanning T2 succeeds (`200 OK: Check-In Verified`).

---

### Category 3: Individual Attendance Check-In Operations

#### `TC-CHK-01: Station QR Scan Check-In Happy Path`
- **Preconditions:** Attendee holding valid Ticket T1 (`status = 'issued'`).
- **Action:** Staff calls `POST /organizations/{org_id}/events/{event_id}/check-ins {"pass_code": T1.pass_code, "station_id": "DESK-1"}`.
- **Assertions:**
  - Returns `200 OK` with `status: "verified"`, attendee name, and check-in timestamp.
  - `check_ins` row created with `check_in_status = 'valid'`, `method = 'qr_scan'`.
  - `Ticket.status` transitions to `'used'`.
  - `event_registration_settings.current_attended_count` increments from 0 to 1.

#### `TC-CHK-02: Team Member Individual Check-In Rule (Strict Isolation)`
- **Preconditions:** Team "CyberSquad" registered with 3 members: Alice, Bob, Charlie. All hold issued passes.
- **Action:** Alice arrives and scans her pass at 09:00 AM.
- **Assertions:**
  - Alice's check-in succeeds (`200 OK`). Alice's ticket status is `'used'`.
  - Bob and Charlie remain unchecked (`status = 'registered'`, ticket status `'issued'`).
  - Total event attended count increments by **1**, NOT 3.
  - Checking in Bob later at 09:30 AM records Bob's distinct timestamp without affecting Alice or Charlie.

#### `TC-CHK-03: Duplicate / Replay Scan Idempotency`
- **Preconditions:** Attendee "Alice" was checked in at 09:00 AM at Station 1.
- **Action:** Alice's pass is scanned a second time at Station 2 at 09:05 AM.
- **Assertions:**
  - Returns `200 OK` with `status: "already_checked_in"`.
  - Response includes original check-in timestamp ("09:00 AM") and station ("Station 1").
  - Zero secondary `check_ins` rows created.
  - `current_attended_count` remains 1 (no double-counting).

#### `TC-CHK-04: Search-Based Manual Fallback Check-In`
- **Preconditions:** Attendee "Carlos Gomez" arrives with dead phone battery.
- **Action A:** Staff calls `GET /check-in-lookup?q=Gomez`.
  - **Assertion:** Returns matching participant record with masked email (`c***@college.edu`).
- **Action B:** Staff verifies photo ID and calls `POST /check-ins {"participant_id": carlos.id, "method": "manual_search"}`.
  - **Assertion:** Returns `200 OK: Check-In Verified`. Check-in row records `method = 'manual_search'`.

---

### Category 4: Check-In Corrections & Audit Ledger

#### `TC-COR-01: Manager Voids Accidental Check-In With Mandatory Reason`
- **Preconditions:** Volunteer mistakenly checked in participant "David" instead of "Daniel".
- **Action:** Event Lead calls `POST /check-ins/{check_in_id}/void {"reason": "Volunteer clicked wrong attendee in search"}`.
- **Assertions:**
  - Response is `200 OK`. `check_ins.check_in_status` becomes `'voided'`.
  - `check_in_corrections` row created with `previous_status = 'valid'`, `new_status = 'voided'`, reason, actor, and timestamp.
  - Associated `Ticket.status` reverts from `'used'` back to `'issued'`.
  - `event_registration_settings.current_attended_count` decrements from 1 to 0.

#### `TC-COR-02: Desk Volunteer Denied Correction Authority`
- **Preconditions:** Ordinary volunteer holding only `REGISTRATION_STAFF` (`ACTION_CHECK_IN`).
- **Action:** Volunteer attempts `POST /check-ins/{check_in_id}/void`.
- **Assertions:** Returns `403 Forbidden` (`ACTION_CORRECT_CHECK_IN` required).

---

### Category 5: Scope Boundaries & Sibling-Event Isolation

#### `TC-SCP-01: Sibling Event Pass Scan Rejection`
- **Preconditions:** Multi-event program "TechFest" has Event 1 (Hackathon) and Event 2 (RoboWars). Attendee registers for Event 1 (Pass 1).
- **Action:** Check-in staff at Event 2 scans Pass 1.
- **Assertions:**
  - Returns `400 Bad Request` ("Pass is not valid for this event").
  - No check-in recorded for Event 2.

#### `TC-SCP-02: Cross-Tenant Pass Scan Rejection`
- **Preconditions:** Attendee has valid pass for Org 2. Staff in Org 1 scans the pass.
- **Assertions:** Returns uniform `404 Not Found: Ticket not found` (prevents cross-tenant discovery).

---

### Category 6: Privacy, Contact Masking & Exports

#### `TC-PRV-01: Desk Staff Contact Masking`
- **Preconditions:** Desk staff holding `ACTION_VIEW_ROSTER` calls `GET /participants`.
- **Assertions:** Email is serialized as `a***@college.edu`; phone number is serialized as `***-***-3210`.

#### `TC-PRV-02: Manager Unmasked Contact Access & CSV Export`
- **Preconditions:** Event Lead holding `ACTION_VIEW_ATTENDEE_CONTACT` and `ACTION_EXPORT_PARTICIPANTS`.
- **Action A:** `GET /participants/{id}` -> Returns raw email and phone number.
- **Action B:** `GET /roster-export` -> Streams CSV file containing unmasked roster. Audit event recorded.

---

### Category 7: Concurrency & Race Condition Protection

#### `TC-CON-01: Simultaneous Registration Race at Capacity Boundary`
- **Preconditions:** Event capacity limit is 10. Current confirmed count is 9 (1 slot remaining).
- **Action:** 5 concurrent threads submit solo registration requests simultaneously.
- **Assertions:**
  - Exactly **1 request succeeds** (`201 Created`).
  - Exactly **4 requests fail** with `400 Bad Request: Event capacity has been reached`.
  - Final confirmed count is exactly 10/10.

#### `TC-CON-02: Concurrent Duplicate QR Scans`
- **Preconditions:** Attendee arrives with Pass P1.
- **Action:** 2 scanner stations scan Pass P1 at the exact same millisecond.
- **Assertions:**
  - Exactly 1 station receives `status: "verified"` (`200 OK`).
  - The other station receives `status: "already_checked_in"` (`200 OK`).
  - Unique index `uq_check_in_event_participant` prevents duplicate row insertion.
  - Attended count increments by exactly 1.

---

### Category 8: Migration Roundtrip Lifecycle

#### `TC-MIG-01: Migration Upgrade / Downgrade Roundtrip`
- **Action:** Run Alembic migration `b7c8d9e0f1a2` (`head`), downgrade to `a6b7c8d9e0f1`, re-upgrade to `head`.
- **Assertions:**
  - Clean execution with zero SQLite constraint errors.
  - All 7 new tables, foreign keys, check constraints, and partial indexes are created, dropped, and recreated cleanly.

