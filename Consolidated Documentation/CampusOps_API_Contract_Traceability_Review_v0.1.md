# CampusOps — API Contract Traceability Review

**Version:** 0.1  
**Date:** 2026-10-28  
**Status:** Review findings documented; API contract remains a draft and is not implementation authorization.  
**Reviewed against:** `CampusOps_API_Contract_Draft_v0.1.md`, `CampusOps_Requirements_Specification_v0.9.md`, `CampusOps_Data_Model_and_Relationship_Map_v0.1.md`, `CampusOps_Role_and_Permission_Matrix_v0.1.md`, `CampusOps_Foundational_Workflow_Reconciliation_v0.1.md`, and `CampusOps_Decision_Log_v0.8.md`.

## 1. Executive result

The API contract covers most major capability families in the requirements: organization/workspace accounts, invitations, standalone events, programs and child events, task/evidence review, registration, individual check-in, close-out, permissions and auditing. It is **not yet ready to be treated as a frozen API contract** because some critical workflow rules are represented inconsistently or lack a complete endpoint path.

A revised draft, `CampusOps_API_Contract_Draft_v0.2.md`, applies the corrections that can be made without inventing provider choices or silently approving unresolved policy decisions.

## 2. Traceability summary

| Requirements/workflow | API coverage | Data-model coverage | Review result |
|---|---|---|---|
| Personal accounts and organization workspace | `/me`, organization and invitation routes; actual signup/login delegated to selected identity provider | `User`, `Organization`, `Membership` | Covered at conceptual level; identity provider and signup handoff remain open. |
| College/club details and organization verification | Organization create/edit and verification routes | `Organization`, `OrganizationVerification` | Mostly covered; verification evidence and decision workflow not finalized. |
| Office bearers and faculty coordinator tenure records | Roster GET/PUT existed | `OrganizationPersonRecord` / tenure-like records | Needs strict distinction between a directory/tenure record and an account membership/role. v0.2 proposes tenure-specific endpoints and states that a roster record grants no access by itself. |
| Standalone event with per-department leads | Event and department routes, lead invitations and department member assignment | `Event`, event-scoped `Department`, scoped role assignments | Covered; department assignment endpoint naming was ambiguous with organization membership. v0.2 uses `department-assignments`. |
| Multi-event program, shared departments, event leads and coordinators | Program, child-event, shared-department, event-lead invitation and event-specific department assignment routes | `Program`, child `Event`, program-scoped `Department`, event-scoped task and assignment records | Covered in general. Directory semantics need to preserve the founder rule that all active members of the program workspace can see basic member/event assignment details, without granting private record access. |
| Team directory across events | `/programs/{programId}/members` | Membership/role/department assignment records | Original API access note was too narrow/ambiguous. v0.2 states active program-workspace members can view the approved basic directory across child events; contact details remain restricted. |
| Tasks with owners and specific deadlines | Create, edit, progress, deadline request/change, history | `Task`, `TaskAssignee`, deadline/status history | Partially covered. v0.1 allowed ambiguous mutation through generic `PATCH`; v0.2 separates assignee changes and deadline-change decisions and requires a specific deadline for active tasks. |
| Evidence submission and approval | Evidence submissions, review endpoints, review history | `EvidenceSubmission`, `EvidenceArtifact`, `TaskReview` | Conceptually covered; the final reviewer role bundle is still pending. Self-approval is prohibited. |
| Native registration | Public registration submission, config, participants | `RegistrationForm`, `Registration`, `Participant`, registration-participant link | Covered, but individual/team registration creation needed one canonical internal model. v0.2 clarifies this and leaves whether a separate staff-side team-creation route is needed open. |
| External registration source | Connections, import jobs, retry and status | Source connection, external mapping and sync run | Covered as a design direction; provider, sync direction, source-of-truth fields, conflict behavior and auth model remain open. |
| Individual check-in for solo and team registrations | Lookup, one-person check-in, attendance list and correction | `CheckIn` linked to individual `Participant` | Strong alignment. v0.2 expresses correction as an auditable void operation rather than deletion. Offline behavior remains open. |
| Event close-out and program reports | Close-out, event report, report evidence, program report | `PostEventReport`, evidence, close-out records and audit | Covered conceptually; report revisions/reopen policy and exact mandatory fields remain open. |
| Internal staff operational blockers | Requirements v0.9 has P0 `CO-FR-012`, data model has `InternalOperationalIssue`; v0.1 API stated no blocker API was included pending confirmation | `InternalOperationalIssue` | **Direct consistency gap.** v0.2 proposes internal staff-only issue routes to match CO-FR-012 while explicitly prohibiting public participant issue submission. Final scope should retain this only as internal ops. |
| Participant-facing question/issue submission | Explicitly absent | Explicitly excluded | Correct. Do not add attendee doubt/request/ticket endpoints. |
| File evidence | Evidence endpoints mention file/link submissions and private storage; upload session remains a note | `EvidenceArtifact` / `FileObject` | Incomplete endpoint-level contract. v0.2 adds this as a required decision: define upload initiation/completion, scanning, size/type controls, authorized retrieval and retention. |
| Notifications and invitations | Invitation create/resend/revoke, user notification endpoints; email treated as side effect | `Notification`, invitation and audit records | Conceptually covered; delivery status, retry/outbox and notification channel policy remain provider-level decisions. |
| Authorization and tenant isolation | Explicit security invariants | Organization scope constraints, role assignment and audit data | Good high-level coverage; test all endpoints with direct API calls and cross-org/cross-event negative tests before implementation readiness. |

## 3. Findings by severity

### Critical before freezing the API contract

**API-REV-001 — Role/person record separation**  
An office-bearer or faculty-coordinator roster record must not automatically create an account, membership or access grant. The API/data model must separately represent tenure/roster information and a person's actual CampusOps membership/role. This is needed to support editable leadership tenure without accidental access.

**API-REV-002 — Task deadline changes can bypass the dedicated workflow**  
The generic task `PATCH` endpoint could be read as allowing direct deadline changes, while dedicated deadline-change endpoints exist. The API should reject direct `due_date`/`due_at` changes through generic patch and use the auditable deadline workflow. Likewise, assignee changes should be explicit and auditable. Applied in v0.2.

**API-REV-003 — Operational issue scope mismatch**  
Requirements v0.9 and the data model retain staff-only operational blockers, but the API draft omitted those routes pending confirmation. v0.2 proposes scoped staff-only routes consistent with `CO-FR-012`; no participant-facing issue submission is allowed. Confirm that the final PRD retains only the internal operational use.

**API-REV-004 — Registration create paths are ambiguous**  
The generic public registration endpoint supports both solo and team registration, while a team-registrations create endpoint could become a parallel path. Both must converge on the same validation and persistence service and model. Before freezing v1, decide whether the team endpoint is only for authorized staff/walk-in operations or remove it in favor of one create route with `registration_type` and a participant roster. Clarification added in v0.2.

### High priority before implementation

**API-REV-005 — Program directory access must match the founder workflow**  
The founder wants people in the multi-event workspace to view members across the other events. Make the basic cross-event roster available to active program-workspace members. This must not grant access to private participant data, personal contacts, task evidence or event administration. Clarified in v0.2.

**API-REV-006 — Department assignment naming collided with membership terminology**  
The standalone department endpoints used a `memberships` path while the data model also uses organization membership. That creates confusion about whether a route creates organization access or only department membership. v0.2 changes these routes to `department-assignments` and keeps organization membership separate.

**API-REV-007 — Task state vocabulary differs across documents**  
The API draft used `submitted_for_review`; the data model discussed “Awaiting review,” while requirements sometimes display “In review.” These should be one canonical machine state with a UI-label mapping. v0.2 sets `submitted_for_review` as the canonical API value and documents display labels. Apply the mapping to the PRD/schema before freeze.

**API-REV-008 — File upload flow isn't fully specified**  
A task can submit evidence as a file or link, but the API contract only discusses an upload-session endpoint as a possibility. Provider choice is not needed to define the lifecycle: initiate upload, upload privately, finalize/verify metadata and scan state, attach to evidence submission, and authorize retrieval. Provider-specific signed-URL details remain open.

**API-REV-009 — Check-in reversal must be a correction, not deletion**  
The v0.1 table used `DELETE` while text prohibited physical deletion. v0.2 proposes a `POST .../void` route requiring authorization and a reason, preserving original check-in and correction history.

### Medium priority / policy to resolve

**API-REV-010 — Task assignee endpoints were implicit**  
Creation/patch could be used to assign owners, but separate assignment mutation makes permission validation and history clearer. v0.2 adds explicit assignee add/remove routes with a no-owner safeguard.

**API-REV-011 — Reviewer authority remains a product decision**  
Founder workflow says leads and core members review proof. The precise role/scope table must define the relevant lead (standalone department lead vs multi-event event lead), authorized core members, backup reviewers, and no self-review. Do not ship with a generic `reviewer` permission disconnected from this model.

**API-REV-012 — Deadline and time zone semantics need one rule**  
A task requires a specific due date. If a time is set, interpret it in the event/organization's declared time zone and store a canonical instant; date-only deadlines should remain date-only and not shift through UTC conversion. Due-date change requests must preserve old/new values, actor, reason, and notifications.

**API-REV-013 — Invite token handling needs explicit secret hygiene**  
Invite tokens should be high entropy, single-use, expiry-bound, stored as a hash, redacted from logs/analytics, and not echoed in errors. Exact frontend route and provider remain open. Added to v0.2 endpoint rule.

**API-REV-014 — Email invitation delivery status is not completely exposed**  
Invitation state should distinguish pending acceptance from delivery failure. Retrying an email must not create a duplicate membership or consume the invitation. This can be handled internally with an outbox and exposed through safe invitation delivery metadata; provider choice remains open.

## 4. Applied changes in API contract v0.2

1. Clarified that office-bearer/faculty tenure records do not themselves grant account access.
2. Proposed add/edit/end-tenure endpoints rather than an ambiguous whole-roster replacement operation.
3. Renamed standalone department `memberships` endpoints to `department-assignments`.
4. Specified basic roster visibility across child events for active members of a program workspace, while preserving private-data permission boundaries.
5. Made generic task PATCH disallow direct deadline/assignee mutation, and added explicit assignee and deadline-request decision operations.
6. Standardized machine task state `submitted_for_review`, with UI labels “In review”/“Awaiting review” mapped to it.
7. Clarified that public native registrations, staff-entry registrations and imports converge on one internal registration model; the separate team endpoint remains a design choice, not a parallel schema.
8. Changed check-in reversal from delete to auditable void/correction.
9. Added internal staff-only operational blocker routes in line with CO-FR-012. No participant-facing issue submission endpoint has been added.
10. Added upload lifecycle and invite-token secret hygiene to the explicit contract/decision requirements.

## 5. Open decisions remain open

The following are not settled by this review:

- Authentication provider and account-creation handoff.
- Organization verification method and evidence.
- Final role bundle/inheritance and reviewer/backup-reviewer rules.
- Whether separate staff team-registration creation endpoint is required.
- Exact registration fields, duplicate matching and team roster-edit cutoff.
- First external registration provider and import-versus-sync strategy.
- Offline check-in behavior, storage/email/hosting providers and retention policies.
- Report finalization/reopen policy and exact mandatory fields.

These should be assigned a status in the decision log rather than silently assumed.

## 6. Required contract acceptance tests before approval

- A roster/tenure edit does not create a login or privilege; a separate approved membership invitation does.
- Department assignments are not confused with organization membership.
- Program roster visibility shows basic cross-event directory data but blocks private event participant/task/evidence data outside scope.
- Task deadline and assignee fields cannot be changed through generic patch paths that bypass dedicated authorization/audit handling.
- Task state values are consistent across API, requirements, data model and UI mapping.
- A team registration creates one team/group entry plus an individual participant record per member; repeating the same submission does not duplicate records.
- Every participant has a separate check-in. A check-in correction preserves the original event and reason.
- Internal operational issues are visible only to authorized staff; no public attendee issue-raising route exists.
- Private evidence cannot be read without parent task scope; unscanned/invalid files cannot be accepted as approved evidence under the defined scan policy.
- A cross-organization or cross-event request is denied even if the caller fabricates a resource ID.
- Invitation email delivery failure does not mark acceptance and retry does not duplicate membership.

## 7. Recommendation

Use API contract v0.2 as the next review baseline, not as an implementation-ready commitment. Then reconcile the canonical task-state mapping and assignment entities back into the requirements, role matrix and logical data model. The next approval gate should be a small, explicit founder decision set covering reviewer authority, directory privacy, registration path design, and deadline-change policy.
