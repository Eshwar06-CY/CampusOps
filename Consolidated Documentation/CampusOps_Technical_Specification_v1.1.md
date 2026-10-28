# CampusOps — Technical Specification

**Version:** 1.1  
**Status:** Consolidated proposal; FPC-01–FPC-05 are founder-approved at policy level; implementation and provider feasibility remain open  
**Companion:** `CampusOps_PRD_v1.1.md`  
**Working mode:** Documentation only; no code or infrastructure created by this specification.

## 1. Purpose and status conventions

This document translates the approved product policy and consolidated PRD into an initial technical design. It is not a statement that the design has been implemented, tested, or approved for production.

Status labels:
- **Confirmed product rule:** explicitly defined by the founder and/or approved in FA-001–FA-009.
- **Proposed technical approach:** recommended, not a provider or implementation commitment.
- **Open gate:** requires a choice or feasibility test before the affected feature is implemented or real data is used.

## 2. Architectural recommendation

### 2.1 Proposed architecture

Use a modular monolith for the initial application. Keep domain modules logically separated while deploying a single backend application. Do not add microservices, message brokers, Redis or Kubernetes without demonstrated need.

```text
Browser
  ├─ Public landing / authentication entry
  └─ Authenticated application (role- and scope-aware views)
         │ HTTPS / JSON API
         ▼
Backend application (modular monolith; proposed FastAPI)
  ├─ Identity adapter and organization membership
  ├─ Organizations and directory/tenure records
  ├─ Roles, permissions, invitations and audit
  ├─ Events, programs, departments and assignments
  ├─ Tasks, deadlines, evidence and reviews
  ├─ Registration, participants and check-in
  ├─ Event-day status / internal blockers
  ├─ Post-event reports and closure
  └─ Notifications and external integration adapters
         │
         ├─ PostgreSQL (relational records and constraints)
         ├─ Private evidence object storage (provider open)
         ├─ Transactional email/notification provider (open)
         └─ Selected registration source adapter (provider and sync model open)
```

### 2.2 Proposed stack, not yet selected

| Layer | Candidate | Status / conditions |
|---|---|---|
| Frontend | React + TypeScript + Vite | Proposed; inspect repository and actual environment before committing |
| UI styling | Tailwind CSS or equivalent component/system choice | Open; prioritize accessible, consistent forms and tables |
| Backend | Python + FastAPI + Pydantic | Proposed |
| Database | PostgreSQL | Strong proposal due to relational integrity, transactions and constraints; provider/hosting open |
| ORM/migrations | SQLAlchemy + Alembic | Proposed; validate in a small technical check |
| Authentication | Supabase Auth preferred candidate behind an identity adapter | Founder-approved candidate; final provider lock follows the documented feasibility/security review of account lifecycle, MFA, recovery, token validation, cost and region |
| Evidence storage | Private object storage | Vendor, size/type limits, scanning and retention open |
| Email/notifications | Transactional provider adapter | Provider/channel and retry policy open |
| Testing | Pytest; Vitest/React Testing Library; Playwright for critical journeys | Proposed test tooling, not installed or executed |

### 2.3 Architecture principles

1. Organization tenancy is explicit in every organization-owned resource.
2. Authorization is enforced on the server, with database constraints/defense in depth where possible.
3. Keep standalone and multi-event UX distinct while sharing domain services and event concepts.
4. Treat file uploads and external registration data as untrusted inputs.
5. Critical operations—task approvals, roster changes, check-in, role updates and closure—must be transactional/auditable.
6. Provider-specific behavior is isolated behind adapters where practical.
7. Do not promise offline mode, performance, uptime or scale until measured.

## 3. Domain and logical data model

The detailed source model is in `CampusOps_Data_Model_and_Relationship_Map_v0.1.md`. The consolidated logical model is:

### 3.1 Identity and organization

- **User:** one personal login identity; a person may belong to more than one organization.
- **Organization:** college club/organization workspace, with verification state and organization details.
- **Membership:** connects a User to an Organization and provides status (invited/active/suspended/removed) and membership history.
- **OrganizationPersonRecord:** editable office-bearer and faculty-coordinator directory/tenure record. Not itself an authentication identity and never automatically grants access.
- **RoleDefinition / Permission / RolePermission:** role labels map to controlled permission sets. Custom role names may be supported but cannot invent arbitrary permissions without an explicit grant path.
- **RoleAssignment:** binds a member or assignment to an organization/program/event/department/task scope. Store who granted/changed it and when.
- **Invitation:** intended email, organization, role and scope; token hash/reference, expiry, status, revocation and acceptance audit. Seven-day expiry is approved; provider delivery remains open.
- **AuditEvent:** actor, action, resource/scope, timestamp and appropriate changed fields; do not store secrets or raw tokens.

### 3.2 Event structure

- **Program:** a multi-event parent with common departments, shared summary, and program-specific assignments.
- **Event:** either a standalone event or a child of a Program; has dates/time zone, optional venue, state, schedule, tasks, registration/check-in and close-out records.
- **Department:** event-scoped for standalone events; program-scoped and shared across child events for a multi-event program.
- **EventLeadAssignment:** identifies event lead(s) and exact child-event scope.
- **DepartmentMembership:** connects a person to a department with scope; standalone lead permissions may include departmental membership/task management.
- **TaskAssignee:** relates task to individual(s) with explicit responsibilities; do not infer an event membership from a mere directory entry.

Avoid a single fixed `lead_user_id` field where multiple equivalent leads or assignments across scopes may exist. Use scoped assignment records.

### 3.3 Tasks, evidence and reviews

- **Task:** event scope, optional department scope, title/description, owner requirement, status, priority, due timestamp/time zone, dependencies, proof-required rule and change history.
- **TaskAssignee:** one or more authorized individual assignments where product rules allow it.
- **TaskDependency:** directed relationship with cycle prevention.
- **TaskStatusHistory:** old/new status, actor, timestamp and reason where appropriate.
- **EvidenceSubmission:** a versioned submission linked to a task and submitter, with file/link references, submission time and state.
- **EvidenceArtifact:** private file metadata or an external link; metadata and access authorization kept separate from public URLs.
- **TaskReview:** reviewer, decision, note, timestamp and evidence version. Prevent reviewer==submitter for a submission by default.

Recommended state model:

`Not Started → In Progress → Submitted for Review → Completed`

If rejected: `Submitted for Review → Changes Requested → In Progress/Submitted for Review`.

A proof-required task cannot be set to `Completed` by a generic task update. Approval must be a separate authorized operation. State transitions are validated server-side and recorded.

### 3.4 Registration and attendance

- **RegistrationForm:** event-scoped native form configuration and version/state.
- **Registration:** registration/group header with source (`native` or named external adapter), event, stable source record ID where available, timestamps and import history.
- **Participant:** individual person record with minimized personal data and organization/event visibility rules.
- **RegistrationParticipant:** join record between a registration/group and each individual participant, with participant-level status. Solo registrations use one participant; group registrations use multiple.
- **CheckIn:** one participant per event/station/time and status, with idempotency key/unique event-participant rule as applicable, actor, correction/void reason and audit history.
- **ExternalSourceRecord / SyncRun / SyncConflict:** record source identifiers, last successful sync, status, failures and conflicts. Exact physical tables may differ if equivalent traceability is preserved.

Approved rules:
- One check-in record per individual participant per event unless a supported correction path changes its state.
- Duplicate attempts return a clear already-checked-in response and do not inflate attendance.
- Concurrent check-ins must be atomic/idempotent.
- Never merge participants solely because emails match. Ambiguous matches go to authorized review.
- Roster changes are audited; a program/event may configure a cutoff. If configured, post-cutoff changes require authorized review.
- Native and external records must be normalized through one validation model, but the external connector and sync direction are not selected.

### 3.5 Post-event and operations

- **PostEventReport:** event details, duration/venue, registrations, attended counts derived from check-in, notes and closure state.
- **ReportEvidence:** link or private file reference attached to report sections.
- **InternalOperationalIssue:** staff-only blocker with event/task link, owner, status, priority if required, resolution notes and history. No participant-facing ticket resource.
- **Notification:** intended user, type, related resource, delivery state and safe metadata. App state remains authoritative if email delivery fails.
- **ClosureChecklistItem:** mandatory/optional report/evidence deliverables and exception information.

## 4. Authorization model

### 4.1 Principles

- Deny by default; each protected operation checks the authenticated user, active organization membership, permission and target resource scope.
- Role names are not the source of truth for access; role-to-permission grants and scope are.
- Membership, directory/tenure records and role assignments are distinct.
- Role assignments should not implicitly cascade into private participant/evidence records without a defined rule.
- Revoke effective access promptly when a membership or invitation is revoked. Preserve audit history and authored records.
- Never trust client-provided role, organization ID, reviewer ID, participant ID or event scope without server authorization.

### 4.2 Approved role policy defaults

- **Proof review:** an assigned lead or authorized core member reviews within scope; no self-approval; a backup reviewer or documented escalation exists; rejection requires a reason and notification.
- **Scopes:** organization, program, event, department and task where appropriate; no implicit access to unrelated child-event private data.
- **Directory:** all active workspace/program members can see basic name, role, department and event assignments. Email/phone require authorized operational need; participant records do not appear in the general directory.
- **Deadlines:** active task has owner and specific deadline; event time zone is used; assignee requests changes with reason; authorized lead/office bearer decides. Direct changes by an explicitly authorized admin record old/new values, actor/time/reason and notify affected parties.
- **Check-in:** QR/registration ID with search fallback; individual check-in; duplicates blocked/idempotent; corrections require a reason and audit; walk-ins follow event policy and required validation.
- **Connectivity:** online-first with documented manual fallback; do not claim offline capability until tested.
- **External registrations:** stable source IDs and idempotent ingestion; no auto-merge based solely on email; ambiguous matches reviewed; team and individual records are separate; roster changes audited; configured cutoff may require review after the cutoff.
- **Operational blockers:** internal staff-only records allowed; participant-facing issue/query portals excluded.
- **Invitations:** single-use, bound to target email/workspace/role/scope, revocable, expires after seven days; resend safely reissues/refreshes; failed delivery does not create membership.

### 4.3 Still-open account/security decisions

The nine FA decisions above are approved. These distinct account/technical decisions are still open:
- College/club verification evidence and who reviews it.
- Authentication provider, account recovery details and whether MFA is mandatory for administrators before production.
- Exact Primary Workspace Administrator transfer/recovery procedure and acceptable evidence in an emergency.
- Email provider and notification retries.
- Physical role/permission schema and detailed permission bundles.
- Session duration, logout/revocation and provider-specific security configuration.

## 5. API contract principles

The route-level draft is `CampusOps_API_Contract_Draft_v0.2.md`. Before implementation, reconcile it with the approved decisions and finalize naming, payload schemas and OpenAPI details. The resource boundaries should include:

- Auth adapter / personal accounts (provider-managed; no hand-rolled passwords unless a reviewed reason exists).
- Organizations, verification state, directory records and memberships.
- Invitations, acceptance/revocation/resend, scoped roles and permissions.
- Programs, events, departments, event leads and memberships.
- Tasks, assignees, deadline-change requests, status updates, evidence submissions and task reviews.
- Native registration forms, registrations, participant records, team join records, external sync runs/conflicts, check-ins and audited corrections.
- Internal operational blockers, post-event reports, report evidence, closure checklist and program summaries.

Use explicit operations for high-impact mutations, not only generic PATCH calls: approve/reject evidence, request/change a deadline, reassign a member, accept/revoke an invitation, record/correct check-in, resolve a sync conflict, transfer administration and close an event. Validate state transitions server-side. Use consistent errors and correlation IDs; do not expose sensitive details in errors/logs.

### 5.1 Transaction and idempotency needs

- Check-in: atomic per-participant-per-event behavior; concurrent attempts must not produce duplicate attendance.
- External import: stable source ID/idempotency key, safe retries and visible sync conflicts.
- Invitation acceptance: single-use token and unique membership constraint; retrying the same accepted invitation must not create duplicates.
- Evidence review: review is bound to a specific evidence version; an older approval must not approve a newer unreviewed submission.
- Task/deadline changes: optimistic concurrency or equivalent conflict detection for simultaneous edits; audit successful sensitive mutations.

## 6. Evidence and file storage

Proposed approach: private object storage with database metadata. Provider is not selected.

Requirements:
- Authorize upload initiation, completion and download separately.
- Validate file size, allowed MIME/extensions and actual file signature where feasible; protect against malicious uploads and unsafe links.
- Never expose permanent public URLs to internal evidence by default; use short-lived authorized access where appropriate.
- Record uploader, owner scope, submission version and timestamps.
- Decide whether external links are accepted, how reviewers access them, and whether access permissions are validated.
- Define retention, deletion and backup behavior before real photos/participant records are used.
- Do not log raw invitation tokens, authentication secrets, private link tokens or unnecessary attendee data.

**Open gate:** allowed file types/size, scanning, photo consent and retention period, private-storage vendor, object access model and orphaned upload cleanup.

## 7. External registration integration

Native registration and selected external integration are product requirements. Exact provider, direction and timing are not approved.

Recommended technical shape:
- Define a provider adapter that maps imported records into the same internal registration/participant validation path as native registration.
- Persist source/provider identifier, source form/event identifier, import timestamp, sync status and external update metadata where available.
- Idempotently process repeated pulls/retries.
- Keep raw external payload access controlled and avoid storing unnecessary fields.
- Surface invalid data, missing fields and ambiguous matches to an authorized reconciliation workflow.
- Do not silently overwrite native changes with external data without an explicit field ownership/source-of-truth policy.
- Start with one provider and limited supported operations; do not promise universal compatibility.

Google Forms is a candidate only. Verify permissions, API support, quotas, owner access and expected update cadence during a technical feasibility step. Do not call an integration implemented until tested using a controlled form and synthetic records.

## 8. Reliability, connectivity and operations

Approved initial stance: online-first with documented manual fallback. A full offline check-in product is not promised.

Before a pilot:
- Test with representative venue latency, temporary network failure and recovery.
- Communicate whether a check-in was saved, is pending, or failed. Never present an unconfirmed operation as successfully synchronized.
- Write a staff manual fallback and later reconciliation procedure.
- If future evidence justifies offline mode, separately design device storage, local authentication/authorization, conflict rules, sync/replay, duplicate prevention and lost-device risk.
- Define deployment environments, secrets handling, backups, restoration, monitoring and error handling before real data is used.

## 9. Testing strategy

Proposed tool choices: Pytest for backend, frontend component tests with an appropriate React testing stack, and Playwright for critical end-to-end flows. These tools are not installed or run by this specification.

Minimum test groups:
1. Unit/domain tests for task state transitions, deadline rule, permission evaluation and attendance calculations.
2. API integration tests for every protected endpoint and organization/event isolation.
3. Concurrency/idempotency tests for check-in, invitation acceptance, import replay and evidence review.
4. End-to-end standalone event lifecycle.
5. End-to-end multi-event program lifecycle and cross-event scoping.
6. Native registration, solo/team participant record creation, check-in and close-out.
7. External import, malformed input, ambiguous match and provider failure once a provider is selected.
8. Accessibility, responsive UI, empty/loading/error states and recovery flows.
9. Security tests for privilege escalation, direct-API bypass, unauthorized evidence downloads, token reuse and account recovery.
10. Backup/restore and degraded connectivity checks before a pilot.

## 10. Security and privacy baseline

- Personal data minimization and defined purpose for each attendee/staff field.
- Organization creation starts in `pending_verification`; the verified-email creator is the Primary Workspace Administrator, but privileged workspace operations remain limited until platform-admin verification passes. Organization verification evidence is an official institution/club page or domain, or faculty-coordinator confirmation when public evidence is insufficient; collect only necessary evidence and provide reasons/resubmission for rejection.
- Require MFA for CampusOps platform operators. Workspace primary administrators must enrol MFA before real participant data is used in a pilot.
- Ordinary account recovery uses provider-managed verified-email recovery. Sensitive workspace recovery requires documented review using independent organization evidence, notice to established contacts, session revocation, and invalidation of outstanding invitations/reset links.
- Individual account identity; no shared club login.
- Server-enforced least privilege and organization/event isolation.
- Safe invitation/reset token storage and expiry; rate limiting and non-enumerating recovery responses.
- Audit important role, approval, deadline, membership, check-in, synchronization and closure actions.
- Do not include secrets or unnecessary personal data in logs.
- Define account deletion/deactivation, organization membership removal, participant record retention/export/correction/deletion, and evidence lifecycle.
- Keep administrator recovery and verification as distinct, reviewed processes; account existence or knowledge of a club name must not be enough for takeover.

## 11. Technical decisions still open

The policy decisions FPC-01–FPC-05 are approved. The items below describe remaining technical or operational closure, not a reopening of those approved policies.

| Decision | Current state | Gate |
|---|---|---|
| Authentication provider | Supabase Auth is the preferred candidate, approved for feasibility/security evaluation; not yet locked for production | Verify account lifecycle, invitation acceptance, email verification, TOTP MFA, recovery, FastAPI-side token validation, pricing, portability and data region |
| Database/hosting provider | PostgreSQL proposed; hosting/region open | Check cost, environment separation, backup/restore and latency needs |
| ORM/migrations | SQLAlchemy/Alembic proposed | Validate developer workflow and constraints in a small technical check |
| File storage | Private object storage proposed | Evaluate access control, retention, upload validation, cost and region |
| Email provider | Transactional adapter proposed | Test invite delivery, bounce/failure, resend, security and cost |
| External registration provider | Google Forms candidate | Prove access, field mapping, stable IDs, sync cadence and recovery |
| Sync direction | Not decided | Prefer limited one-way import for first connector unless need evidence supports more |
| MFA policy | Approved policy: MFA required for platform operators; workspace primary administrators must enrol before real participant data is used in a pilot | Implement and test enforcement, recovery, session revocation and privileged-action safeguards before pilot |
| Organization verification | Policy approved: creator email verification plus platform-admin review of official institution/club evidence or faculty-coordinator confirmation when needed; reasoned rejection/resubmission | Implement verification queue, evidence minimization, status transitions and review audit. Renewal/update triggers remain to be specified if needed |
| Admin recovery | Policy approved: independent organization evidence, notice to established contacts, session revocation, invalidate outstanding invite/reset links | Define the operational reviewer/queue, evidence retention and exact exceptional recovery runbook before real-data pilot |
| Offline check-in | Not promised; manual fallback approved | Only add full offline after feasibility and reconciliation test |
| Performance/reliability thresholds | Not set | Define realistic volume and targets before production pilot |

## 12. Implementation readiness gate

Do not treat this technical spec as approved for production or start implementation solely because it exists. Before development authorization:

1. Reconcile PRD, approved decisions, role matrix, data model and API contract; no conflicting states or scope rules remain.
2. Close or explicitly defer every open gate listed above.
3. Select the first release slice and define acceptance tests for it.
4. Inspect the actual development repository/environment before selecting versions or installing packages.
5. Estimate effort and costs with current provider information; define environment and backup/restore plan.
6. Have the founder explicitly authorize implementation.

## 13. Version history

| Version | Change |
|---|---|
| 1.0 | Consolidates architectural proposal, logical model, permission defaults, API principles, registration/check-in integrity, task proof workflow, security and testing. Incorporates founder approval of FA-001–FA-009. |
| 1.1 | Incorporates founder approval of FPC-01–FPC-05. Records Supabase Auth as the preferred candidate pending feasibility/security evaluation; specifies approved organization-verification, initial-admin, attendee-information, MFA and recovery policies. Other provider selections, schema/API closure and implementation remain open. |
