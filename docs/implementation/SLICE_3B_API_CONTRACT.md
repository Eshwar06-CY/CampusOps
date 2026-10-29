# CampusOps — Slice 3B REST API Contract Specification

**Document Version:** 1.0  
**Status:** Implementation Baseline for Development Slice 3B  
**Authoritative References:** `Consolidated Documentation/CampusOps_API_Contract_Draft_v0.2.md`, `CampusOps_Data_Model_and_Relationship_Map_v0.1.md`, `CampusOps_Role_and_Permission_Matrix_v0.1.md`, and `CampusOps_Decision_Log_v1.5_Addendum.md` (D-SLICE3-01 through D-SLICE3-06).

---

## 1. Global Architectural & Security Conventions

1. **Base URL:** All API routes are prefixed with `/api/v1`.
2. **Authentication:** All requests require a valid Bearer token handled via `get_current_user`. In development/testing without an upstream identity provider configured, normal runtime fails closed with HTTP 401 Unauthorized.
3. **Pydantic v2 Models:** All mutation payloads enforce `extra="forbid"`. Unrecognized keys or injection of unauthorized audit/internal fields (`id`, `created_at`, `status`, `organization_id`, `created_by_user_id`, `token_hash`) are rejected with `HTTP 422 Unprocessable Entity`.
4. **Tenant Isolation & Non-Disclosing Responses:** All resource queries are strictly scoped to `organization_id`. Requests targeting nonexistent resources or resources belonging to another organization return `HTTP 404 Not Found` without disclosing cross-tenant existence.
5. **Organization Verification Gate (FPC-02 / FPC-03):** Operational creations and mutations (`programs`, `events`, `departments`, `leads`, `invitations`) are blocked with `HTTP 403 Forbidden` if the organization is in `pending_verification` status.
6. **Timezone Policy (D-SLICE3-05):** Events default to `Asia/Kolkata`. Any provided timezone string is strictly validated against the IANA timezone database (`zoneinfo.ZoneInfo`).
7. **Date/Time Ordering (D-SLICE3-05):**
   - Single-day events (`event_end_date IS NULL OR event_end_date == event_date`): `planned_end_time >= planned_start_time` when both are provided.
   - Multi-day events (`event_end_date > event_date`): `planned_end_time` may precede `planned_start_time` on the clock.
   - `event_end_date >= event_date` when `event_end_date` is provided.
   - For child events under a Program, event dates must fall within the Program's `planned_start_date` and `planned_end_date`.

---

## 2. Program Endpoints

### 2.1 `POST /api/v1/organizations/{organization_id}/programs`
Creates a multi-event program umbrella within an organization workspace.

- **Permissions:** `PRIMARY_ADMIN` or `OFFICE_BEARER` (`ACTION_CREATE_EVENT`). Organization must be `verified`.
- **Request Body (`ProgramCreateRequest`):**
  ```json
  {
    "name": "E-Week 2027",
    "description": "Annual Entrepreneurship Week",
    "planned_start_date": "2027-02-10",
    "planned_end_date": "2027-02-15"
  }
  ```
- **Responses:**
  - `201 Created` → `ProgramResponse`
  - `400 Bad Request` → Validation error (empty name, end date < start date, or duplicate name in organization)
  - `403 Forbidden` → Caller not authorized or organization unverified
  - `404 Not Found` → Organization not found or caller not a member

### 2.2 `GET /api/v1/organizations/{organization_id}/programs`
Lists active programs in the organization.

- **Permissions:** Any active member with a valid role in the organization.
- **Responses:**
  - `200 OK` → `List[ProgramResponse]`
  - `404 Not Found` → Organization not found or caller not a member

### 2.3 `GET /api/v1/organizations/{organization_id}/programs/{program_id}`
Retrieves program details, including summary counts of active child events and shared departments.

- **Permissions:** Any active member with a valid role in the organization.
- **Responses:**
  - `200 OK` → `ProgramResponse`
  - `404 Not Found` → Program does not exist, belongs to another organization, or is archived

### 2.4 `PATCH /api/v1/organizations/{organization_id}/programs/{program_id}`
Updates program metadata (name, description, planned dates).

- **Permissions:** `PRIMARY_ADMIN` or `OFFICE_BEARER`.
- **Request Body (`ProgramUpdateRequest`):** All fields optional.
  ```json
  {
    "name": "E-Week 2027 Renamed",
    "description": "Updated description",
    "planned_start_date": "2027-02-10",
    "planned_end_date": "2027-02-16"
  }
  ```
- **Responses:**
  - `200 OK` → `ProgramResponse`
  - `400 Bad Request` → Invalid date order, duplicate name, or narrowing date range such that existing child events fall outside
  - `403 Forbidden` → Insufficient role
  - `404 Not Found` → Program not found, foreign org, or archived

### 2.5 `POST /api/v1/organizations/{organization_id}/programs/{program_id}/archive`
Non-destructively archives a program (D-SLICE3-04). Preserves all child events and departments.

- **Permissions:** `PRIMARY_ADMIN` or `OFFICE_BEARER`.
- **Responses:**
  - `200 OK` → `ProgramResponse` (with `status: "archived"`, `archived_at` populated)
  - `404 Not Found` → Program not found, foreign org, or already archived

---

## 3. Event Endpoints

### 3.1 `POST /api/v1/organizations/{organization_id}/events`
Creates an operational event. Supports both workflows:
- **Workflow A (Standalone Event):** `program_id = null`
- **Workflow B (Child Event):** `program_id = "<uuid>"` (must belong to same org)

- **Permissions:** `PRIMARY_ADMIN` or `OFFICE_BEARER`. Organization must be `verified`.
- **Request Body (`EventCreateRequest`):**
  ```json
  {
    "name": "RoboWars 2027",
    "description": "Combat robotics competition",
    "program_id": null,
    "event_date": "2027-02-12",
    "event_end_date": "2027-02-13",
    "planned_start_time": "2027-02-12T10:00:00Z",
    "planned_end_time": "2027-02-13T02:00:00Z",
    "venue": "Campus Arena",
    "event_format": "in_person",
    "registration_mode": "team",
    "timezone": "Asia/Kolkata"
  }
  ```
- **Responses:**
  - `201 Created` → `EventResponse`
  - `400 Bad Request` → Cross-tenant program reference, archived parent program, invalid date/time sequencing, or invalid IANA timezone identifier
  - `403 Forbidden` → Caller not authorized or organization unverified
  - `404 Not Found` → Organization not found or parent program not found

### 3.2 `GET /api/v1/organizations/{organization_id}/events`
Lists events for the organization. Optional query param `program_id` filters by parent program; `program_id=null` or omitting returns all organization events.

- **Permissions:** Any active member with a valid role in the organization.
- **Responses:**
  - `200 OK` → `List[EventResponse]`
  - `404 Not Found` → Organization not found or caller not a member

### 3.3 `GET /api/v1/organizations/{organization_id}/programs/{program_id}/events`
Convenience sub-resource route listing child events specifically belonging to a program.

- **Permissions:** Any active member with a valid role in the organization.
- **Responses:**
  - `200 OK` → `List[EventResponse]`
  - `404 Not Found` → Program not found or caller not a member

### 3.4 `POST /api/v1/organizations/{organization_id}/programs/{program_id}/events`
Convenience sub-resource route creating a child event under a program.

- **Permissions:** `PRIMARY_ADMIN` or `OFFICE_BEARER`.

### 3.5 `GET /api/v1/organizations/{organization_id}/events/{event_id}`
Retrieves details for a specific event.

- **Permissions:** Active organization member.
- **Responses:**
  - `200 OK` → `EventResponse`
  - `404 Not Found` → Event does not exist, belongs to another organization, or is archived

### 3.6 `PATCH /api/v1/organizations/{organization_id}/events/{event_id}`
Updates event metadata, date, time, venue, or format.
- `program_id` cannot be modified (D-SLICE3-03: immutability of parentage).

- **Permissions:** `PRIMARY_ADMIN`, `OFFICE_BEARER`, or assigned `EVENT_LEAD` on this specific event.
- **Responses:**
  - `200 OK` → `EventResponse`
  - `400 Bad Request` → Invalid date/time sequencing, dates outside parent program range, invalid timezone, or attempt to re-parent event
  - `403 Forbidden` → Caller lacks permission on this event scope
  - `404 Not Found` → Event not found, foreign org, or archived

### 3.7 `POST /api/v1/organizations/{organization_id}/events/{event_id}/archive`
Non-destructively archives an event (D-SLICE3-04). Assigned leads cease having operational edit rights.

- **Permissions:** `PRIMARY_ADMIN` or `OFFICE_BEARER`.
- **Responses:**
  - `200 OK` → `EventResponse` (with `status: "archived"`, `archived_at` populated)
  - `404 Not Found` → Event not found, foreign org, or already archived

---

## 4. Department Endpoints

### 4.1 `POST /api/v1/organizations/{organization_id}/departments`
Creates a functional department. Enforces exclusive parentage (D-SLICE3-01):
- Program department: `program_id` populated, `standalone_event_id: null`
- Standalone event department: `standalone_event_id` populated, `program_id: null`
- Child events in a program cannot own separate departments in this release.

- **Permissions:** `PRIMARY_ADMIN` or `OFFICE_BEARER`. Organization must be `verified`.
- **Request Body (`DepartmentCreateRequest`):**
  ```json
  {
    "name": "Logistics & Facilities",
    "description": "Venue setup and equipment",
    "program_id": "<uuid>",
    "standalone_event_id": null
  }
  ```
- **Responses:**
  - `201 Created` → `DepartmentResponse`
  - `400 Bad Request` → Both parents set, neither parent set, child event parent, or cross-tenant parent
  - `403 Forbidden` → Caller not authorized or organization unverified
  - `404 Not Found` → Organization, parent program, or parent event not found

### 4.2 `GET /api/v1/organizations/{organization_id}/departments`
Lists departments in the organization. Optional query filters: `program_id`, `standalone_event_id`.

- **Permissions:** Active organization member.
- **Responses:**
  - `200 OK` → `List[DepartmentResponse]`

### 4.3 `GET /api/v1/organizations/{organization_id}/departments/{department_id}`
Retrieves department details.

- **Permissions:** Active organization member.
- **Responses:**
  - `200 OK` → `DepartmentResponse`
  - `404 Not Found` → Department not found, foreign org, or archived

### 4.4 `PATCH /api/v1/organizations/{organization_id}/departments/{department_id}`
Updates department name or description. Parent links (`program_id`, `standalone_event_id`) cannot be changed.

- **Permissions:** `PRIMARY_ADMIN` or `OFFICE_BEARER`.
- **Responses:**
  - `200 OK` → `DepartmentResponse`
  - `404 Not Found` → Department not found or archived

### 4.5 `POST /api/v1/organizations/{organization_id}/departments/{department_id}/archive`
Non-destructively archives a department.

- **Permissions:** `PRIMARY_ADMIN` or `OFFICE_BEARER`.
- **Responses:**
  - `200 OK` → `DepartmentResponse` (`status: "archived"`)

---

## 5. Event Lead Endpoints

### 5.1 `GET /api/v1/organizations/{organization_id}/events/{event_id}/leads`
Lists all currently active event lead assignments for an event.

- **Permissions:** Active organization member with access to the event.
- **Responses:**
  - `200 OK` → `List[EventLeadResponse]`
  - `404 Not Found` → Event not found or caller not a member

### 5.2 `POST /api/v1/organizations/{organization_id}/events/{event_id}/leads`
Assigns an eligible workspace member as an Event Lead.
- Requires target `membership_id` (belongs to active member in the same org, active user account, verified email).
- Transactionally creates both `EventLeadAssignment` and `RoleAssignment(role_name="EVENT_LEAD", scope_type="event")`.
- Enforces D-SLICE3-02: at most one active lead assignment per member per event.

- **Permissions:** `PRIMARY_ADMIN` or `OFFICE_BEARER` (`ACTION_MANAGE_ROLES`). Organization must be `verified`.
- **Request Body (`EventLeadAssignRequest`):**
  ```json
  {
    "membership_id": "<uuid>"
  }
  ```
- **Responses:**
  - `201 Created` → `EventLeadResponse`
  - `400 Bad Request` → Target member inactive, suspended, unverified email, or cross-tenant
  - `409 Conflict` → Member is already an active Event Lead for this event
  - `404 Not Found` → Event or member not found

### 5.3 `POST /api/v1/organizations/{organization_id}/events/{event_id}/leads/{assignment_id}/revoke`
Revokes an active Event Lead assignment with audit trail (`revoked_at` recorded).
- Transactionally marks the corresponding `RoleAssignment` as revoked.

- **Permissions:** `PRIMARY_ADMIN` or `OFFICE_BEARER`.
- **Responses:**
  - `200 OK` → `EventLeadResponse` (`revoked_at` populated)
  - `400 Bad Request` → Assignment already revoked
  - `404 Not Found` → Assignment not found or foreign event/org

---

## 6. Scoped Invitations Integration (Slice 3B Unblocking)

### 6.1 `POST /api/v1/organizations/{organization_id}/invitations`
Now supports:
- `scope_type="organization"`: `scope_id: null` (allowed roles: `OFFICE_BEARER`, `COORDINATOR`, `REGISTRATION_STAFF`)
- `scope_type="department"`: `scope_id: "<valid department uuid>"` (allowed roles: `DEPARTMENT_LEAD`, `COORDINATOR`)
- `scope_type="event"`: `scope_id: "<valid event uuid>"` (allowed roles: `EVENT_LEAD`, `COORDINATOR`, `REGISTRATION_STAFF`)

**Enforcements:**
- Rejects non-existent, cross-tenant, or archived target departments/events with `HTTP 400 Bad Request` or `HTTP 404 Not Found`.
- Rejects `role_name="PRIMARY_ADMIN"` with `HTTP 403 Forbidden`.
- Rejects role/scope mismatches with `HTTP 400 Bad Request`.
- Fails closed with `HTTP 503 Service Unavailable` if transactional email is unconfigured.
- Raw token is never returned in HTTP responses.

### 6.2 `POST /api/v1/invitations/accept`
Accepts raw token in JSON body (`{"token": "..."}`).
- Atomically creates `OrganizationMembership` (or reactivates previously removed membership).
- Creates scoped `RoleAssignment`.
- **Special Atomicity for `EVENT_LEAD`:** If `role_name == "EVENT_LEAD"` and `scope_type == "event"`, atomically creates `EventLeadAssignment` in the exact same transaction, rolling back everything if any part fails.

