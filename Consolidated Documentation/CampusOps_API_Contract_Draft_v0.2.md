# CampusOps — API Contract Draft

**Version:** 0.2  
**Status:** Draft v0.2 after traceability review; not approved for implementation  
**Date:** 2026-10-28  
**Working mode:** Documentation only. This document specifies proposed API behavior; it does not contain implemented endpoints.

## 1. Purpose

Define a consistent first-pass HTTP API for CampusOps across organization accounts, invitations and memberships, standalone events, multi-event programs, departments, tasks, proof review, registration, individual check-in, and post-event documentation.

This draft uses REST conventions and JSON payloads as a shared discussion baseline. Authentication provider, email provider, file-storage provider, external registration provider, hosting, offline check-in behavior, and several permission defaults remain undecided. Provider-specific behavior must not be treated as final until those decisions are recorded.

## 2. Confirmed product directions represented here

1. Each organization has a workspace; every office bearer and team member has an individual account. No shared club login.
2. CampusOps supports two setup workflows: standalone event and multi-event program.
3. Standalone workflow: the event defines its departments and assigns a lead for each required department. Leads can manage their department's members and work within permissions. Office bearers and authorized core members may assign work to leads or coordinators.
4. Multi-event workflow: a program contains multiple child events and has shared departments. Leads are assigned to particular events rather than appointed as department leads by default. Coordinators are assigned to shared departments and specific event work.
5. Workspace members can discover members across events. Exact visibility of personal email/phone remains undecided; directory access does not imply access to private attendee or evidence data.
6. Tasks have specific deadlines, owners, progress, and—when required—proof submitted as a file or link. Proof-required tasks become completed only after authorized review. Rejections require a note and notification.
7. Registration can be native or via an external source. Solo or team registration must result in individual participant records and individual check-in decisions.
8. Post-event records include event details, registration and attendance, supporting evidence, reports, and closure status.
9. Marketing campaign management, promotional activity tracking, poster/reel creation, and social publishing are out of scope.
10. Participant-facing doubts, questions, or issue submission are out of scope. Any future staff-only operational issue capability would require separate confirmation and must not become attendee support ticketing.
11. No application code or integrations are authorized by this document.

## 3. API conventions

### 3.1 Base path and media type

Proposed base path: `/api/v1`.

- Requests and responses use `application/json`, except binary upload/download flows.
- IDs are opaque strings (UUID-like values are recommended, but the physical format is not finalized).
- Timestamps are ISO 8601 UTC instants. Event-local date/time fields include an explicit IANA time-zone identifier when a time-of-day is relevant.
- List endpoints use cursor pagination by default: `?limit=50&cursor=...`.
- Filtering and sorting must be documented per endpoint. Do not expose unrestricted query languages to clients.
- State-changing operations should support request idempotency where retrying can create duplicate invitations, imports, registrations, evidence submissions, or check-ins.

### 3.2 Common response shape

Successful single-resource response (illustrative):

```json
{
  "data": {
    "id": "evt_opaque_id",
    "name": "Example Workshop"
  },
  "meta": {
    "request_id": "req_opaque_id"
  }
}
```

List response (illustrative):

```json
{
  "data": [],
  "page": {
    "next_cursor": null,
    "has_more": false
  },
  "meta": {
    "request_id": "req_opaque_id"
  }
}
```

Error response (illustrative):

```json
{
  "error": {
    "code": "permission_denied",
    "message": "You do not have permission to perform this action.",
    "details": [],
    "request_id": "req_opaque_id"
  }
}
```

Avoid including private fields, raw provider errors, stack traces, tokens, or sensitive participant data in errors or logs.

### 3.3 Common status codes

- `200 OK`: successful read or update.
- `201 Created`: new resource created.
- `202 Accepted`: asynchronous work accepted, such as a verification or import job.
- `204 No Content`: successful deletion/revocation where no body is needed.
- `400 Bad Request`: malformed request or invalid state transition.
- `401 Unauthorized`: no valid authentication.
- `403 Forbidden`: authenticated but not authorized.
- `404 Not Found`: resource absent or intentionally concealed because the caller lacks access.
- `409 Conflict`: duplicate operation, stale state, invalid state transition, or concurrency conflict.
- `422 Unprocessable Entity`: valid JSON but field-level validation failure.
- `429 Too Many Requests`: rate limit exceeded.
- `5xx`: unexpected server or dependency failure; return a request ID, not internal implementation details.

## 4. Identity, organization, and workspace membership

Authentication is a separate concern from organization authorization. If a managed identity provider is selected, password creation, login, reset, and MFA may be handled by that provider; CampusOps APIs still validate the resulting authenticated identity and enforce all workspace permissions server-side.

### 4.1 Identity/account endpoints (provider-neutral conceptual contract)

| Method | Path | Purpose | Notes |
|---|---|---|---|
| `GET` | `/me` | Return the authenticated user's profile and account ID | Never returns password or secrets. |
| `PATCH` | `/me/profile` | Update permitted profile fields | Email change may require re-verification. |
| `POST` | `/auth/password-reset-requests` | Request password recovery | May be implemented by provider, not CampusOps. Response must not reveal whether an email exists. |

Signup/login endpoints are intentionally provider-neutral until identity provider selection is approved.

### 4.2 Organization endpoints

| Method | Path | Purpose | Access / rules |
|---|---|---|---|
| `POST` | `/organizations` | Create an organization workspace with college name and club name | Authenticated, email-verified user; workspace enters the configured verification state. |
| `GET` | `/organizations/{organizationId}` | Read workspace profile | Active member with suitable scope. |
| `PATCH` | `/organizations/{organizationId}` | Edit college/club/workspace details | Organization administrator or explicit permission grant. |
| `POST` | `/organizations/{organizationId}/verification-submissions` | Submit evidence/details for organization verification | Verification method and evidence types remain open. |
| `GET` | `/organizations/{organizationId}/verification-status` | Read verification state | Authorized workspace administrator; public disclosure is not implied. |
| `GET` | `/organizations/{organizationId}/members` | List organization members | Active workspace members may see the approved basic directory fields. Contact-field visibility remains configurable and undecided. |
| `GET` | `/organizations/{organizationId}/office-bearers` | Read office-bearer and faculty-coordinator tenure records | Authorized member; return only approved directory fields. A roster record alone does not create a login or grant permissions. |
| `POST` | `/organizations/{organizationId}/office-bearer-tenures` | Add a current office-bearer/faculty-coordinator record | Explicitly authorized administrator; may link to an existing organization member or remain a directory-only record. |
| `PATCH` | `/organizations/{organizationId}/office-bearer-tenures/{tenureId}` | Edit a tenure record or end the tenure | Explicitly authorized administrator; preserve historical tenure and audit history. Ending a tenure does not silently revoke/modify account roles; membership/role changes require a separate operation. |
| `POST` | `/organizations/{organizationId}/administrator-transfers` | Start workspace administrator transfer | Requires current administrator authorization, a recipient, and a transfer/acceptance flow; final rules remain pending. |

### 4.3 Memberships, invitations, and scoped role assignments

| Method | Path | Purpose | Access / rules |
|---|---|---|---|
| `GET` | `/organizations/{organizationId}/memberships` | List active and pending memberships | Authorized workspace role; privacy filtering applies. |
| `POST` | `/organizations/{organizationId}/invitations` | Invite a person to the organization or a specific allowed scope | Caller must have permission to grant the requested role and scope. |
| `GET` | `/invitations/{invitationToken}/preview` | Show the invitee what workspace, scope, role, and inviter the invitation refers to | Token must be valid; expose only what is needed to accept/reject. Tokens must be high-entropy and single-use. Store only a token hash server-side, redact tokens from logs/analytics, prevent caching of previews, and avoid exposing token values in error text or referrer destinations. |
| `POST` | `/invitations/accept` | Accept invitation and associate the user's individual account with the granted membership/role | Invitation email and authenticated identity must match under the approved policy. Invitee cannot elevate the granted role. |
| `POST` | `/invitations/{invitationId}/resend` | Resend invitation | Inviter or authorized administrator; rate-limited and token-safe. |
| `POST` | `/invitations/{invitationId}/revoke` | Revoke pending invitation | Authorized inviter/admin. |
| `DELETE` | `/organizations/{organizationId}/memberships/{membershipId}` | Remove a member from this organization | Revokes organization-scoped access but does not delete the personal account or unrelated memberships. Preserve history. |
| `GET` | `/organizations/{organizationId}/role-assignments` | List scoped role assignments | Authorized administrator; sensitive role changes are audited. |
| `POST` | `/organizations/{organizationId}/role-assignments` | Create a scoped role assignment | Grantor can only grant allowed permissions and scopes. |
| `PATCH` | `/organizations/{organizationId}/role-assignments/{assignmentId}` | Change a role/scope | Validate authority boundaries; log actor, before/after values, reason where required. |
| `DELETE` | `/organizations/{organizationId}/role-assignments/{assignmentId}` | Remove a role assignment | Removes the specified assignment only; does not delete user or unrelated assignments. |

### 4.4 Role and scope rules

Roles are names/permission bundles, not sufficient security checks by themselves. Each role assignment has an explicit scope (organization, program, event, department, or task where applicable). Parent-scope access must not automatically grant access to every child event's private tasks, attendance, registration details, evidence, or audit history.

Recommended authorization tuple for every protected operation:

`authenticated user + active membership + explicit permission + matching resource scope + valid resource state`.

## 5. Event workspaces

### 5.1 Create/list/edit standalone events

| Method | Path | Purpose | Access / rules |
|---|---|---|---|
| `POST` | `/events` | Create a standalone event | Requires workspace membership and event-creation permission. `mode` must be `standalone`; venue may be omitted initially. |
| `GET` | `/events` | List events visible to caller | Results filtered to authorized workspaces/scopes. Supports type/status/date filters. |
| `GET` | `/events/{eventId}` | Read event details | Requires permission for that event scope. |
| `PATCH` | `/events/{eventId}` | Edit name, date, day, time zone, venue, or event details | Validate state and dates; preserve relevant change history. Name and venue can be changed after creation within policy. |
| `GET` | `/events/{eventId}/overview` | Read event operational summary | Returns only fields caller may access: task summary, assignments, registration/check-in counts, and closure status as granted. |

Illustrative create request:

```json
{
  "mode": "standalone",
  "name": "Product Workshop",
  "event_date": "2027-03-12",
  "timezone": "Asia/Kolkata",
  "venue": null
}
```

The event date/day should be derived from the chosen event date and time zone where possible rather than separately storing a manually editable weekday value that can become inconsistent.

### 5.2 Standalone departments and department leads

| Method | Path | Purpose | Access / rules |
|---|---|---|---|
| `GET` | `/events/{eventId}/departments` | List departments for standalone event | Event-scoped access. |
| `POST` | `/events/{eventId}/departments` | Add department | Authorized event organizer; department name must be unique within the event or duplicates explicitly handled. |
| `PATCH` | `/events/{eventId}/departments/{departmentId}` | Edit department details | Authorized event organizer; changes audited where materially affect assignments. |
| `POST` | `/events/{eventId}/departments/{departmentId}/lead-invitations` | Invite a department lead | Invitation is scoped to this event/department; acceptance creates the configured role assignment. |
| `GET` | `/events/{eventId}/departments/{departmentId}/members` | List members of department | Authorized event/department member; contacts filtered by privacy rules. |
| `POST` | `/events/{eventId}/departments/{departmentId}/department-assignments` | Assign/add a member to department | Caller must have member-assignment permission; new member may need to accept an invitation if not already a workspace member. |
| `DELETE` | `/events/{eventId}/departments/{departmentId}/department-assignments/{assignmentId}` | Remove department assignment | Removes the department assignment without deleting the account, organization membership, or unrelated event assignments. |

### 5.3 Multi-event programs

| Method | Path | Purpose | Access / rules |
|---|---|---|---|
| `POST` | `/programs` | Create a multi-event program | Requires workspace membership and program-creation permission. |
| `GET` | `/programs` | List programs visible to caller | Filtered by workspace and scope. |
| `GET` | `/programs/{programId}` | Read program details and summary | Program-scoped access. |
| `PATCH` | `/programs/{programId}` | Edit program name, date range, and details | Authorized program/workspace role. |
| `POST` | `/programs/{programId}/events` | Create a child event in the program | Child event remains separately addressable and has its own registration, task and attendance records. |
| `GET` | `/programs/{programId}/events` | List child events | Program member access; filter private fields by event scope. |
| `GET` | `/programs/{programId}/departments` | List shared program departments | Shared department structure does not grant implicit access to each child's private records. |
| `POST` | `/programs/{programId}/departments` | Create shared program department | Authorized program administrator. |
| `PATCH` | `/programs/{programId}/departments/{departmentId}` | Edit shared department | Changes to shared structure must be evaluated against existing event assignments. |
| `POST` | `/programs/{programId}/events/{eventId}/lead-invitations` | Invite a lead for a specific child event | Role assignment is event-scoped; no department lead is created by default in this workflow. |
| `POST` | `/programs/{programId}/events/{eventId}/department-assignments` | Assign a member/coordinator to a shared department for a specific event/work scope | Explicitly records the event(s) and department(s) the member is assigned to; shared department alone grants no event-task/attendee access. |
| `GET` | `/programs/{programId}/members` | Program workspace roster view across all child events | Any active member of the program workspace may discover basic member identity, role, department and assigned-event information across child events, consistent with the founder workflow; private contact details and protected operational records remain separately permission-scoped. |
| `GET` | `/programs/{programId}/overview` | Consolidated program status | Summaries aggregate without merging individual event identities, participant records, or attendance. |

The user specified separate setup experiences. That is a UX requirement; it does not require duplicated backend resource types. Shared APIs can support different setup sequences while preserving the structural distinction between standalone events and a program with child events.

## 6. Tasks, deadlines, evidence, reviews, and notifications

### 6.1 Tasks and progress

| Method | Path | Purpose | Access / rules |
|---|---|---|---|
| `GET` | `/events/{eventId}/tasks` | List authorized event tasks | Filters include owner, department, state, deadline window, and overdue. Access remains event/department scoped. |
| `POST` | `/events/{eventId}/tasks` | Create task | Requires a title, a specific due date or due timestamp, applicable event-timezone context, and valid owner/scope. A task cannot be created as active work without a deadline; any draft exception must be explicit. Due-date/time changes must use the dedicated auditable deadline-change flow. |
| `GET` | `/tasks/{taskId}` | Read task | Requires task's event/department scope. |
| `PATCH` | `/tasks/{taskId}` | Edit permitted task fields other than direct deadline or assignee mutations | Check permission and resource state. Direct changes to `due_date`/`due_at` or assignee relationships through this endpoint are rejected; use the dedicated audited operations below. |
| `POST` | `/tasks/{taskId}/assignees` | Add or replace a task assignee according to the request operation | Authorized task manager; validate active organization membership and event/department scope; retain assignment history. |
| `DELETE` | `/tasks/{taskId}/assignees/{assignmentId}` | Remove an assignee | Authorized task manager; prevent an active task from being left without a responsible owner unless it is deliberately unassigned/draft under an explicit policy. |
| `POST` | `/tasks/{taskId}/progress-updates` | Add progress update/comment | Authorized task member; text validation and audit history apply. |
| `POST` | `/tasks/{taskId}/deadline-change-requests` | Request new deadline | Assignee or permitted member; proposed deadline and reason required; request does not alter the active deadline. |
| `GET` | `/tasks/{taskId}/deadline-change-requests` | List deadline-change requests | Authorized task scope; distinguish pending, approved, and rejected requests. |
| `POST` | `/deadline-change-requests/{requestId}/decision` | Approve or reject a requested deadline change | Authorized reviewer within task scope; record actor, old/new deadline, decision, reason, timestamp and notify affected people. A direct authorized deadline-change path may exist for designated administrators, but must be separately specified and audited. |
| `GET` | `/tasks/{taskId}/history` | Read task history | Authorized task scope; return status, ownership, deadline and review changes subject to access controls. |

### 6.2 Evidence submission and review

| Method | Path | Purpose | Access / rules |
|---|---|---|---|
| `POST` | `/tasks/{taskId}/evidence-submissions` | Submit file evidence or a link for review | Task assignee or permitted submitter; stores immutable submission/version and moves proof-required task to `submitted_for_review`. |
| `GET` | `/tasks/{taskId}/evidence-submissions` | List evidence versions | Authorized task scope; private files are not exposed through public URLs. |
| `GET` | `/evidence-submissions/{submissionId}` | Read submission metadata | Authorization checked against parent task and scope. |
| `POST` | `/evidence-submissions/{submissionId}/reviews` | Approve or reject submission | Reviewer must be authorized for the task's scope and must not be the submitter. Rejection requires a note. |
| `GET` | `/tasks/{taskId}/reviews` | Read review history | Authorized task scope. |

A file upload may need a separate upload-session endpoint, such as `POST /file-uploads`, followed by a completion call. Exact presigned URL behavior depends on the file-storage provider and remains unresolved.

### 6.3 Proposed task states and transitions

Proposed API state values (canonical machine-readable values):

- `draft`
- `assigned`
- `in_progress`
- `blocked`
- `submitted_for_review` (UI label may display “In review” or “Awaiting review”)
- `changes_requested`
- `completed`
- `cancelled`

The requirements document and logical data model should use these canonical values or maintain an explicit, one-to-one mapping. Avoid treating “In review,” “Awaiting review,” and `submitted_for_review` as three separate states.

Rules:

1. A task with a proof-required policy can enter `completed` only after a reviewer approves the current evidence submission.
2. The submitter cannot review/approve their own submission, even if they also have a lead/office-bearer role.
3. Rejection requires a non-empty reason, preserves the rejected evidence/review, returns the task to `changes_requested`, and creates a notification for the submitter/assignee.
4. Resubmission creates a new immutable evidence version. A review for an older submission cannot approve a newer submission by mistake.
5. Approval and task state transition occur atomically or through a consistency-safe process to prevent a partially approved/completed task.
6. For proof-optional tasks, the completion path must be explicit in task policy. The permitted completion roles are still to be approved.
7. The exact backup-reviewer mechanism and whether lead review permission is automatic within scope remain proposed decisions, not confirmed.

### 6.4 Notifications

| Method | Path | Purpose | Access / rules |
|---|---|---|---|
| `GET` | `/notifications` | List notifications for current user | User can only access their own notifications. |
| `POST` | `/notifications/{notificationId}/read` | Mark notification read | Owner only. |
| `POST` | `/notifications/read-batch` | Mark selected notifications read | Owner only; validate IDs. |

Email/push delivery is an internal side effect of invitations, task changes, reviews, deadlines and other approved events. Client requests must not be allowed to spoof arbitrary sender identities or recipients. Delivery provider is not selected.

## 7. Registration, participants, team registration, and check-in

### 7.1 Registration configuration and submission

| Method | Path | Purpose | Access / rules |
|---|---|---|---|
| `GET` | `/events/{eventId}/registration-config` | Read registration configuration | Authorized event team. |
| `PUT` | `/events/{eventId}/registration-config` | Create/update native registration fields and settings | Authorized event organizer; published configuration changes need a policy and audit history. |
| `POST` | `/public/events/{publicEventKey}/registrations` | Submit a native public registration | Public endpoint with rate limits, validation, anti-abuse measures and minimal PII. Supports `solo` or `team` registration, but creates individual participant records for every registered person. |
| `GET` | `/events/{eventId}/registrations` | List registration records | Authorized registration staff; personal data fields minimized by role. |
| `GET` | `/events/{eventId}/participants` | Search/list individual participants | Authorized event registration/check-in scope; pagination and rate limits apply. |
| `GET` | `/participants/{participantId}` | Read participant record | Event-scoped permission and field-level privacy checks. |
| `PATCH` | `/participants/{participantId}` | Correct participant details | Authorized role; changes audited and constrained by event roster-edit policy. |
| `POST` | `/events/{eventId}/team-registrations` | Staff-side creation of a team registration when an authorized manual/walk-in workflow requires it | Use the same canonical registration service as public/native registration; must not create a second independent data path. Every team member still gets an individual participant record. Whether a separate staff endpoint is needed remains open. |
| `GET` | `/team-registrations/{teamRegistrationId}` | Read team/group registration and roster | Authorized registration staff; view must not disclose unnecessary private contact details. |

Public registration must not accept client-supplied authoritative fields such as `checked_in`, reviewer identity, internal role, or approval status. These fields are server-managed.

### 7.2 External registration imports

Proposed provider-neutral resource endpoints:

| Method | Path | Purpose | Access / rules |
|---|---|---|---|
| `GET` | `/events/{eventId}/registration-integrations` | List configured external sources | Authorized event/workspace admin. Do not expose secrets. |
| `POST` | `/events/{eventId}/registration-integrations` | Configure an external source | Provider and synchronization mode must be supported and approved. Secrets stored server-side. |
| `POST` | `/events/{eventId}/registration-import-jobs` | Start a manual import/sync | Authorized operator; idempotency and replay protection required. |
| `GET` | `/registration-import-jobs/{jobId}` | Inspect job status, summary and safe error details | Authorized operator; no raw secrets or unnecessary PII in logs. |
| `POST` | `/registration-import-jobs/{jobId}/retry` | Retry a recoverable import | Authorized operator; import must be idempotent. |

Google Forms is a candidate integration because the existing workflow uses it, but is not yet selected as the first integration. The API contract must later specify read/write direction, polling/webhook strategy if supported, provider identifiers, field mapping, stale data handling, error recovery, and the record-matching policy. Do not merge participants solely on email without an explicitly approved matching rule.

### 7.3 Individual check-in

| Method | Path | Purpose | Access / rules |
|---|---|---|---|
| `POST` | `/events/{eventId}/check-ins` | Check in one participant | Registration/check-in permission; body identifies one participant. Use an idempotency key or equivalent uniqueness constraint. |
| `GET` | `/events/{eventId}/check-ins` | List/check summary of attendance records | Authorized event team; permissions and personal data minimization apply. |
| `GET` | `/events/{eventId}/check-in-lookup` | Resolve QR/registration identifier or search query | Authorized check-in staff; return only fields needed to verify identity. Exact lookup methods remain open. |
| `POST` | `/events/{eventId}/check-ins/{checkInId}/void` | Void/correct a mistaken check-in | Authorized correction role; reason required. Preserve the original check-in and append a correction event; no physical deletion. |

Required invariants:

- A check-in is tied to a specific event and individual participant.
- A team registration or team QR may locate the group/roster but must not automatically mark all participants present.
- Each participant is verified and checked in individually.
- Duplicate and near-simultaneous attempts do not create multiple active check-ins for the same participant/event.
- Walk-in or missing-registration handling must be explicit and recorded; it must not silently bypass validation.
- Offline/degraded-network behavior remains unresolved and must be tested before a real event pilot.

## 8. Post-event documentation and closure

| Method | Path | Purpose | Access / rules |
|---|---|---|---|
| `GET` | `/events/{eventId}/closeout` | Read closure checklist and completion status | Authorized event team. |
| `PUT` | `/events/{eventId}/closeout` | Update required close-out checklist/status | Authorized close-out role; required fields and exceptions recorded. |
| `GET` | `/events/{eventId}/report` | Read event summary | Authorized report access; report separates registration count, unique participants and individual attendance. |
| `POST` | `/events/{eventId}/report/finalize` | Finalize post-event report | Authorized reviewer/lead; require configured mandatory fields or recorded exceptions. Finalization and reopening policy remains to be defined. |
| `POST` | `/events/{eventId}/supporting-evidence` | Attach event photos/documents as report evidence | Authorized uploader; private object storage, type/size limits, scanning and retention policy required. |
| `GET` | `/programs/{programId}/report` | Read program-level outcome summary | Authorized program scope; clearly distinguish event-level counts from deduplicated program-wide counts. |

The product does not include campaign planning or social media publishing. The report may record facts about what happened and attach event evidence, but must not add promotional campaign workflow. Participant-facing doubt/issue submission endpoints are intentionally absent from this contract.

## 9. Staff-only operational blockers (not participant support)

Requirements Specification v0.9 includes `CO-FR-012` for tracking operational issues. To keep this API contract consistent with that requirement, the following **staff-only** routes are proposed. They must not be exposed as public participant submission endpoints.

| Method | Path | Purpose | Access / rules |
|---|---|---|---|
| `GET` | `/events/{eventId}/operational-issues` | List internal blockers for the event | Authorized event staff within scope; response fields are minimized by role. |
| `POST` | `/events/{eventId}/operational-issues` | Record an internal blocker, such as a room or equipment problem | Authorized event staff; requires description, priority/status and an owner or explicit unassigned state. |
| `GET` | `/operational-issues/{issueId}` | Read one internal blocker | Authorization checked against parent event and actor's scoped membership. |
| `PATCH` | `/operational-issues/{issueId}` | Update owner, status, priority or resolution note | Authorized event staff; preserve actor/time history. |

The founder excluded participant-facing questions, doubts, and issue raising. Do not add public attendee issue submission, a guest support ticket portal, or attendee-initiated requests under these routes. These endpoints should remain only if the P0 internal operational-blocker requirement is retained in the final PRD.

## 10. Authorization and security invariants

Every endpoint must enforce the following server-side:

1. Authentication and active membership for the relevant organization/workspace.
2. Explicit permission on the requested action and the resource scope.
3. No implicit access from program membership to every child event's private participant data, task evidence, or check-in records.
4. No permission escalation through client-provided role names or resource IDs.
5. Invitation acceptance cannot grant privileges beyond the invitation's current valid role/scope.
6. Removed/revoked memberships cease authorizing new requests immediately, subject to defined session/token revocation behavior.
7. File evidence uses private storage and authorized access; no public permanent links for private submissions.
8. Attendee data is field-filtered by role and purpose; registration/check-in endpoints are rate-limited and audited where appropriate.
9. Sensitive mutations (role assignments, task approvals, attendance corrections, roster edits, deadline changes, administrator transfer) create audit records.
10. Mutating operations that might be retried must prevent duplicate side effects or clearly return the original result.
11. Public endpoints must not reveal whether a private organization exists, expose member directories, or leak registration data.
12. Errors and logs must not expose passwords, access tokens, invitation tokens, provider secrets, or unnecessary participant data.

## 11. Concurrency and data-integrity contract

- Use database-level uniqueness and transactions for invitations, role grants, team member/participant associations, task review transitions, and check-ins where appropriate.
- Use optimistic concurrency (for example, version or `updated_at` precondition) for sensitive updates such as task reviews, deadline edits and role changes; exact protocol is to be chosen at implementation.
- Evidence review must reference the exact submitted version. A stale review must not approve a newer submission.
- A successful task review and corresponding state transition must be atomic or consistency-safe.
- Registration imports should store external source IDs and be replayable without creating duplicate participant records.
- Program reports must make counting rules explicit to avoid accidentally double-counting repeated or multi-event attendees.
- Event date and timezone must be validated; date-only values must not be accidentally shifted by UTC conversion.
- Check-in correction must preserve the original action and correction reason.

## 12. Proposed domain resource map

This is the logical vocabulary for the API, not the finalized physical database schema:

- `User`
- `Organization`
- `OrganizationVerification`
- `OfficeBearerTenure` / `FacultyCoordinatorRecord`
- `Membership`
- `Invitation`
- `RoleAssignment`
- `Program`
- `Event`
- `Department` (event-scoped for standalone; shared by program in multi-event workflow)
- `DepartmentMembership` / event-specific assignment
- `Task`
- `TaskProgressUpdate`
- `TaskDeadlineChange`
- `EvidenceSubmission`
- `TaskReview`
- `Notification`
- `RegistrationConfig`
- `RegistrationRecord` or `TeamRegistration`
- `Participant`
- `ExternalRegistrationSource`
- `RegistrationImportJob`
- `CheckIn`
- `CloseoutChecklist`
- `EventReport`
- `SupportingEvidence`
- `AuditEvent`

Exact table boundaries and naming will be decided with the physical schema and approved requirements.

## 13. Acceptance-test categories required before implementation readiness

1. **Account and invitation:** new individual account, existing user invitation, expired/revoked invitation, email mismatch, duplicate invitation, role scope not elevated.
2. **Organization boundaries:** member of Organization A attempts to read or mutate Organization B's data.
3. **Standalone permissions:** department lead acts within their department and is denied access to another department's restricted task/evidence.
4. **Multi-event boundaries:** shared department membership does not authorize access to every child event; event lead can manage assigned event and is denied unrelated event actions.
5. **Task approval:** self-review denied; authorized review succeeds; rejection note required; stale-version review denied; notification and history preserved.
6. **Deadline changes:** assignee request does not silently alter deadline; authorized changes preserve old/new values, reason, actor and notification; timezone interpreted consistently.
7. **Registration:** solo and team registration create individual participants; external import replay does not duplicate people; conflicting records are surfaced rather than silently merged.
8. **Check-in:** team QR does not bulk-check-in; each participant gets their own check-in; concurrent duplicate scans do not produce duplicates; correction is auditable.
9. **Close-out:** registrations and actual attendance remain distinguishable; mandatory documentation is checked; program report aggregation follows explicit counting rules.
10. **Privacy and files:** private email, participant contact data, evidence files and audit records are not returned to unauthorized roles; public API rate limiting and safe errors are tested.

## 14. Decisions still open

### Required before treating the API contract as implementation-ready

- Whether leads automatically receive review permission within their assigned scope (proposed default: yes, except self-review) and who is backup reviewer.
- Exact role/permission bundles and inheritance rules for office bearers, core members, leads, coordinators, volunteers, and faculty coordinators. A tenure/roster record alone does not grant account access; an active membership and scoped role assignment are separate.
- Which roster contact fields are visible to all workspace members.
- Participant fields required for solo and team registration; roster-edit cutoff policy.
- Check-in lookup methods, correction authority, and walk-in handling.
- Proof-required vs proof-optional task rules and who may complete proof-optional tasks.
- Deadline update authority and how date-only deadlines are presented/processed.
- The first external registration integration and whether it is read-only import or bidirectional sync.
- Final file upload protocol (upload initiation/completion, size/type controls, scanning status, private download authorization and retention).
- Offline/degraded-network check-in policy.

### Required before selecting implementation providers

- Identity/authentication provider.
- Email/notification provider.
- Evidence/file storage provider and allowed formats/sizes, scan requirements and retention.
- Hosting region, budget, backups, restore targets and monitoring.
- External integration auth model, provider limits and sync frequency.

### Required before a real-world pilot

- Authorization tests across every relevant scope.
- Backup/restore verification.
- Security and privacy review for real participant records.
- Failed provider operation and import-replay recovery tests.
- Check-in contingency procedure and staff instructions.
- Explicit personal-data retention, export, correction and deletion policies.

## 15. Review decision

This API contract is a draft for product and architecture review. It does not approve implementation or freeze providers, route names, schemas, or status enums. Once the Gate A decisions are confirmed or expressly kept provisional, reconcile this contract with the final requirements specification, role/permission matrix, logical data model, architecture decision record, and decision log. Any mismatch must be resolved before implementation begins.

## 16. Change log

| Version | Change |
|---|---|
| 0.1 | Initial provider-neutral REST-style API contract covering identity/workspaces, invitations, standalone and multi-event workflows, tasks/evidence/reviews, registrations/participants/check-ins, close-out, security invariants, and remaining decisions. |
| 0.2 | Applied a traceability review: clarified roster-versus-access identity, renamed department assignment routes to avoid membership ambiguity, made task assignee/deadline mutations explicit, aligned review-state vocabulary, clarified program-wide member-directory visibility, defined internal staff-only operational-blocker routes consistent with CO-FR-012, and specified a canonical registration model and auditable check-in voiding. Remaining policy/provider decisions stay open. |
