# CampusOps — Slice 4B REST API Contract

**Date:** 29 October 2026  
**Status:** Frozen Implementation Contract for Slice 4B  
**Authoritative Baseline:** `Consolidated Documentation/CampusOps_API_Contract_Draft_v0.2.md`, `CampusOps_PRD_v1.1.md`, `CampusOps_Technical_Specification_v1.1.md`, and `Consolidated Documentation/CampusOps_Decision_Log_v1.6_Addendum.md` (D-SLICE4-01).

---

## 1. Global Architectural & Security Conventions

1. **URL Prefix & Versioning:** All endpoints are hosted under `/api/v1`.
2. **Tenant Scoping & Anti-Enumeration:**
   - All task and operational blocker endpoints are strictly organization-scoped: `/organizations/{organization_id}/tasks...` and `/organizations/{organization_id}/blockers...`.
   - Access attempts targeting non-existent, archived, or foreign organizations return `HTTP 404 Not Found` with detail `"Organization not found."` to eliminate cross-tenant existence enumeration.
   - Access attempts to tasks or blockers belonging to an organization other than the URL path return `HTTP 404 Not Found`.
3. **Fail-Closed Authentication:**
   - Every protected route enforces `get_current_user`, resolving an active `UserProfile` with a verified email from trusted authentication claims.
   - Unauthenticated requests fail closed with `HTTP 401 Unauthorized`.
   - Acting-user identity (`created_by_user_id`, `actor_id`, `changed_by_user_id`) is strictly extracted from the authenticated principal on the server; caller-supplied IDs in request payloads are forbidden.
4. **Strict Schema Validation (`extra="forbid"`):**
   - All mutation request bodies reject extraneous, unrecognized, or client-injected fields with `HTTP 422 Unprocessable Entity`.
5. **No Data/Secret Leakage:**
   - No endpoints expose internal database tracebacks, raw credentials, or private file references.
   - Evidence URLs are syntactically validated; no server-side HTTP fetches are executed.

---

## 2. Task Management API Routes

### 2.1 `POST /api/v1/organizations/{organization_id}/tasks`
- **Description:** Creates an operational task within a verified organization.
- **Permission Required:** `ACTION_CREATE_TASK` within the requested scope (`organization`, `program`, `event`, or `department`).
- **Preconditions:** Organization must be verified; parent scopes must be active (non-archived); deadline (`due_date`) is required; timezone must be valid IANA identifier.
- **Request Body (`TaskCreateRequest`):**
  ```json
  {
    "title": "Audio Setup",
    "description": "Configure main stage mixer and microphones",
    "due_date": "2026-11-15",
    "due_time": "14:00:00",
    "timezone": "Asia/Kolkata",
    "priority": "high",
    "proof_required": true,
    "scope_type": "event",
    "scope_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "assignee_membership_id": "4fa85f64-5717-4562-b3fc-2c963f66afa7"
  }
  ```
- **Responses:**
  - `201 Created`: Returns `TaskResponse`.
  - `400 Bad Request`: Scope integrity error, missing deadline, or invalid timezone.
  - `403 Forbidden`: Caller lacks `ACTION_CREATE_TASK` or organization is unverified.
  - `404 Not Found`: Organization or referenced scope not found.
  - `422 Unprocessable Entity`: Extra fields or schema validation error.

### 2.2 `GET /api/v1/organizations/{organization_id}/tasks`
- **Description:** Lists tasks that the caller is authorized to view within the organization.
- **Permission Required:** `ACTION_VIEW_TASK` per task item. Non-authorized tasks (such as sibling event tasks for an Event Lead, or unrelated department tasks for a Department Lead) are excluded from the result.
- **Query Parameters:**
  - `status: Optional[str]` (e.g. `not_started`, `assigned`, `in_progress`, `submitted_for_review`, `completed`, `cancelled`)
  - `scope_type: Optional[str]` (`organization`, `program`, `event`, `department`)
  - `scope_id: Optional[UUID]`
  - `assigned_to_me: bool = false` (filters to tasks where caller is the active assignee)
  - `limit: int = 50` (bounded: 1–100)
  - `offset: int = 0` (min: 0)
- **Responses:**
  - `200 OK`: Returns `List[TaskResponse]`.
  - `401 Unauthorized`: Unauthenticated.
  - `404 Not Found`: Organization not found.

### 2.3 `GET /api/v1/organizations/{organization_id}/tasks/{task_id}`
- **Description:** Retrieves an individual task.
- **Permission Required:** `ACTION_VIEW_TASK` on the task.
- **Responses:**
  - `200 OK`: Returns `TaskResponse`.
  - `403 Forbidden`: Caller lacks view permission.
  - `404 Not Found`: Organization or task not found, or task belongs to another tenant.

### 2.4 `PATCH /api/v1/organizations/{organization_id}/tasks/{task_id}`
- **Description:** Updates permitted task metadata (title, description, priority).
- **Permission Required:** `ACTION_UPDATE_TASK` on the task.
- **Preconditions:** Task must not be in terminal status (`completed` or `cancelled`). Deadline changes, assignment changes, and status transitions must use dedicated audited endpoints.
- **Request Body (`TaskUpdateRequest`):**
  ```json
  {
    "title": "Updated Title",
    "description": "Updated Description",
    "priority": "critical"
  }
  ```
- **Responses:**
  - `200 OK`: Returns `TaskResponse`.
  - `400 Bad Request`: Task in terminal status.
  - `403 Forbidden`: Permission denied.
  - `404 Not Found`: Task not found.

### 2.5 `POST /api/v1/organizations/{organization_id}/tasks/{task_id}/assign`
- **Description:** Assigns or reassigns the single accountable worker for a task (D-SLICE4-01).
- **Permission Required:** `ACTION_ASSIGN_TASK` on the task.
- **Preconditions:**
  - Task must not be in terminal status (`completed` or `cancelled`).
  - Assignee must hold an active membership in the same organization.
  - Prior active assignee is deactivated (`assignment_status = 'unassigned'`) and preserved in history.
- **Request Body (`TaskAssignRequest`):**
  ```json
  {
    "assignee_membership_id": "4fa85f64-5717-4562-b3fc-2c963f66afa7"
  }
  ```
- **Responses:**
  - `200 OK`: Returns `TaskResponse`.
  - `400 Bad Request`: Ineligible membership, duplicate active assignment, or terminal task status.
  - `403 Forbidden`: Caller lacks assignment authority.
  - `404 Not Found`: Task or organization not found.

### 2.6 `POST /api/v1/organizations/{organization_id}/tasks/{task_id}/start`
- **Description:** Transitions task from `not_started`, `assigned`, or `changes_requested` to `in_progress`.
- **Permission Required:** Active assignee on the task, or authorized manager with `ACTION_UPDATE_TASK`.
- **Preconditions:** Task must be in status `not_started`, `assigned`, or `changes_requested`.
- **Responses:**
  - `200 OK`: Returns `TaskResponse`.
  - `400 Bad Request`: Invalid state machine transition.
  - `403 Forbidden`: Permission denied.
  - `404 Not Found`: Task not found.

### 2.7 `POST /api/v1/organizations/{organization_id}/tasks/{task_id}/cancel`
- **Description:** Cancels an active task with mandatory audit reason.
- **Permission Required:** `ACTION_UPDATE_TASK` on the task.
- **Preconditions:** Task must not be in terminal status (`completed` or `cancelled`). Non-empty reason required.
- **Request Body (`TaskCancelRequest`):**
  ```json
  {
    "cancellation_reason": "Event speaker rescheduled; setup not needed."
  }
  ```
- **Responses:**
  - `200 OK`: Returns `TaskResponse`.
  - `400 Bad Request`: Missing reason or already terminal.
  - `403 Forbidden`: Caller lacks update authority.
  - `404 Not Found`: Task not found.

### 2.8 `GET /api/v1/organizations/{organization_id}/tasks/{task_id}/history`
- **Description:** Retrieves status history, deadline history, and assignee history for a task.
- **Permission Required:** `ACTION_VIEW_TASK` on the task.
- **Responses:**
  - `200 OK`: Returns `TaskHistoryResponse`.
  - `403 Forbidden`: Permission denied.
  - `404 Not Found`: Task not found.

---

## 3. Deadline Operations

### 3.1 `POST /api/v1/organizations/{organization_id}/tasks/{task_id}/deadline`
- **Description:** Adjusts a task's deadline with mandatory reason and immutable audit preservation.
- **Permission Required:** `ACTION_CHANGE_DEADLINE` on the task.
- **Preconditions:**
  - Task must not be in terminal status (`completed` or `cancelled`).
  - `new_due_date` is mandatory.
  - `reason` must be non-empty.
- **Request Body (`TaskDeadlineChangeRequest`):**
  ```json
  {
    "new_due_date": "2026-11-20",
    "new_due_time": "18:00:00",
    "reason": "Stage vendor delayed delivery."
  }
  ```
- **Responses:**
  - `200 OK`: Returns `TaskResponse`.
  - `400 Bad Request`: Missing reason, missing date, or terminal status.
  - `403 Forbidden`: Permission denied.
  - `404 Not Found`: Task not found.

---

## 4. Submission & Review Workflows

### 4.1 `POST /api/v1/organizations/{organization_id}/tasks/{task_id}/submissions`
- **Description:** Submits completion proof for review.
- **Permission Required:** Caller must be the **active assignee** on the task.
- **Preconditions:**
  - Task must be in status `assigned`, `in_progress`, or `changes_requested`.
  - If `proof_required == True`, at least one valid evidence URL must be provided.
  - URLs must be absolute HTTPS/HTTP with valid hostname (max 2048 chars).
  - Automatically increments `submission_number` and transitions task to `submitted_for_review`.
- **Request Body (`EvidenceSubmissionRequest`):**
  ```json
  {
    "evidence_urls": ["https://drive.google.com/file/d/example123"],
    "submitter_note": "Audio check verified with stage lead."
  }
  ```
- **Responses:**
  - `201 Created`: Returns `EvidenceSubmissionResponse`.
  - `400 Bad Request`: Invalid evidence URL or missing required proof.
  - `403 Forbidden`: Caller is not an active assignee.
  - `404 Not Found`: Task not found.

### 4.2 `GET /api/v1/organizations/{organization_id}/tasks/{task_id}/submissions`
- **Description:** Lists all evidence submissions and reviews for a task.
- **Permission Required:** `ACTION_VIEW_TASK` on the task.
- **Responses:**
  - `200 OK`: Returns `List[EvidenceSubmissionResponse]`.
  - `403 Forbidden`: Permission denied.
  - `404 Not Found`: Task not found.

### 4.3 `POST /api/v1/organizations/{organization_id}/tasks/{task_id}/submissions/{submission_id}/review`
- **Description:** Approves or requests changes on an evidence submission.
- **Permission Required:** `ACTION_REVIEW_PROOF` on the task scope.
- **Preconditions:**
  - **Self-Review Prohibition:** Submitter and active assignees cannot review their own work.
  - `decision` must be `"approved"` or `"changes_requested"`.
  - If `"changes_requested"`, a non-empty `review_note` is mandatory.
  - Submission must be in `pending_review` status. Duplicate/conflicting reviews are rejected.
  - If approved, task transitions to `completed` and records `completed_at`.
  - If changes requested, task transitions to `changes_requested`.
- **Request Body (`TaskReviewRequest`):**
  ```json
  {
    "decision": "changes_requested",
    "review_note": "Stage mic 2 has static noise; please re-test and submit updated log."
  }
  ```
- **Responses:**
  - `200 OK`: Returns `TaskReviewResponse`.
  - `400 Bad Request`: Missing review note for rejection, invalid decision, self-review attempt, or submission already reviewed.
  - `403 Forbidden`: Caller lacks review authority or self-review prohibited.
  - `404 Not Found`: Submission or task not found.

---

## 5. Staff-Only Operational Blockers API Routes

### 5.1 `POST /api/v1/organizations/{organization_id}/blockers`
- **Description:** Creates an internal operational blocker.
- **Permission Required:** `ACTION_CREATE_BLOCKER` within the target scope. Restricted to internal staff roles (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`, `DEPARTMENT_LEAD`, `COORDINATOR`).
- **Preconditions:** Organization must be verified; scopes must belong to the organization and be non-archived.
- **Request Body (`OperationalBlockerCreateRequest`):**
  ```json
  {
    "title": "Main Hall Locked",
    "description": "Facilities manager has not arrived with keys.",
    "scope_type": "event",
    "scope_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "priority": "critical",
    "owner_membership_id": "4fa85f64-5717-4562-b3fc-2c963f66afa7"
  }
  ```
- **Responses:**
  - `201 Created`: Returns `OperationalBlockerResponse`.
  - `400 Bad Request`: Scope integrity error.
  - `403 Forbidden`: Permission denied or organization unverified.
  - `404 Not Found`: Scope not found.

### 5.2 `GET /api/v1/organizations/{organization_id}/blockers`
- **Description:** Lists operational blockers within the caller's authorized scope.
- **Query Parameters:**
  - `status: Optional[str]` (`open`, `in_progress`, `resolved`, `wont_fix`)
  - `scope_type: Optional[str]`
  - `scope_id: Optional[UUID]`
  - `task_id: Optional[UUID]`
  - `limit: int = 50`
  - `offset: int = 0`
- **Responses:**
  - `200 OK`: Returns `List[OperationalBlockerResponse]`.
  - `401 Unauthorized`: Unauthenticated.
  - `404 Not Found`: Organization not found.

### 5.3 `GET /api/v1/organizations/{organization_id}/blockers/{blocker_id}`
- **Description:** Retrieves detailed blocker information including history.
- **Permission Required:** `ACTION_VIEW_BLOCKER` on the blocker's scope.
- **Responses:**
  - `200 OK`: Returns `OperationalBlockerDetailResponse`.
  - `403 Forbidden`: Permission denied.
  - `404 Not Found`: Blocker not found.

### 5.4 `PATCH /api/v1/organizations/{organization_id}/blockers/{blocker_id}`
- **Description:** Updates permitted blocker metadata (title, description, priority, owner).
- **Permission Required:** `ACTION_RESOLVE_BLOCKER` or `ACTION_CREATE_BLOCKER` on the blocker.
- **Preconditions:** Cannot update a blocker in `resolved` or `wont_fix` status without reopening it.
- **Responses:**
  - `200 OK`: Returns `OperationalBlockerResponse`.
  - `400 Bad Request`: Blocker in closed status.
  - `403 Forbidden`: Permission denied.
  - `404 Not Found`: Blocker not found.

### 5.5 `POST /api/v1/organizations/{organization_id}/blockers/{blocker_id}/resolve`
- **Description:** Resolves an operational blocker with mandatory note and actor audit.
- **Permission Required:** `ACTION_RESOLVE_BLOCKER` on the blocker.
- **Request Body (`OperationalBlockerResolveRequest`):**
  ```json
  {
    "resolution_note": "Facilities officer unlocked hall at 08:30.",
    "status": "resolved"
  }
  ```
- **Responses:**
  - `200 OK`: Returns `OperationalBlockerResponse`.
  - `400 Bad Request`: Missing resolution note or blocker already resolved.
  - `403 Forbidden`: Permission denied.
  - `404 Not Found`: Blocker not found.

### 5.6 `POST /api/v1/organizations/{organization_id}/blockers/{blocker_id}/reopen`
- **Description:** Reopens a previously resolved or `wont_fix` blocker.
- **Permission Required:** `ACTION_RESOLVE_BLOCKER` on the blocker.
- **Request Body (`OperationalBlockerReopenRequest`):**
  ```json
  {
    "reason": "Air conditioning unit failed again after initial restart."
  }
  ```
- **Responses:**
  - `200 OK`: Returns `OperationalBlockerResponse`.
  - `400 Bad Request`: Missing reason or blocker is already open.
  - `403 Forbidden`: Permission denied.
  - `404 Not Found`: Blocker not found.

---

## 6. In-App Notification API Routes

### 6.1 `GET /api/v1/notifications`
- **Description:** Lists in-app notifications for the authenticated user.
- **Permission Required:** Authenticated caller (access strictly scoped to `current_user.id`).
- **Query Parameters:**
  - `organization_id: Optional[UUID]`
  - `unread_only: bool = false`
  - `limit: int = 50`
  - `offset: int = 0`
- **Responses:**
  - `200 OK`: Returns `List[NotificationResponse]`.
  - `401 Unauthorized`: Unauthenticated.

### 6.2 `POST /api/v1/notifications/{notification_id}/read`
- **Description:** Marks a notification as read.
- **Permission Required:** Caller must be the intended recipient (`notification.user_id == current_user.id`). Attempting to mark another user's notification returns `HTTP 404 Not Found`.
- **Responses:**
  - `200 OK`: Returns `NotificationResponse`.
  - `404 Not Found`: Notification not found or access denied.

