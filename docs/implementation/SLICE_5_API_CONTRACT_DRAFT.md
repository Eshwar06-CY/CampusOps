# CampusOps — Slice 5 REST API Contract Draft

**Date:** 29 October 2026  
**Status:** Draft API Contract for Slice 5 Implementation  
**Authoritative Baseline:** `Consolidated Documentation/CampusOps_API_Contract_Draft_v0.2.md`, `CampusOps_PRD_v1.1.md` (CO-FR-008, CO-FR-009), `CampusOps_Technical_Specification_v1.1.md` Section 3.4, and `CampusOps_Role_and_Permission_Matrix_v0.1.md`.

---

## 1. Global Conventions & Trust Boundaries

### 1.1 Dual API Namespaces
Slice 5 routes are cleanly partitioned into two distinct namespaces reflecting their trust boundaries:
1. **Public Participant Namespace (`/api/v1/public/...`):**
   - Unauthenticated, self-service endpoints accessible by prospective attendees.
   - Addressed by an unguessable high-entropy `public_event_key` (UUIDv4) to prevent event enumeration.
   - Enforces IP and submission-rate throttling, bot-abuse countermeasures, and strict personal data minimization.
   - Does not disclose roster lists, attendance numbers, internal organizer identities, or other attendees' data.
2. **Staff Operational Namespace (`/api/v1/organizations/{org_id}/events/{event_id}/...`):**
   - Authenticated, role-gated endpoints for workspace administrators, event leads, and check-in volunteers.
   - Strictly enforces CampusOps deny-by-default RBAC and multi-tenant isolation.
   - Cross-tenant requests return uniform `HTTP 404 Not Found` to prevent entity enumeration.

### 1.2 Pydantic Validation & Security Conventions
- All mutation request models enforce `model_config = ConfigDict(extra="forbid")` to block parameter pollution and client ID injection.
- Response serialization models enforce `from_attributes=True` and censor private fields based on the caller's authorized permissions.
- Idempotency: Duplicate check-in attempts return a successful HTTP response with `status: "already_checked_in"` without inflating counts or altering timestamps.

---

## 2. Public Participant-Facing Endpoints

### 2.1 `GET /api/v1/public/events/{public_event_key}`
- **Description:** Retrieves public event details and current registration availability.
- **Authentication:** None (Public).
- **Responses:**
  - `200 OK`:
    ```json
    {
      "public_event_key": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
      "event_name": "Apex Annual Hackathon 2026",
      "description": "24-hour collaborative coding challenge.",
      "event_date": "2026-11-20",
      "event_end_date": "2026-11-21",
      "venue": "Campus Main Auditorium",
      "timezone": "Asia/Kolkata",
      "registration_status": "open",
      "registration_format": "team_only",
      "team_size_min": 2,
      "team_size_max": 4,
      "capacity_available": true
    }
    ```
  - `404 Not Found`: Event not found, registration unconfigured, or event archived.

---

### 2.2 `POST /api/v1/public/events/{public_event_key}/registrations`
- **Description:** Submits a native self-service registration (solo or team).
- **Authentication:** None (Public).
- **Rate Limit:** 5 requests per minute per IP.
- **Request Body (`PublicRegistrationRequest`):**
  ```json
  {
    "registration_type": "team",
    "team_name": "ByteCrafters",
    "contact_email": "lead@college.edu",
    "contact_phone": "+919876543210",
    "participants": [
      {
        "full_name": "Aarav Sharma",
        "email": "lead@college.edu",
        "phone_number": "+919876543210",
        "college_name": "Apex Engineering College",
        "student_id": "APEX-2023-CS-042",
        "is_primary_contact": true,
        "team_role": "Team Lead"
      },
      {
        "full_name": "Diya Patel",
        "email": "diya.patel@college.edu",
        "phone_number": "+919876543211",
        "college_name": "Apex Engineering College",
        "student_id": "APEX-2023-CS-088",
        "is_primary_contact": false,
        "team_role": "Member"
      }
    ]
  }
  ```
- **Responses:**
  - `201 Created`: Returns confirmation and individualized digital admission passes for every attendee:
    ```json
    {
      "registration_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "confirmation_code": "REG-HACK-8392",
      "registration_status": "confirmed",
      "registration_type": "team",
      "team_name": "ByteCrafters",
      "passes": [
        {
          "participant_id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
          "participant_name": "Aarav Sharma",
          "pass_code": "CO-PASS-8B1A2C3D4E5F6G7H",
          "pass_url": "https://campusops.internal/passes/CO-PASS-8B1A2C3D4E5F6G7H"
        },
        {
          "participant_id": "5fa85f64-5717-4562-b3fc-2c963f66afa8",
          "participant_name": "Diya Patel",
          "pass_code": "CO-PASS-9A2B3C4D5E6F7G8H",
          "pass_url": "https://campusops.internal/passes/CO-PASS-9A2B3C4D5E6F7G8H"
        }
      ]
    }
    ```
  - `400 Bad Request`: Registration closed, capacity exhausted, invalid team size, or duplicate email.
  - `422 Unprocessable Entity`: Schema validation or missing mandatory fields.

---

### 2.3 `GET /api/v1/public/events/{public_event_key}/passes/{pass_code}`
- **Description:** Secure attendee pass rendering endpoint. Returns pass details and QR payload.
- **Authentication:** None (Protected by 128-bit unguessable pass token).
- **Responses:**
  - `200 OK`:
    ```json
    {
      "pass_code": "CO-PASS-8B1A2C3D4E5F6G7H",
      "event_name": "Apex Annual Hackathon 2026",
      "participant_name": "Aarav Sharma",
      "status": "issued",
      "issued_at": "2026-10-29T10:30:00Z",
      "qr_payload": "CO-PASS-8B1A2C3D4E5F6G7H",
      "instructions": "Present this digital pass at the registration desk for individual check-in."
    }
    ```
  - `404 Not Found`: Invalid or revoked pass code.

---

## 3. Staff-Facing Registration & Capacity Management

### 3.1 `GET /api/v1/organizations/{organization_id}/events/{event_id}/registration-settings`
- **Description:** Retrieves event registration settings, capacity limits, and real-time counters.
- **Permission Required:** `ACTION_VIEW_EVENT` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`, `COORDINATOR`).
- **Responses:** `200 OK` (returns settings model), `403 Forbidden`, `404 Not Found`.

### 3.2 `PUT /api/v1/organizations/{organization_id}/events/{event_id}/registration-settings`
- **Description:** Updates registration settings, capacity limits, format, and scheduling windows.
- **Permission Required:** `ACTION_CONFIGURE_REGISTRATION` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`).
- **Request Body (`EventRegistrationSettingsUpdateRequest`):**
  ```json
  {
    "is_open": true,
    "registration_format": "team_only",
    "capacity_limit": 200,
    "team_size_min": 2,
    "team_size_max": 4,
    "waitlist_enabled": false,
    "registration_open_at": "2026-11-01T00:00:00Z",
    "registration_close_at": "2026-11-18T23:59:59Z"
  }
  ```
- **Responses:** `200 OK`, `400 Bad Request` (invalid dates/sizes), `403 Forbidden`, `404 Not Found`.

### 3.3 `GET /api/v1/organizations/{organization_id}/events/{event_id}/registrations`
- **Description:** Lists registration transaction headers with filters.
- **Permission Required:** `ACTION_VIEW_ROSTER` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`, `REGISTRATION_STAFF`).
- **Query Parameters:** `status: Optional[str]`, `registration_type: Optional[str]`, `limit: int = 50`, `offset: int = 0`.
- **Responses:** `200 OK` (returns `List[RegistrationSummaryResponse]`), `403 Forbidden`, `404 Not Found`.

### 3.4 `POST /api/v1/organizations/{organization_id}/events/{event_id}/registrations/walk-in`
- **Description:** Staff-assisted walk-in registration at the check-in desk.
- **Permission Required:** `ACTION_CHECK_IN` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`, `REGISTRATION_STAFF`).
- **Request Body:** Same schema as public registration, tagged with `registration_channel = 'walk_in'`.
- **Responses:** `201 Created` (returns confirmed registration and issued pass), `400 Bad Request`.

### 3.5 `POST /api/v1/organizations/{organization_id}/events/{event_id}/registrations/{registration_id}/cancel`
- **Description:** Cancels a registration, releasing capacity and invalidating all associated passes.
- **Permission Required:** `ACTION_MANAGE_ROSTER` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`).
- **Request Body:** `{"cancellation_reason": "Team withdrew due to exam schedule."}`
- **Responses:** `200 OK`, `400 Bad Request` (already cancelled or checked in), `403 Forbidden`, `404 Not Found`.

---

## 4. Staff-Facing Participant Roster Management

### 4.1 `GET /api/v1/organizations/{organization_id}/events/{event_id}/participants`
- **Description:** Lists individual attendee roster records with search and status filtering. Contact fields are masked unless the caller holds `ACTION_VIEW_ATTENDEE_CONTACT`.
- **Permission Required:** `ACTION_VIEW_ROSTER` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`, `REGISTRATION_STAFF`).
- **Query Parameters:** `search: Optional[str]`, `status: Optional[str]`, `limit: int = 50`, `offset: int = 0`.
- **Responses:** `200 OK` (returns `List[ParticipantRosterItemResponse]`).

### 4.2 `GET /api/v1/organizations/{organization_id}/events/{event_id}/participants/{participant_id}`
- **Description:** Retrieves detailed participant record and associated ticket pass status.
- **Permission Required:** `ACTION_VIEW_ROSTER`. Contact information is unmasked only if caller has `ACTION_VIEW_ATTENDEE_CONTACT`.

### 4.3 `PATCH /api/v1/organizations/{organization_id}/events/{event_id}/participants/{participant_id}`
- **Description:** Corrects attendee details (typos in name, college, or roll number).
- **Permission Required:** `ACTION_MANAGE_ROSTER` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`).
- **Request Body (`ParticipantUpdateRequest`):**
  ```json
  {
    "full_name": "Aarav K. Sharma",
    "college_name": "Apex Institute of Technology",
    "student_id": "APEX-2023-CS-042"
  }
  ```
- **Responses:** `200 OK`, `400 Bad Request`, `403 Forbidden`, `404 Not Found`.

### 4.4 `POST /api/v1/organizations/{organization_id}/events/{event_id}/participants/{participant_id}/reissue-pass`
- **Description:** Invalidates existing pass and generates a new opaque pass credential for an attendee.
- **Permission Required:** `ACTION_MANAGE_ROSTER` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`).
- **Request Body:** `{"reason": "Attendee lost access to original digital pass."}`
- **Responses:** `200 OK` (returns newly issued `TicketResponse`).

---

## 5. Staff-Facing Attendance Check-In Endpoints

### 5.1 `POST /api/v1/organizations/{organization_id}/events/{event_id}/check-ins`
- **Description:** Checks in an individual attendee via QR pass token or manual participant ID.
- **Permission Required:** `ACTION_CHECK_IN` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`, `REGISTRATION_STAFF`).
- **Request Body (`CheckInRequest`):**
  ```json
  {
    "pass_code": "CO-PASS-8B1A2C3D4E5F6G7H",
    "participant_id": null,
    "method": "qr_scan",
    "station_id": "DESK-NORTH-1"
  }
  ```
- **Responses:**
  - `200 OK (Verified)`:
    ```json
    {
      "check_in_id": "1fa85f64-5717-4562-b3fc-2c963f66afa1",
      "status": "verified",
      "participant_id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
      "participant_name": "Aarav Sharma",
      "team_name": "ByteCrafters",
      "checked_in_at": "2026-11-20T08:45:12Z",
      "station_id": "DESK-NORTH-1"
    }
    ```
  - `200 OK (Idempotent Duplicate Scan)`:
    ```json
    {
      "check_in_id": "1fa85f64-5717-4562-b3fc-2c963f66afa1",
      "status": "already_checked_in",
      "participant_id": "4fa85f64-5717-4562-b3fc-2c963f66afa7",
      "participant_name": "Aarav Sharma",
      "checked_in_at": "2026-11-20T08:45:12Z",
      "station_id": "DESK-NORTH-1",
      "message": "Attendee was already checked in at 08:45:12."
    }
    ```
  - `400 Bad Request`: Ticket revoked, cancelled, or event mismatch.
  - `403 Forbidden`: Caller lacks check-in authority.
  - `404 Not Found`: Pass code or event not found.

---

### 5.2 `GET /api/v1/organizations/{organization_id}/events/{event_id}/check-in-lookup`
- **Description:** Fast lookup resolving scanned QR code or manual search query for verification.
- **Permission Required:** `ACTION_CHECK_IN`.
- **Query Parameters:** `q: str` (pass code or participant name/email prefix).
- **Responses:** `200 OK` (returns participant summary with masked contact details and check-in eligibility).

---

### 5.3 `POST /api/v1/organizations/{organization_id}/events/{event_id}/check-ins/{check_in_id}/void`
- **Description:** Voids/corrects an accidental check-in record with a mandatory audit reason.
- **Permission Required:** `ACTION_CORRECT_CHECK_IN` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`). Ordinary registration desk staff are denied (HTTP 403).
- **Request Body (`CheckInVoidRequest`):**
  ```json
  {
    "reason": "Accidental manual check-in of wrong attendee; attendee confirmed not present."
  }
  ```
- **Responses:**
  - `200 OK`:
    ```json
    {
      "check_in_id": "1fa85f64-5717-4562-b3fc-2c963f66afa1",
      "check_in_status": "voided",
      "voided_at": "2026-11-20T09:15:00Z",
      "reason": "Accidental manual check-in of wrong attendee; attendee confirmed not present."
    }
    ```
  - `400 Bad Request`: Check-in already voided or missing mandatory reason.
  - `403 Forbidden`: Caller lacks managerial correction authority.
  - `404 Not Found`: Check-in not found.

---

## 6. Staff-Facing Attendance Reporting & Exports

### 6.1 `GET /api/v1/organizations/{organization_id}/events/{event_id}/attendance-summary`
- **Description:** Real-time operational attendance metrics.
- **Permission Required:** `ACTION_VIEW_ATTENDANCE_REPORT` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`, `COORDINATOR`).
- **Responses:**
  - `200 OK`:
    ```json
    {
      "event_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "capacity_limit": 200,
      "total_registered_individual": 192,
      "total_confirmed_participants": 192,
      "total_attended_participants": 164,
      "attendance_percentage": 85.42,
      "total_teams_registered": 48,
      "teams_fully_attended": 38,
      "teams_partially_attended": 8,
      "teams_absent": 2
    }
    ```

### 6.2 `GET /api/v1/organizations/{organization_id}/events/{event_id}/roster-export`
- **Description:** Exports normalized participant and check-in roster as a downloadable CSV.
- **Permission Required:** `ACTION_EXPORT_PARTICIPANTS` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`).
- **Responses:**
  - `200 OK`: `text/csv` stream with header `Content-Disposition: attachment; filename="roster_{event_id}.csv"`.
  - `403 Forbidden`: Caller lacks export authorization.

