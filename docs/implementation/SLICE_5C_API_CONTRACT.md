# CampusOps — Slice 5C REST API Contract

**Date:** 29 October 2026  
**Status:** Implemented & Verified API Contract for Slice 5C  
**Authoritative Baseline:** `Consolidated Documentation/CampusOps_API_Contract_Draft_v0.2.md`, `CampusOps_PRD_v1.1.md` (CO-FR-008, CO-FR-009, FA-005, FA-007), `CampusOps_Technical_Specification_v1.1.md` Section 3.4, and `Consolidated Documentation/CampusOps_Role_and_Permission_Matrix_v0.1.md`.

---

## 1. Global Conventions & Trust Boundaries

### 1.1 Dual API Namespaces
Slice 5C routes are strictly partitioned into two distinct namespaces matching their trust boundaries:
1. **Public Participant Namespace (`/api/v1/public/...`):**
   - Unauthenticated, self-service endpoints accessible by prospective attendees.
   - Addressed by an unguessable high-entropy `registration_key` slug (`reg_<32-hex>`) to prevent sequential event enumeration.
   - Enforces PII protection (zero participant email/phone in QR payloads or unauthenticated status looks).
   - Enforces idempotent registration submissions and safe pass credential redaction on replays.
   - Safe errors: non-existent keys return uniform `404 Not Found`.
2. **Staff Operational Namespace (`/api/v1/organizations/{organization_id}/events/{event_id}/...`):**
   - Authenticated, role-gated endpoints for workspace administrators, event leads, and check-in volunteers.
   - Strictly enforces CampusOps deny-by-default RBAC and multi-tenant isolation.
   - Cross-tenant requests return uniform `HTTP 404 Not Found` to prevent entity enumeration.
   - Ordinary registration desk volunteers (`REGISTRATION_STAFF`) inspect only masked contact information (`mask_email`, `mask_phone`). Unmasked contact disclosure requires elevated `ACTION_VIEW_ATTENDEE_CONTACT`.
   - Check-in voids require `ACTION_CORRECT_CHECK_IN` (manager-only: Primary Admin, Office Bearer, Event Lead).

### 1.2 Pydantic Validation & Security Conventions
- All mutation request models enforce `model_config = ConfigDict(extra="forbid")` to block parameter pollution and client ID injection.
- Response models enforce `model_config = ConfigDict(from_attributes=True)`.
- Idempotency: Duplicate check-in attempts return a successful HTTP 200 response with `status: "already_checked_in"` without inflating counts or altering timestamps.
- Idempotency conflict: Reusing an idempotency key with diverging payload data returns `HTTP 409 Conflict`.

---

## 2. Public Participant Endpoints

### 2.1 `GET /api/v1/public/events/{registration_key}`
- **Description:** Retrieves public event details, registration status, format, team sizing bounds, and capacity availability.
- **Authentication:** None (Public).
- **Responses:**
  - `200 OK`:
    ```json
    {
      "public_registration_key": "reg_3a1b2c...",
      "event_id": "24cf97e8-da5b-48df-8709-56c327456690",
      "event_name": "Hackathon 2026",
      "description": "Collaborative coding challenge.",
      "event_date": "2026-11-02",
      "event_end_date": "2026-11-03",
      "venue": "Campus Main Auditorium",
      "timezone": "Asia/Kolkata",
      "registration_status": "open",
      "registration_format": "both",
      "team_size_min": 2,
      "team_size_max": 4,
      "capacity_available": true
    }
    ```
  - `404 Not Found`: Registration key invalid, event unconfigured, or event/parent program archived.

---

### 2.2 `POST /api/v1/public/events/{registration_key}/registrations`
- **Description:** Submits a native self-service registration (individual or team). Issues unguessable digital admission passes.
- **Authentication:** None (Public).
- **Request Body (`PublicRegistrationRequest` with `extra="forbid"`):**
  ```json
  {
    "registration_type": "team",
    "team_name": "ByteCrafters",
    "contact_email": "lead@student.edu",
    "contact_phone": "+91 9876543210",
    "idempotency_key": "idemp_12345",
    "participants": [
      {
        "full_name": "Team Lead Aarav",
        "email": "lead@student.edu",
        "phone_number": "+91 9876543210",
        "college_name": "Apex University",
        "student_id": "APEX-2026-001",
        "is_primary_contact": true,
        "team_role": "leader"
      },
      {
        "full_name": "Member Diya",
        "email": "diya@student.edu",
        "phone_number": "+91 9876543211",
        "college_name": "Apex University",
        "student_id": "APEX-2026-002",
        "is_primary_contact": false,
        "team_role": "member"
      }
    ]
  }
  ```
- **Responses:**
  - `201 Created`:
    ```json
    {
      "registration_id": "7fa85f64-5717-4562-b3fc-2c963f66afa6",
      "confirmation_code": "REG-8B1A2C3D",
      "registration_status": "confirmed",
      "registration_type": "team",
      "team_name": "ByteCrafters",
      "is_waitlisted": false,
      "passes": [
        {
          "participant_id": "8fa85f64-5717-4562-b3fc-2c963f66afa7",
          "participant_name": "Team Lead Aarav",
          "ticket_reference": "TKT-A1B2C3D4",
          "pass_code": "CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P",
          "pass_url": "/api/v1/public/events/{registration_key}/passes/CO-PASS-..."
        }
      ]
    }
    ```
  - `400 Bad Request`: Registration closed, temporal window closed, capacity exhausted, or duplicate intra-team member.
  - `409 Conflict`: Idempotency key reused with different registration payload.
  - `422 Unprocessable Entity`: Team size bounds violation, missing team name, or schema error.
  - `404 Not Found`: Event not found or registration key invalid.

---

### 2.3 `POST /api/v1/public/events/{registration_key}/passes/verify` *(Secure Standard)*
- **Description:** Verifies and displays attendee digital admission pass details. Transmits bearer credential in the request body to prevent token exposure in browser history, HTTP referer headers, reverse proxy logs, and telemetry.
- **Authentication:** None (Protected by 128-bit unguessable pass token in JSON payload).
- **Request Body (`PublicPassVerifyRequest` with `extra="forbid"`):**
  ```json
  {
    "pass_code": "CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P"
  }
  ```
- **Responses:**
  - `200 OK`:
    ```json
    {
      "ticket_reference": "TKT-A1B2C3D4",
      "pass_code": "CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P",
      "event_name": "Hackathon 2026",
      "participant_name": "Team Lead Aarav",
      "status": "issued",
      "issued_at": "2026-10-29T10:00:00Z",
      "used_at": null,
      "qr_payload": "CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P",
      "instructions": "Present this digital pass at the registration desk for individual check-in."
    }
    ```
  - `404 Not Found`: Invalid pass code, revoked pass, or event mismatch (uniform timing, zero PII disclosed).

---

### 2.4 `GET /api/v1/public/events/{registration_key}/passes/{pass_code}` *(Legacy Compatible)*
- **Description:** Maintained for backwards compatibility with existing clients and static links. Equivalent response to `POST .../passes/verify`.

---

### 2.5 `POST /api/v1/public/events/{registration_key}/registrations/lookup` *(Secure Standard)*
- **Description:** Capability-based registration status lookup without exposing confirmation codes in URL paths or proxy logs. Protects contact PII.
- **Authentication:** None (Protected by unguessable confirmation code in request body).
- **Request Body (`PublicRegistrationLookupRequest` with `extra="forbid"`):**
  ```json
  {
    "confirmation_code": "REG-8B1A2C3D"
  }
  ```
- **Responses:**
  - `200 OK`:
    ```json
    {
      "confirmation_code": "REG-8B1A2C3D",
      "registration_status": "confirmed",
      "registration_type": "team",
      "team_name": "ByteCrafters",
      "participant_count": 2,
      "created_at": "2026-10-29T10:00:00Z",
      "participants": [
        {
          "full_name": "Team Lead Aarav",
          "team_role": "leader",
          "is_primary_contact": true,
          "status": "registered"
        }
      ]
    }
    ```
  - `404 Not Found`: Registration code not found.

---

### 2.6 `GET /api/v1/public/events/{registration_key}/registrations/{confirmation_code}` *(Legacy Compatible)*
- **Description:** Legacy path parameter status lookup. Maintained for backwards compatibility.

---

### 2.7 `POST /api/v1/public/events/{registration_key}/registrations/cancel` *(Secure Standard)*
- **Description:** Self-service registration cancellation using request body parameters. Protects confirmation code from URL parameter leakage.
- **Authentication:** None (Requires confirmation code + matching contact email in JSON body).
- **Request Body (`PublicRegistrationCancelBodyRequest` with `extra="forbid"`):**
  ```json
  {
    "confirmation_code": "REG-8B1A2C3D",
    "contact_email": "lead@student.edu",
    "cancellation_reason": "Family emergency, unable to attend"
  }
  ```
- **Responses:**
  - `200 OK`:
    ```json
    {
      "confirmation_code": "REG-8B1A2C3D",
      "registration_status": "cancelled",
      "cancelled_at": "2026-10-29T10:30:00Z",
      "message": "Registration successfully cancelled and admission passes invalidated."
    }
    ```
  - `400 Bad Request`: Cannot cancel after attendees have already checked in.
  - `404 Not Found`: Registration code not found or contact email mismatch.

---

### 2.8 `POST /api/v1/public/events/{registration_key}/registrations/{confirmation_code}/cancel` *(Legacy Compatible)*
- **Description:** Legacy path-parameter cancellation route. Maintained for backwards compatibility.

---

## 3. Staff Registration & Settings Management Endpoints

### 3.1 `GET /api/v1/organizations/{organization_id}/events/{event_id}/registration-settings`
- **Description:** Retrieves event registration settings and counters.
- **Permission Required:** `ACTION_VIEW_REGISTRATIONS` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`, `REGISTRATION_STAFF`).
- **Responses:** `200 OK`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`.

---

### 3.2 `PUT /api/v1/organizations/{organization_id}/events/{event_id}/registration-settings`
- **Description:** Updates registration settings, limits, scheduling windows, access code, or rotates registration key.
- **Permission Required:** `ACTION_MANAGE_REGISTRATION_SETTINGS` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`).
- **Request Body (`EventRegistrationSettingsUpdateRequest`):**
  ```json
  {
    "is_open": true,
    "registration_format": "both",
    "capacity_limit": 100,
    "team_size_min": 2,
    "team_size_max": 4,
    "rotate_registration_key": false
  }
  ```
- **Responses:** `200 OK`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`.

---

### 3.3 `GET /api/v1/organizations/{organization_id}/events/{event_id}/registrations`
- **Description:** Lists registration transactions with pagination and status filters.
- **Permission Required:** `ACTION_VIEW_REGISTRATIONS`.
- **Query Parameters:** `status: Optional[str]`, `registration_type: Optional[str]`, `limit: int = 50`, `offset: int = 0`.
- **Responses:** `200 OK` (list of `StaffRegistrationSummaryResponse`), `401 Unauthorized`, `403 Forbidden`, `404 Not Found`.

---

### 3.4 `POST /api/v1/organizations/{organization_id}/events/{event_id}/registrations/walk-in`
- **Description:** Creates an authorized staff-assisted walk-in registration at the event desk.
- **Permission Required:** `ACTION_CHECK_IN` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`, `REGISTRATION_STAFF`).
- **Request Body:** Same schema as `PublicRegistrationRequest`, channel tagged as `"walk_in"`.
- **Responses:** `201 Created` (returns registration and issued passes), `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`.

---

### 3.5 `POST /api/v1/organizations/{organization_id}/events/{event_id}/registrations/{registration_id}/cancel`
- **Description:** Staff cancellation of a registration transaction. Releases confirmed capacity and revokes passes.
- **Permission Required:** `ACTION_MANAGE_REGISTRATION_SETTINGS`.
- **Request Body:** `{"cancellation_reason": "Team withdrew due to exam schedule."}`
- **Responses:** `200 OK`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`.

---

## 4. Staff Participant Roster & Pass Management Endpoints

### 4.1 `GET /api/v1/organizations/{organization_id}/events/{event_id}/participants`
- **Description:** Lists attendee roster records with tiered privacy masking. Contact details are masked unless caller holds `ACTION_VIEW_ATTENDEE_CONTACT`.
- **Permission Required:** `ACTION_VIEW_REGISTRATIONS`.
- **Query Parameters:** `search: Optional[str]`, `status: Optional[str]`, `limit: int = 50`, `offset: int = 0`.
- **Responses:** `200 OK` (list of `StaffParticipantRosterItemResponse`), `401 Unauthorized`, `403 Forbidden`, `404 Not Found`.

---

### 4.2 `GET /api/v1/organizations/{organization_id}/events/{event_id}/participants/{participant_id}`
- **Description:** Retrieves complete participant detail, full ticket history, and check-in status.
- **Permission Required:** `ACTION_VIEW_REGISTRATIONS`. Unmasked contact details require `ACTION_VIEW_ATTENDEE_CONTACT`.
- **Responses:** `200 OK`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`.

---

### 4.3 `PATCH /api/v1/organizations/{organization_id}/events/{event_id}/participants/{participant_id}`
- **Description:** Corrects attendee details (`full_name`, `college_name`, `student_id`, `phone_number`).
- **Permission Required:** `ACTION_MANAGE_REGISTRATION_SETTINGS`.
- **Responses:** `200 OK`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`.

---

### 4.4 `POST /api/v1/organizations/{organization_id}/events/{event_id}/participants/{participant_id}/reissue-pass`
- **Description:** Revokes all existing active/used passes and generates a fresh unguessable pass token.
- **Permission Required:** `ACTION_MANAGE_REGISTRATION_SETTINGS`.
- **Request Body:** `{"reason": "Attendee phone died, requested replacement ticket at desk."}`
- **Responses:** `200 OK` (returns `IssuedPassResponse` with new raw pass token), `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`.

---

## 5. Staff Attendance Check-In & Audited Void Endpoints

### 5.1 `POST /api/v1/organizations/{organization_id}/events/{event_id}/check-ins`
- **Description:** Records verified attendance arrival via QR scan or manual search. Enforces strictly one valid check-in per attendee.
- **Permission Required:** `ACTION_CHECK_IN`.
- **Request Body (`CheckInRequest`):**
  ```json
  {
    "pass_code": "CO-PASS-8B1A2C3D4E5F6G7H8I9J0K1L2M3N4O5P",
    "participant_id": null,
    "method": "qr_scan",
    "station_id": "DESK-1"
  }
  ```
- **Responses:**
  - `200 OK (Verified)`:
    ```json
    {
      "check_in_id": "1fa85f64-5717-4562-b3fc-2c963f66afa1",
      "status": "verified",
      "participant_id": "8fa85f64-5717-4562-b3fc-2c963f66afa7",
      "participant_name": "Team Lead Aarav",
      "team_name": "ByteCrafters",
      "checked_in_at": "2026-10-29T10:15:00Z",
      "station_id": "DESK-1",
      "message": "Check-in verified successfully."
    }
    ```
  - `200 OK (Duplicate Scan)`:
    ```json
    {
      "check_in_id": "1fa85f64-5717-4562-b3fc-2c963f66afa1",
      "status": "already_checked_in",
      "participant_id": "8fa85f64-5717-4562-b3fc-2c963f66afa7",
      "participant_name": "Team Lead Aarav",
      "team_name": "ByteCrafters",
      "checked_in_at": "2026-10-29T10:15:00Z",
      "station_id": "DESK-1",
      "message": "Attendee was already checked in at 10:15:00."
    }
    ```
  - `400 Bad Request`: Pass revoked, cancelled, or attendee ineligible.
  - `401 Unauthorized`, `403 Forbidden`, `404 Not Found`.

---

### 5.2 `GET /api/v1/organizations/{organization_id}/events/{event_id}/check-in-lookup`
- **Description:** Search attendee roster for desk check-in verification via ticket token, reference, name, or student ID.
- **Permission Required:** `ACTION_CHECK_IN`.
- **Query Parameters:** `q: str` (min_length=1).
- **Responses:** `200 OK` (list of `CheckInLookupItemResponse` with masked email and check-in eligibility).

---

### 5.3 `POST /api/v1/organizations/{organization_id}/events/{event_id}/check-ins/{check_in_id}/void`
- **Description:** Voids an accidental check-in record. Reverts ticket to `"issued"` and participant to `"registered"`, decrements attended count, and appends an immutable audit record.
- **Permission Required:** `ACTION_CORRECT_CHECK_IN` (manager-only: `PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`). Desk volunteers denied (HTTP 403).
- **Request Body (`CheckInVoidRequest`):**
  ```json
  {
    "reason": "Accidental check-in of wrong attendee; confirmed not present."
  }
  ```
- **Responses:** `200 OK` (returns `CheckInVoidResponse`), `400 Bad Request` (reason < 10 chars), `403 Forbidden`, `404 Not Found`.

---

## 6. Staff Attendance Reporting & CSV Export Endpoints

### 6.1 `GET /api/v1/organizations/{organization_id}/events/{event_id}/attendance-summary`
- **Description:** Operational attendance metrics, attendance percentage, and team attendance breakdown.
- **Permission Required:** `ACTION_VIEW_REGISTRATIONS`.
- **Responses:**
  - `200 OK`:
    ```json
    {
      "event_id": "24cf97e8-da5b-48df-8709-56c327456690",
      "capacity_limit": 50,
      "current_confirmed_count": 3,
      "current_attended_count": 2,
      "attendance_percentage": 66.67,
      "total_individual_registrations": 1,
      "total_team_registrations": 1,
      "total_participants_registered": 3,
      "teams_fully_attended": 0,
      "teams_partially_attended": 1,
      "teams_absent": 0
    }
    ```

---

### 6.2 `GET /api/v1/organizations/{organization_id}/events/{event_id}/roster-export`
- **Description:** Streams normalized participant and attendance roster as a downloadable CSV.
- **Permission Required:** `ACTION_EXPORT_PARTICIPANTS` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`).
- **Responses:**
  - `200 OK`: `text/csv` with `Content-Disposition: attachment; filename="roster_{event_id}.csv"`.
  - `401 Unauthorized`, `403 Forbidden`.
- **Security Hardening (CWE-1236 Formula Injection Protection):**
  - All user-supplied text cells (`full_name`, `email`, `phone_number`, `college_name`, `student_id`, `team_name`) are processed through `sanitize_csv_cell(...)`.
  - Any field beginning with formula execution trigger characters (`=`, `+`, `-`, `@`, `\t`, `\r`) is automatically prepended with a single quote (`'`), neutralizing spreadsheet formula execution.

---

## 7. Rate Limiting & Abuse Prevention Operational Boundary

### 7.1 Architecture & Separation of Concerns
1. **Public Route Brute-Force & Enumeration Protection:**
   - Public capability endpoints (`/api/v1/public/events/...`) use high-entropy cryptographically unguessable tokens (128-bit hex slugs and random UUIDs) with uniform `404 Not Found` responses upon error or invalid input, leaking zero attendee PII or internal system state.
   - Idempotency guarantees prevent replay attacks from artificially depleting event capacity or issuing duplicate passes.
2. **Operational Gateway vs Application Layer Rate Limiting:**
   - **Application Boundary:** The FastAPI application layer focuses on deterministic business logic, database transactions, authorization, and cryptographic integrity.
   - **Gateway Boundary:** Rate limiting for volumetric denial of service and distributed credential brute-force protection is enforced at the reverse proxy / API gateway layer (Nginx / Envoy / Cloudflare) with configured thresholds:
     - Public discovery & lookup: `60 requests / minute per client IP`.
     - Registration submission: `10 requests / minute per client IP`.
     - Check-in scanning (staff): `120 requests / minute per authenticated staff token`.

