# CampusOps — Product Requirements Document (PRD)

**Version:** 1.1  
**Status:** Consolidated product baseline; FPC-01–FPC-05 founder-approved; not an authorization to implement  
**Prepared:** 28 October 2026  
**Product:** CampusOps — Event Operations Management SaaS  
**Working tagline:** Plan Better. Coordinate Smarter. Deliver with Confidence.

## 1. Executive summary

CampusOps is intended to help organizations prepare, coordinate, execute, and document events in one connected workspace. It must support both a simple standalone event (for example, a workshop or seminar) and a complex multi-event program (for example, a college festival such as ASPERA E-Week), without forcing a small event through festival-level setup.

The product's defining intention is a connected operating workflow: teams, tasks, deadlines, proof of completion, registration, individual check-in, event-day status, and post-event records remain linked rather than being managed as unrelated tools. The product vision is comprehensive, but delivery should proceed in tested increments.

The first research beachhead to investigate is college clubs and student-led organizations, grounded in the founder's experience coordinating E-Week. This is a proposed initial customer segment, not validated market demand. CampusOps may support other event organizers over time.

## 2. Product vision and problem hypothesis

### 2.1 Vision

Provide a shared operating workspace through which an organization can prepare an event, coordinate people and work, run its event-day operations, and close out the event with reliable records.

### 2.2 Problem hypothesis

Event organizers may coordinate event details, teams, deadlines, approvals, registrations, attendance, evidence, and reports across spreadsheets, forms, messaging applications, shared documents, and meetings. This can create repeated follow-ups, unclear ownership, inconsistent records, difficult check-in, and incomplete post-event documentation.

This is a hypothesis to validate, not a proven statement about all event organizers. Competitors already offer many overlapping features. CampusOps must demonstrate an easier, better-connected workflow instead of claiming that an all-in-one feature list is unique.

### 2.3 Product principles

1. One organization workspace with individual accounts; never a shared club password.
2. Different setup journeys for standalone events and multi-event programs, using shared underlying concepts where sensible.
3. Permissions are explicit and scoped; a title alone must not grant access to unrelated events or private records.
4. A task cannot be completed solely by changing its status: evidence submission and authorized review are required.
5. Team registration and individual attendance are distinct; every participant is checked in individually.
6. Operational records remain connected from planning through closure.
7. Keep the product usable for a workshop while supporting more complex event programs.
8. Do not claim offline operation, integration compatibility, security, efficiency gains, or production readiness until tested.

### 2.4 Competitive context and positioning hypothesis

The prior research phase reviewed public product pages and comparison material for Planning Pod, Cvent, Eventbrite, Fensta, Campusmeet, Swipin, Chapter, Asana, Trello and Airtable. These providers collectively advertise overlapping capabilities in event setup, task management, event registration, attendee check-in, volunteer/team coordination, reporting or general project operations. The exact feature set and availability must be rechecked before any launch claim is made.

Reference pages used during the prior research phase include:
- [Planning Pod features](https://planningpod.com/features)
- [Cvent platform](https://www.cvent.com/en/platform)
- [Eventbrite organizer features](https://www.eventbrite.com/organizer/features/all-features/)
- [Fensta](https://www.fensta.in/)
- [Campusmeet](https://campusmeet.in/)
- [Swipin](https://swipin.in/)
- [Asana features](https://asana.com/features)
- [Trello product tour](https://trello.com/tour)

**Positioning hypothesis:** CampusOps offers an event-team-first operational workflow that connects preparation, responsibility assignment, proof-based task completion, participant registration and individual check-in, event-day status, and close-out records. It supports both a standalone event and a multi-event program without forcing either through the same complexity level. This is a hypothesis—not a proven competitive advantage or a claim that competitors lack these features.

**Validation requirement:** Compare actual end-to-end workflows, setup effort, usability, cost/access constraints and target-user needs. Feature presence alone is insufficient; public product documentation may not expose every capability or limitation.

## 3. Scope

### 3.1 In scope

- Public product landing page with product information, sign-in, and organization/account creation entry points.
- Personal user accounts and organization workspaces.
- College/club details and editable office-bearer and faculty-coordinator directory records.
- Organization verification workflow: creator email must be verified and organization/club details reviewed by a CampusOps platform administrator using public institution/club evidence or faculty-coordinator confirmation when public evidence is insufficient; collect minimum necessary evidence and provide a reasoned rejection/resubmission path.
- Invitations for individual team members, bound to an intended email, organization, role and scope.
- Configurable roles and scoped permissions, including equivalent authority for equivalent roles.
- Standalone event setup with event-specific departments and department leads.
- Multi-event program setup with child events, common program departments, and event-specific leads.
- Team membership, task assignment, deadlines, progress updates, proof files/links, approval/rejection, review history, and notifications.
- Organizer-published, read-only attendee information (event schedule, venue, rules and instructions); attendees cannot submit questions, doubts, issues or requests through a participant portal.
- Native registration as a product capability, plus a defined adapter path for selected external registration sources.
- Solo and team registrations that resolve into individual participant records.
- Individual check-in using QR/registration identifier with a search fallback, duplicate prevention and audited corrections.
- Event-day operational overview and staff-only operational blockers.
- Post-event reports, registrations-versus-attendance reconciliation, supporting evidence, closure checklists, and program-level summaries.
- Audit history, access controls, data minimization, backup/recovery planning and testing.

### 3.2 Explicitly out of scope

- Marketing campaign management or promotional execution.
- Tracking class-to-class promotions, college visits or promotional campaigns.
- Poster, presentation, reel, or other marketing-asset creation.
- Social-media publishing and marketing analytics.
- Participant-facing doubt/question/request/issue submission portals.
- A general participant support-ticketing system.

Staff-only operational blockers (for example, equipment not delivered or a room locked) remain in scope as a lightweight internal operations record. This is not a participant-facing ticketing feature.

### 3.3 Deferred or conditional

- External registration provider and initial connector; Google Forms is a candidate, not selected.
- External synchronization direction and field-level source-of-truth rules.
- Full offline check-in; the initial posture is online-first with a documented manual fallback. Do not promise offline support unless designed and tested.
- Reusable prior-event templates; desirable later capability, provided stale dates, rules, personal data and obsolete configuration are not silently copied.
- Advanced automation, complex reporting, additional integrations and organization-wide product analytics.
- Hosting, transactional email provider and evidence-storage vendor. Supabase Auth is the preferred identity candidate pending the required feasibility/security evaluation.

## 4. Users and responsibilities

| User/role | Primary needs | Scope notes |
|---|---|---|
| Organization workspace administrator | Manage workspace configuration, membership, role grants and administrator continuity | Account/workspace role, separate from event title; organization verification and MFA/recovery policies are approved, with operational implementation and provider feasibility still to be completed |
| Office bearer / authorized core member | Oversee preparation, assign work, add members, review evidence and monitor progress | Permissions must be explicitly granted at the appropriate organization/program/event scope; equivalent powers can be configured |
| Event Lead (multi-event program) | Lead assigned child event(s), coordinate work, assign coordinators to shared departments and report progress | Cannot automatically administer other events or their restricted records |
| Department Lead (standalone event) | Manage assigned department members and departmental tasks; review proof when authorized | This is the default standalone structure; not a default separate role for every department in a multi-event program |
| Coordinator / team member | See assigned work, deadlines, briefing and status; update progress and submit evidence | Can see the basic workspace directory but only permitted operational/private records |
| Registration staff | Find registrations and record a participant's individual check-in | Minimum participant data needed for assigned event/station; may be a permission set on an individual account rather than a distinct account type |
| Faculty coordinator | Maintain an organizational role/contact record and, if invited, use the platform with explicit permissions | A directory record alone does not grant account access |
| Participant | Register and be checked in individually | No participant-facing question/issue portal in scope |

### 4.1 Jobs to be done

| User | Job to be done |
|---|---|
| Workspace administrator | Establish a legitimate organization workspace, maintain access and keep workspace administration continuous through leadership changes. |
| Office bearer/core member | See progress across relevant work, assign responsibilities, review evidence and identify overdue or blocked work without reconstructing status from separate conversations. |
| Standalone department lead | Form and coordinate a department, distribute work, monitor deadlines and review proof within authority. |
| Multi-event lead | Run the assigned child event while coordinating through shared program departments and seeing relevant cross-event staffing. |
| Coordinator/team member | Know exactly what to do, by when, with whom, and what evidence is required for acceptance. |
| Registration staff | Verify each participant quickly and accurately, including members of group registrations and exceptions. |
| Event close-out owner | Reconcile registration and attendance, gather report/evidence items, and close the event with an auditable record. |

### 4.2 Identity and organization model

CampusOps has organization workspaces and personal accounts. Every person signs in as themselves. The organization/club does not have a shared password. A workspace membership, a directory/tenure record, and a role assignment are separate concepts:

- Adding or editing an office-bearer or faculty-coordinator directory entry does not automatically create an account or grant access.
- An invitation conveys the role and scope selected by an authorized inviter. The invitee may accept the displayed grant but cannot self-select a higher role.
- Existing users sign in and accept invitations; new invitees create their individual account before accepting.
- Membership removal revokes current access while retaining required historical attribution.
- FPC-01–FPC-05 are founder-approved at policy level. The verified-email creator becomes the Primary Workspace Administrator of a pending workspace, with privileged operations limited until organization verification passes. Supabase Auth is the preferred authentication candidate pending feasibility/security evaluation. Platform operators must use MFA; workspace primary administrators must enrol MFA before real participant data is used in a pilot. Sensitive workspace recovery requires documented review, independent organization evidence, established-contact notification, session revocation and invalidation of outstanding invitations/reset links. Hosting, email and file-storage providers remain open.

## 5. Main user journeys

### 5.1 Public entry and organization onboarding

1. A visitor lands on the public CampusOps page and can learn what it does, log in, or start account/workspace creation.
2. The initial creator creates a personal account and provides college and club/organization details. Password handling belongs to the personal account, not a shared organization account.
3. Personal email verification and organization verification are separate checks. The creator verifies their email; a CampusOps platform administrator reviews organization details using an official institution/club page or domain, or faculty-coordinator confirmation if public evidence is insufficient. Only minimum necessary evidence is collected; no identity-document upload is required by default. Rejections include a reason and a resubmission path.
4. The verified-email creator is the Primary Workspace Administrator of the `pending_verification` workspace. Privileged event/member operations remain limited until organization verification passes. On verification success, the workspace is activated; verification does not automatically validate the roles of subsequent members.
5. The workspace is administered through individual named accounts and scoped permissions.

### 5.2 Standalone event setup

1. An authorized member chooses **Standalone Event**.
2. They enter an editable event name, event date/day, relevant time information, and an optional venue. Venue may be added or changed later.
3. They define the event-specific departments.
4. Each department is assigned a Department Lead using the intended person's name and email. The system issues an invitation tied to that event, department, role and organization.
5. The invitee creates or signs into their individual account and accepts the invitation; they do not create a second club account.
6. Department Leads may add members and assign departmental work within scope. Authorized office bearers/core members may add coordinators and assign tasks directly to leads or coordinators.
7. Tasks require an owner and a specific deadline. Work progresses through status updates, evidence submission and authorized review.

### 5.3 Multi-event program setup

1. An authorized member chooses **Multi-event Program** and enters program details and multiple event records.
2. The program defines common departments. Each child event keeps its own details, dates, venue, tasks, registrations, attendance, issues and close-out record.
3. Leads are assigned to specific child events. By default, separate department leads are not created for every shared department.
4. Authorized office bearers/core members add coordinators and assign them to shared departments and relevant event/task scopes.
5. Members can view the workspace's basic directory across events, while private contact and participant data remain permission-controlled.
6. Program summaries aggregate child-event status without merging the source records or silently double-counting participants.

### 5.4 Task, evidence and approval lifecycle

1. An authorized user creates a task with an owner, due date/time in the event's timezone context, status and optional dependencies.
2. The assignee updates progress and, when work is ready, submits completion evidence as a file or link.
3. The task moves to **Submitted for Review**; it is not yet completed.
4. An authorized reviewer within scope reviews the evidence. The submitter cannot approve their own submission.
5. Approval moves the task to **Completed**. Rejection moves it to **Changes Requested** (or another explicitly defined non-completed state), requires a reason, preserves the history and notifies the assignee.
6. A backup reviewer or documented escalation route is available when the primary reviewer is absent.

### 5.5 Deadline changes

- Every active task has an owner and a specific due date/time.
- An assignee requests a deadline change and supplies a reason.
- An authorized lead or office bearer decides within their scope.
- A specially authorized administrator may make a direct change if explicitly permitted; record old and new values, actor, time and reason, and notify affected people.
- Generic task edits cannot bypass this flow.

### 5.6 Registration and event-day check-in

- CampusOps supports native registration as a product capability and must be able to integrate selected external registration sources later.
- External imports require stable source identifiers where available, idempotent processing, visible sync errors and explicit conflict handling. Do not merge people based only on matching email addresses.
- A team registration/group record is distinct from individual participant records.
- Every participant is checked in individually, including members of a team arriving together.
- Lookup uses QR or registration ID, with name/search fallback for exceptions.
- Duplicate check-ins are blocked or return an idempotent “already checked in” result.
- A correction/void requires authorization, reason and audit history rather than deleting the original record.
- Walk-ins may be added only under the event's configured policy and required fields; an unverified attendee must not be represented as an already verified registration.
- The initial operational stance is online-first with a documented manual fallback. Full offline mode is not promised until designed, implemented and tested.

### 5.7 Internal operational blockers

Authorized staff can record an internal problem such as unavailable equipment, a locked room or a schedule conflict, assign an owner, track resolution and link it to the affected event/task. This is internal operational tracking, not an attendee request portal.

### 5.8 Post-event close-out

The event team records event name/details, venue, date, duration, registration totals, actual attendance, supporting photos/evidence, reports, unresolved obligations and lessons learned. Required items remain outstanding until completed or explicitly excepted by an authorized actor. Program summaries show per-event results and document aggregation rules.

## 6. Functional requirements and acceptance criteria

Priority meanings: **P0** = foundational workflow to define/validate before first-release approval; **P1** = next capability or provider-dependent; **P2** = later/conditional. These priorities do not prove market demand.

| ID | Requirement | Priority | Minimum acceptance criteria |
|---|---|---:|---|
| CO-FR-001 | Create/edit event | P0 | Authorized users can save a draft; required fields and dates are validated; optional venue can be completed later; changes are auditable where material |
| CO-FR-002 | Standalone and multi-event workflows | P0 | Standalone does not require a parent program; program contains child events; shared summary does not destroy event-level records or silently double-count |
| CO-FR-003 | Configurable, scoped roles/permissions | P0 | Equivalent roles can receive equivalent permissions; server enforces all protected actions; no self-elevation; permission changes are audited |
| CO-FR-004 | Teams/departments/memberships | P0 | Standalone department memberships and program shared departments are supported; assignment identifies event/department/task scope; active assignments can be reviewed |
| CO-FR-005 | Task owner/deadline/status | P0 | Active tasks require owner and specific deadline; invalid dependency cycles are blocked; due times respect event timezone |
| CO-FR-006 | Progress/blockers | P0 | Dated progress updates and internal blockers are visible within scope; blocked/overdue items are surfaced |
| CO-FR-007 | Evidence/review | P0 | File/link proof submission precedes review; no self-approval; approval alone transitions task to Completed; rejection requires reason, remains non-completed and triggers notification |
| CO-FR-008 | Native registration | P0 | Initial connected pilot uses native registration as the baseline path; form validation, native participant records, privacy and duplicate handling are defined |
| CO-FR-009 | Individual check-in | P0 | QR/registration-ID lookup plus search fallback; each person has own check-in; duplicate/concurrent check-ins resolve safely; corrections are audited |
| CO-FR-010 | Event-day operations view | P0 | Authorized users can see schedule, assignments, important status, unresolved blockers and check-in activity relevant to their scope |
| CO-FR-011 | Staff reassignment | P0 | Authorized reassignment updates current owner, retains previous assignment/history and notifies relevant people |
| CO-FR-012 | Staff-only operational blockers | P0 | Internal blocker has owner/status/resolution history; no participant-facing ticket or doubt-submission portal |
| CO-FR-013 | Post-event report | P0 | Captures event data, registration vs attendance, photos/supporting evidence and close-out notes; figures trace to source records |
| CO-FR-014 | Event closure | P0 | Mandatory close-out items are visible; closure cannot silently bypass missing required items; authorized exceptions require reason |
| CO-FR-015 | Program-level reporting | P0 for program workflow | Shows child-event status and declared aggregation rules without collapsing event source records |
| CO-FR-016 | External registration integration | P1 until source/feasibility chosen | Stable source IDs where available, idempotent imports, visible failure/conflict state, safe matching and recovery |
| CO-FR-017 | Organization onboarding/directory | P0 | Public landing/login/create-account flow; individual accounts; separate editable organization/person directory; verification policy enforced once selected |
| CO-FR-018 | Invitation lifecycle | P0 | Invitation bound to email/workspace/role/scope; single-use/revocable; proposed expiry 7 days; failed email delivery does not create membership; existing account can accept |
| CO-FR-019 | Notifications | P1 capability; provider undecided | In-app state remains authoritative; delivery failures visible; sensitive content not sent to unauthorized recipients |
| CO-FR-020 | Reusable templates | P2/conditional | If implemented, copied structures are reviewed; old dates/rules/personal data are not silently reused |
| CO-FR-021 | Office-bearer/faculty directory | P0 | Records are editable across tenure changes; directory entries alone do not create account membership or access grants |
| CO-FR-022 | Administrator continuity/recovery | P0 policy, detailed method open | Last admin cannot be silently removed; transfer/recovery requires deliberate process; prior actions remain attributed |
| CO-FR-023 | Audit history | P0 cross-cutting | Captures high-impact role, approval, deadline, check-in correction, integration conflict and closure decisions without logging secrets |

### 6.1 Non-functional, security and privacy requirements

| ID | Requirement | Verification approach |
|---|---|---|
| CO-NFR-001 | Responsive, accessible experience | Test core paths on desktop/mobile; keyboard use, labels, focus, contrast and actionable errors |
| CO-NFR-002 | Data integrity | Test simultaneous updates, retries, duplicate submissions, invalid transitions and failed requests |
| CO-NFR-003 | Useful state/error handling | Validate loading, empty, success, failure, retry and connectivity-loss states |
| CO-NFR-004 | Operational reliability | Define performance, availability, backup/restore and degraded-network targets before real data |
| CO-SEC-001 | Server-side authorization | Direct-API negative tests for every protected operation |
| CO-SEC-002 | Tenant/event isolation | Attempt unauthorized cross-organization and cross-event reads/writes |
| CO-SEC-003 | Personal data minimization | Document field purpose, access, retention, export and deletion |
| CO-SEC-004 | Auditability | Test attribution/history for sensitive role and operational changes |
| CO-SEC-005 | Integration security | Scope/revoke credentials; safe retries; logs do not expose tokens or unnecessary personal data |
| CO-SEC-006 | Invitation/roster privacy | Verify invite scope/email binding; basic member directory separated from private fields and participant records |

## 7. Approved foundational decisions

The founder explicitly approved FA-001–FA-009 in `CampusOps_Founder_Approval_Checklist_v0.2.md` on 28 October 2026, then approved FPC-01–FPC-05 in the subsequent closure decision. These are accepted product-policy decisions for the consolidated baseline.

| ID | Approved rule | Effect on product/technical design |
|---|---|---|
| FA-001 | Review within scope by authorized leads or core members; no self-approval; backup reviewer or documented escalation; rejection reason, retained history and notification | Model reviewer eligibility and review state transitions; enforce server-side |
| FA-002 | Explicit organization/program/event/department/task scopes; no implicit access to unrelated child-event private records; roles map to defined permission sets and users cannot self-grant | Implement scoped authorization and permission tests |
| FA-003 | Workspace-wide basic directory: name, role, department and event assignments; email/phone restricted to authorized operational need; participant data not exposed in directory | Separate directory fields from contact and participant permissions |
| FA-004 | Active tasks require a specific deadline and owner; event timezone is reference; assignee requests changes with reason; authorized lead/office bearer decides; authorized direct admin edits require old/new values, actor, time, reason and notification | Explicit deadline-change operation and audit trail |
| FA-005 | QR/registration ID lookup plus name/search fallback; check-in per person per event; duplicates blocked/idempotent; corrections require reason/audit; walk-ins follow event policy and required verification | Individual check-in record, unique/idempotent behavior, correction trail |
| FA-006 | Online-first with a documented manual fallback; do not claim full offline support until designed/tested; test degraded connectivity before pilot | Connectivity requirement and pilot gate |
| FA-007 | Native and external registrations normalize through internal validation; external source IDs and import history retained; idempotent imports; never merge solely on email; ambiguous matches reviewed; group and individual records separate; roster edits audited; configurable cutoff may be used and post-cutoff changes require review if configured | Adapter/source metadata, conflict queue/manual review, roster change audit; external provider and sync direction remain open |
| FA-008 | Keep lightweight staff-only operational blocker tracking; exclude participant-facing issue/question/request portal | Internal operations resource only; no public ticket routes |
| FA-009 | Invitation links single-use, tied to intended email/workspace/role/scope, revocable, expiry 7 days; resend safely reissues/refreshes; failed delivery does not create membership | Invitation state machine, secure token handling, invitation acceptance tests |

### 7.1 Decisions still open (not covered by FA-001–FA-009 approval)

- College/club verification evidence and review process.
- Which identity/authentication provider to use; managed auth remains a recommendation, not a selected vendor.
- Whether and when administrator MFA is mandatory; high-impact re-authentication is a proposed security control to finalize.
- Emergency organization recovery process and acceptable independent evidence.
- Transactional email/notification provider, file storage provider, hosting region/cost and backup/restore targets.
- First external registration connector (Google Forms is a candidate), access scopes and sync direction.
- Whether the first release implements full offline check-in; it is not promised by the approved online-first default.
- Physical database schema/API path names and file size/type/retention limits.

## 8. First-release strategy

Preserve the full product vision, but validate and deliver connected workflow slices. Proposed first vertical slice:

1. Personal account + organization workspace + initial verification state.
2. Standalone and multi-event setup with correct team structures.
3. Membership/invitations and scoped permissions.
4. Task ownership/deadline/progress/evidence/review.
5. Native registration model and individual check-in, including team registrations.
6. Post-event report and closure checklist.
7. Program-level roll-up for child-event status.
8. External registration adapter after provider/access feasibility is proven; exact initial release placement to be approved in delivery planning.

The team must not commit to a provider integration or full offline behavior merely because it appears in the long-term product direction.

## 9. Success metrics

No baselines or improvement claims currently exist. Define the measurement method before pilot testing.

| Metric | Definition | Baseline/target status |
|---|---|---|
| Setup time | Elapsed time from beginning event setup to the defined ready state for a representative event | Baseline required; no target approved |
| Task accountability | Share of active tasks with an owner and deadline | Baseline required; target to be set after workflow review |
| Overdue task visibility | Number/share of overdue tasks visible to authorized leads before escalation | Baseline required |
| Check-in throughput | Successful individual check-ins per minute under defined conditions | Measure using synthetic/test data and realistic scenario |
| Check-in accuracy | Difference between source registrations and verified individual attendance, with corrections accounted for | Define precise rules before pilot |
| Review turnaround | Time between proof submission and authorized decision | Baseline required |
| Close-out time | Elapsed time from event end until required report/evidence items are complete | Baseline required |
| Program visibility | Ability to show child-event status without double-counting or data leakage | Acceptance-test based |
| Adoption/usability | Completion rate and observed friction in representative workflow tests | Measure; do not fabricate |

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| The all-in-one UI becomes overwhelming | Different standalone/program journeys, role-specific views and user testing |
| Incorrect tenant/scope authorization | Deny-by-default server checks and negative authorization tests |
| Registration duplicates/conflicts | Stable external IDs, idempotent import, review ambiguous matches and audit corrections |
| Internet failure disrupts check-in | Clear online-only/degraded states, manual fallback and connectivity testing |
| Task review backlog | Explicit backup reviewer/escalation policy and review queue visibility |
| Evidence file exposure | Private storage, scoped access, format/size validation and retention policy |
| Leadership changes break access | Separate person records and membership; controlled administrator transfer/recovery |
| Scope/delivery growth | Phased vertical slices, acceptance gates and re-estimation after provider/stack decisions |
| Metrics mislead | Definitions, baselines and source traceability before claims |

## 11. End-to-end acceptance scenarios

- **AT-001 Standalone lifecycle:** create standalone event, departments, invite a lead, add members, assign deadline-specific tasks, submit file/link proof, review/reject/approve, use registration/check-in and complete close-out.
- **AT-002 Multi-event program:** create a parent program with at least two child events and shared departments, assign event leads and coordinators, preserve event-level tasks/registrations/reports, show basic cross-event directory, enforce scope boundaries.
- **AT-003 Registration import:** repeated import is idempotent, stable provider identifiers are preserved, ambiguity is reviewed, failure is visible/recoverable, no merge solely based on email.
- **AT-004 Check-in integrity:** valid, unknown, duplicate, walk-in, corrected/voided, and concurrent check-in attempts yield correct/auditable outcomes.
- **AT-005 Permission boundaries:** equivalent roles receive intended equal capabilities; users cannot self-elevate; cross-scope access is denied; directory access does not expose private details.
- **AT-006 Proof-gated completion:** submission is not completion; authorized review required; no self-approval; rejection reason and notification retained.
- **AT-007 Close-out:** mandatory report/evidence omissions block closure unless a permitted, audited exception is used; totals reconcile to source records.
- **AT-008 Connectivity:** failure states are honest; manual fallback is documented; offline functionality is only claimed after offline/reconciliation tests pass.
- **AT-009 Onboarding/invitation:** separate personal account/workspace, invitation bound to email/scope, existing account acceptance, duplicate membership prevention, safe expiry/revocation and delivery failure handling.
- **AT-010 Role change/leadership transition:** tenure-record edits do not silently grant or remove membership; transfer/recovery rules preserve history.

## 12. Delivery and implementation readiness

The delivery plan is a separate companion document: `CampusOps_Delivery_Plan_v1.1.md`. FPC-01–FPC-05 are approved. Implementation should not start until:

- The consolidated PRD, technical specification and delivery plan have been reviewed together.
- The approved organization-verification, initial-admin, attendee-information and MFA/recovery policies are implemented and tested for the affected slice; Supabase Auth passes feasibility/security evaluation or is replaced through a documented decision; file storage, email, external integration and hosting are selected or safely deferred behind an implementation gate.
- The logical model maps to reviewed uniqueness/foreign key/tenant boundaries.
- API endpoints/operations have acceptance tests tied to requirements.
- The first implementation slice is small, end-to-end and approved by the founder.
- No provider, architecture or release behavior is described as verified until an actual technical check/test has occurred.

## 13. Decision and change control

- This PRD is the consolidated source of product intent and approved foundational policy.
- The technical specification translates the PRD into proposed architecture and data/API behavior; it does not silently override product decisions.
- New founder decisions update the decision log and relevant requirement IDs.
- If a requirement changes, record impact on roles, data, API, tests, delivery sequence and privacy/security.
- A feature is not “done” until its acceptance criteria, security/privacy tests and failure states pass.
- No prototypes or application implementation are authorized by this document alone.

## 14. Supporting artifacts and traceability

This PRD consolidates and supersedes overlapping working drafts for product-intent purposes. Older artifacts remain useful as detailed design history but should not independently override this document.

- Requirements baseline: `CampusOps_Requirements_Specification_v0.9.md`
- Permission detail: `CampusOps_Role_and_Permission_Matrix_v0.1.md`
- Logical data model: `CampusOps_Data_Model_and_Relationship_Map_v0.1.md`
- API design baseline: `CampusOps_API_Contract_Draft_v0.2.md`
- Architecture options: `CampusOps_Architecture_Decision_Record_v0.2.md`
- Founder approvals: FA-001 through FA-009 and FPC-01 through FPC-05 in `CampusOps_Decision_Log_v1.3.md`

## 15. Version history

| Version | Change |
|---|---|
| 1.0 | Consolidates product vision, founder workflows, scope/exclusions, functional/NFR requirements, approved foundational decisions, acceptance tests, metrics, risks and readiness gates. Records FA-001–FA-009 as approved. |
| 1.1 | Records founder approval of FPC-01–FPC-05: passive read-only attendee information; organization verification process; initial Primary Workspace Administrator; Supabase Auth as preferred candidate pending feasibility/security evaluation; and MFA/account-recovery policy. Updates onboarding, scope and implementation-readiness language. Does not authorize implementation. |
