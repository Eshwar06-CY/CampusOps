# CampusOps — Architecture and Requirements Traceability Review

**Version:** 0.1  
**Date:** 28 October 2026  
**Status:** Review completed at document level; decisions remain proposed unless explicitly founder-confirmed.  
**Purpose:** Check whether the proposed architecture, requirements specification, role/permission matrix, and logical data model agree before implementation planning.

## 1. Documents reviewed

- `CampusOps_Requirements_Specification_v0.9.md`
- `CampusOps_Role_and_Permission_Matrix_v0.1.md`
- `CampusOps_Data_Model_and_Relationship_Map_v0.1.md`
- `CampusOps_Architecture_Decision_Record_v0.1.md`
- `CampusOps_Decision_Log_v0.4.md`

This review is documentation-only. It does not authorize coding, package installation, deployment, or mutation of the project workspace.

## 2. Overall assessment

**Assessment: directionally aligned, not yet implementation-ready.** The modular-monolith recommendation, relational database, separate user identity and organization membership, scoped authorization, private evidence storage, registration-source adapter, and individual check-in records are compatible with the product direction.

No need has been established for microservices or a complex distributed system. However, several product rules must be made precise before a physical schema and API contracts are frozen. The main remaining risks concern permissions and scope inheritance, task-review authority, organization verification, external registration synchronization, participant identity/deduplication, privacy of member directories, and event-day connectivity.

The review distinguishes:
- **Aligned:** the documents express compatible intent.
- **Partially aligned:** a direction exists, but a rule, constraint, or failure case is not fully specified.
- **Open decision:** a product/architecture choice still needs to be made.
- **Implementation gate:** must be verified before the named pilot or production use.

## 3. Traceability matrix

| Area | Requirements / workflow | Logical model | Architecture decision | Assessment | Required action before implementation |
|---|---|---|---|---|---|
| Individual identity and organization workspace | CO-FR-021, CO-FR-022, CO-FR-023, CO-FR-030, CO-FR-031 | `User`, `Organization`, `Membership`, `OrganizationPersonRecord`, `Invitation` | ADR-004, ADR-005, ADR-008 | Partially aligned | Choose identity provider; finalize organization verification and pending-workspace behavior; document which account attributes are global versus organization-specific. |
| Personal invitations | CO-FR-023; AT-009 | `Invitation`, `InvitationGrant`, `Membership`, `RoleAssignment` | ADR-004, ADR-008 | Partially aligned | Token must be single-use, expiring and bound to intended email, organization, scope and granted role. Acceptance must re-check current invitation status and authorization server-side. Existing users must join with their existing account. |
| Standalone event setup | CO-FR-001, CO-FR-002, CO-FR-024, CO-FR-026 | `Event` with `program_id = NULL`, event-scoped `Department`, event/department role assignments | ADR-001, ADR-003, ADR-005 | Aligned in principle | Define mandatory/optional setup fields, which fields are editable after work starts, and how date/time/time zone edits affect deadlines and notifications. |
| Multi-event program setup | CO-FR-002, CO-FR-025, CO-FR-015 | `Program`, child `Event` rows, program-scoped `Department`, event-specific `Task` rows | ADR-001, ADR-003, ADR-005 | Partially aligned | Maintain a program-level shared department definition while keeping tasks, schedules, registrations, check-ins and reports event-specific. Explicitly define which program grants apply to child events; do not infer permissions solely from shared department membership. |
| Configurable roles and scopes | CO-FR-003, CO-FR-004; role matrix sections 4–10 | `RoleDefinition`, `Permission`, `RolePermission`, `RoleAssignment`, `Membership` | ADR-005 | Partially aligned | Freeze a permission vocabulary and scope-inheritance rules. Distinguish office bearers, core/sub-core leads, event leads, department leads, coordinators, volunteers, faculty coordinators and registration staff. Equivalent authority should be granted deliberately, not by matching display labels. |
| Task owner and deadline | CO-FR-005, CO-FR-006, CO-FR-027 | `Task`, `TaskAssignee`, `TaskDependency`, `TaskStatusHistory` | ADR-003, ADR-005, ADR-008 | Partially aligned | Require a clear accountable owner and a specific due date/time policy. Decide multiple-assignee behavior, whether deadlines can change after work starts, who may change them, and how deadline changes are audited/notified. |
| Proof-gated task completion | CO-FR-007, CO-FR-027; AT-006, AT-011 | `EvidenceSubmission`, `EvidenceArtifact`, `FileObject`, `TaskReview`, `TaskStatusHistory` | ADR-003, ADR-005, ADR-006, ADR-008 | Aligned in principle; authority open | Enforce the state machine on the server: assignee submits proof → awaiting review → reviewer approves or requests changes → completed only on approval. Define eligible reviewers and keep the recommended self-review prohibition unless explicitly changed. Preserve rejected submissions and notes. |
| Evidence files and links | CO-FR-027, CO-FR-013, CO-SEC-003 | `EvidenceArtifact`, `FileObject`, `ReportEvidence` | ADR-006 | Partially aligned | Set allowed file types/size, HTTPS URL policy, private access model, malware/quarantine expectations, retention/deletion behavior and download authorization. Do not store private evidence at permanent public URLs. |
| Native registration | CO-FR-008, CO-FR-009, CO-FR-028 | `RegistrationForm`, `Registration`, `Participant`, `RegistrationParticipant`, `CheckIn` | ADR-003, ADR-007 | Partially aligned | Define minimum fields and event-specific data retention. Keep team registration separate from individual participant records. Do not use email alone as an infallible unique-person identifier. |
| External registration integration | CO-FR-016; WF-003; AT-003 | Source metadata on registration records; integration/source IDs and sync state | ADR-007 | Open implementation decision | Select the first source and import mode (e.g. Google Forms API, CSV, or both). Define source of truth per field, stable external identifiers, idempotent re-import, mapping failures, conflict review, token revocation and fallback. API availability/permissions must be technically verified. |
| Individual check-in for solo/team events | CO-FR-009, CO-FR-028; AT-004, AT-012 | `Participant`, `RegistrationParticipant`, `CheckIn` | ADR-003, ADR-007, ADR-009 | Aligned in principle; reliability open | Make each check-in event- and participant-scoped; prevent duplicate successful check-ins with transaction/unique invariant; define authorized overrides and audit history. A team registration must never mark all members present automatically. |
| Event-day operational status and staffing changes | CO-FR-010, CO-FR-011, CO-FR-012 | `Task`, `TaskAssignee`, `TaskStatusHistory`, `InternalOperationalIssue`, `AuditEvent` | ADR-005, ADR-008, ADR-009 | Partially aligned | Preserve reassignment history and exactly identify current owner. Ensure issues are internal team/operational blockers only; do not add participant-facing question or issue submission. Define how changes reach affected staff. |
| Notifications | CO-FR-019; rejection and invitation flows | `Notification`, `AuditEvent` | ADR-008 | Partially aligned | Pick channels/provider later; define retry/idempotency and delivery status. Email informs a user but never grants authority. A rejected proof must carry a reviewer note and notify the responsible submitter(s). |
| Post-event close-out and reports | CO-FR-013, CO-FR-014, CO-FR-015; AT-007 | `PostEventReport`, `ReportEvidence`, child `Event` and `Program` | ADR-003, ADR-006 | Aligned in principle | Define required report fields, whether reports are versioned, how attendance totals reconcile, which evidence is mandatory, and how event/program roll-ups avoid confusing attendance counts with unique participants. |
| Internal audit history | CO-SEC-004 and related security requirements | `AuditEvent`, status histories, `TaskReview` | ADR-003, ADR-005, ADR-008 | Partially aligned | Define the required event types, actor/target/scope/time/reason fields, access controls and retention. Do not log passwords, raw invitation tokens, OAuth secrets or unnecessary participant data. |
| Member roster visibility | Founder direction: workspace members can view members across events; CO-SEC-006 | `Membership`, `RoleAssignment`, event/program memberships | ADR-005 | Open privacy detail | Confirm whether names, roles, departments and event assignments are visible workspace-wide while email/contact details remain restricted. Roster visibility must not automatically grant editing rights or access to participant records. |
| Degraded network/offline behavior | CO-NFR-003, CO-NFR-004; WF-004; AT-008 | `CheckIn`, possible sync metadata not yet finalized | ADR-009 | Implementation gate | Test representative venue conditions and agree a manual fallback. Do not promise offline check-in until local data protection, duplicate prevention, sync conflicts, reconciliation and device purge behavior are designed and tested. |
| Hosting, operations and backups | CO-NFR-004, pilot readiness | All persisted records and private file references | ADR-010 | Open decision | Determine budget, region, environment separation, secrets handling, backups and restore tests before accepting real participant records. |

## 4. Cross-document consistency findings

### 4.1 Shared department versus event-scoped work

The logical data model proposes program-scoped shared departments in multi-event programs and event-specific tasks. This matches the founder's intended workflow. Keep that boundary explicit in the physical schema and authorization checks: a coordinator may be assigned to a shared department, but that fact alone must not grant access to every event's tasks or participant records.

### 4.2 Department lead versus event lead

Standalone events use department leads; multi-event programs use leads assigned to individual child events, with departments shared across the program and no default separate lead for every department. Represent these as scoped role assignments instead of hard-coded fields like `event.lead_user_id` or `department.lead_user_id`. This supports equivalent authority, multiple eligible leads, and later reassignment without losing history.

### 4.3 Proof approval is a controlled state transition

UI-only prevention is insufficient. The backend must reject a direct request that tries to mark a proof-required task complete without an approved review. The allowed reviewer roles and self-review policy must be defined in the permission matrix before implementation.

### 4.4 Team registration and individual attendance are different entities

A team registration is a grouping/submission context, not a check-in result. Every participant needs an event-scoped attendance state. Database constraints and transactional code should prevent duplicate check-in under repeated or concurrent requests.

### 4.5 Participant-facing issue submission is out of scope

The requirements and architecture may retain `InternalOperationalIssue` for staff-recorded blockers, incidents or operational problems. They must not create a participant-facing “raise a doubt/issue” feature. Keep the distinction visible in requirements, route authorization, navigation and test scenarios.

### 4.6 Marketing stays out of scope

Do not add promotional campaign planning, class-to-class promotion tracking, poster/reel creation or social media publishing. Operational event briefings, registration, staffing and close-out documentation remain in scope.

### 4.7 Proposal status must remain visible

Technology selections (frontend/backend stack, PostgreSQL, managed identity, object storage, notification provider and hosting) are proposals until their respective gates are completed. Founder-confirmed product behavior should be kept separate from recommended security and hosting defaults.

## 5. Priority decision gates

### Gate A — Required before freezing API contracts and physical schema

1. Role and permission rules by scope, including the approval-eligible roles and self-review prohibition.
2. Program/event/department relationships and permission inheritance behavior.
3. Native registration fields, team registration structure, individual participants and duplicate-person handling.
4. Task proof-required rule and status transitions.
5. Roster visibility: fields everyone can see versus contact details restricted to specific roles.
6. Definitions for dates, times, time zones and deadline edits.

### Gate B — Required before selecting providers/integration implementation

1. Authentication provider and verified account lifecycle.
2. Organization verification and pending-workspace behavior.
3. First external registration source, OAuth/access model, sync direction and failure recovery.
4. File storage/provider, allowed types/size, private access and retention.
5. Transactional email/notification provider and retry semantics.
6. Hosting budget and region constraints.

### Gate C — Required before a real-world pilot

1. Organization isolation and negative authorization tests pass.
2. Task approval and check-in concurrency/idempotency tests pass.
3. Private file/evidence access checks and retention behavior are verified.
4. Registration import failure and reconciliation workflow is tested.
5. A realistic event-day connectivity test and documented manual fallback are completed.
6. Backup and restoration procedure is tested.
7. Data retention, export and deletion decisions are documented.

## 6. Recommended next review sequence

1. Review the role/permission matrix and close Gate A items, especially approval permissions and roster privacy.
2. Amend the logical data model to express the agreed constraints (do not create a physical schema yet).
3. Choose the initial registration integration approach using a feasibility test before selecting a provider.
4. Update the ADR and decision log with each approved decision.
5. Only then prepare API contracts and an implementation-ready PRD.

## 7. Decision summary

- **Directionally aligned:** modular monolith, relational operational data, individual accounts plus organization membership, role/scope authorization, private evidence storage, adapter-based external registration, separate event/program workflows, individual check-in.
- **Partially aligned:** role inheritance, reviewer authority, due-time semantics, data retention, notification behavior, file policy and reporting roll-ups.
- **Still open:** authentication/hosting/storage/email vendors, organization verification policy, external integration sequence, offline check-in, roster contact privacy and several permission rules.
- **Implementation status:** no code authorized or produced by this review.
