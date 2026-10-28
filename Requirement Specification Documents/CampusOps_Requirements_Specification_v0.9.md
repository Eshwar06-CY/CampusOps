# CampusOps — Requirements Specification

**Version:** 0.9  
**Status:** Working requirements draft — adds a recommended organization-verification, invitation, administrator-recovery, and security policy package for founder review; these policy defaults are not confirmed decisions  
**Product:** Event Operations Management SaaS  
**Scope:** Organization onboarding, pre-event preparation and backend operations, team/account management, task deadlines and proof review, event-day execution, native/external registration, individual participant check-in, and post-event documentation.  
**Explicit exclusions:** Marketing campaign management, promotional execution, poster/reel creation, social media publishing, and attendee-facing doubt/request/issue-submission portals. Internal staff operational blockers/issues may remain in scope.

**Current working mode:** Requirements and decision documentation only. Do not create or revise prototypes, frontend screens, application code, installations, or integrations unless the founder explicitly asks for implementation. Existing prototype artifacts from earlier iterations are not evidence that workflows are validated or production-ready.

**Founder-confirmed account/workspace model:** CampusOps has an organization workspace for the college club, and each office bearer, faculty coordinator, lead, coordinator, and other team member who uses the platform has an individual named account with appropriate permissions. There is no shared club login. The first person establishes the organization workspace using their personal account and is proposed to become its Primary Workspace Administrator; the organization workspace itself has no separate password. College/club verification is required by the intended onboarding flow, but the verification method must be defined before implementation. Invited members use or create their own personal accounts, while workspace membership, role, department and event/program scope are separate authorization records. Transfer, recovery, organization-verification and invitation lifecycle policies are documented as proposed defaults in v0.9 and remain subject to review.

## 1. Product direction

CampusOps is intended to help organizations plan, coordinate, execute, and document events in one connected workspace. It should support standalone events (such as workshops, seminars, and hackathons) and multi-event programs (such as college festivals), without requiring every user to operate a complex festival workflow.

The product vision is comprehensive. Requirements in this draft describe desired capabilities; they do not mean that all capabilities must be delivered in the first release.

## 2. Preliminary preferences incorporated in v0.2

| ID | Preference | Draft interpretation | Status |
|---|---|---|---|
| D-001 | Native registration and external integrations | CampusOps should provide native registration forms and participant records, while also supporting selected external registration sources. | Direction accepted; providers and sync behavior open |
| D-002 | Configurable roles and permissions | Organizations can configure roles and permissions, including equivalent authority for roles that have the same responsibilities. | Direction accepted; permission model to be designed |
| D-003 | Attendee information and tracked request workflow | Superseded in v0.5 | Participant-facing doubt/question/issue submission is out of scope; retain registration/check-in and authorized internal operational tracking. |
| D-004 | Separate standalone and multi-event workflows | The interface should offer distinct setup paths for an individual event and a multi-event program. | Direction accepted; recommended to retain shared underlying event concepts and services |

These are preliminary product preferences, not irreversible architecture decisions. They must be tested against usability, security, operational reliability, effort, and the first-release scope.

## 3. Functional requirements

Priority definitions:
- **P0 — Foundation:** must be specified and validated before the first implementation plan is approved.
- **P1 — Next capability:** part of the product direction, but may be phased after the foundational workflow.
- **P2 — Later/conditional:** build only after a validated need and a clear implementation case.

Priority is not a claim that research has proven market demand.

### A. Event workspace and structure

#### CO-FR-001 — Create and edit an event (P0)
**User story:** As an organizer, I need to create an event with the details necessary to plan and run it.

**Acceptance criteria:**
- An authorized organizer can create and edit event name, description, dates/times, venue, time zone, and relevant operational details.
- Required fields are validated; invalid dates/times are rejected with actionable messages.
- A draft can be saved before it is ready to publish or operate.
- The system records creation and relevant updates.

#### CO-FR-002 — Support distinct standalone-event and program workflows (P0)
**User story:** As an organizer, I want a setup flow appropriate to a single event or a program containing multiple events.

**Acceptance criteria:**
- A user can create a standalone event without having to create a parent program.
- A user can create a program/festival and add multiple independently managed events to it.
- The program workflow supports shared overview information while each child event retains its own schedule, team, tasks, registrations, check-ins, issues, and close-out records.
- The interface does not force standalone-event users through program-level setup steps they do not need.
- Program and standalone workflows use consistent shared concepts where appropriate, so similar operations do not behave unpredictably across contexts.
- A parent program's summary does not merge or double-count individual event records without explicit aggregation rules.

**Architecture note:** “Separate workflows” means distinct user journeys and screens where useful. It does not, by itself, require separate databases or duplicated implementations. Prefer shared underlying event concepts unless research proves that a different model is necessary.

### B. Roles, teams, and permissions

#### CO-FR-003 — Configure roles and permissions (P0)
**User story:** As an organization administrator, I need to define access according to our actual responsibilities rather than being forced into a fixed title hierarchy.

**Acceptance criteria:**
- Authorized administrators can assign predefined roles and, within supported limits, configure roles and permission sets.
- Equivalent roles can be granted equivalent permissions even when their titles differ (for example, two lead roles with equal authority).
- Permissions can be scoped appropriately to the organization, program, or individual event.
- The system follows least-privilege principles: users receive only the access necessary for their responsibilities.
- Authorization is enforced server-side for every protected action, not only by hiding UI controls.
- Role or permission changes to sensitive capabilities are recorded in an audit history.
- The system prevents accidental privilege escalation and clearly shows who can grant or change permissions.

#### CO-FR-004 — Organize teams and departments (P0)
**User story:** As an event lead, I need to organize team members into departments and assign responsibilities.

**Acceptance criteria:**
- Authorized users can create departments or functional teams and assign members.
- A person can be assigned to more than one event or team when authorized.
- Each assignment identifies its event/program scope and relevant responsibilities.
- The system can show a person's active assignments so conflicting workloads can be spotted.

### C. Planning and task execution

#### CO-FR-005 — Assign and track tasks (P0)
- Tasks can have a title, description, owner(s), status, specific due date (and optional due time), priority, and optional dependencies. The assignee cannot directly set a proof-gated task to `Completed`; completion requires review approval.
- Invalid dates and invalid dependency cycles are rejected or prevented.
- Relevant users can see their own tasks; authorized leads can see tasks within their scope.
- Overdue and blocked tasks are identifiable.

#### CO-FR-006 — Record progress and blockers (P0)
- Authorized users can add dated progress updates and mark tasks not started, in progress, blocked, or awaiting review. A proof-gated task reaches `Completed` only after an authorized reviewer approves its evidence.
- Blockers can include a description and responsible person when known.
- Leads can review current status and the history of important updates without relying solely on a separate meeting or message thread.

#### CO-FR-007 — Manage approvals (P0)
- Authorized users can mark an item as requiring approval and identify the authorized reviewer or role.
- Reviewers can approve or reject it; a rejection can include a reason.
- The current decision, decision-maker, timestamp, and relevant history are visible to authorized users.
- Only authorized users can make approval decisions.

### D. Registration, participant records, and check-in

#### CO-FR-008 — Provide native registration (P0 capability; release scope to be confirmed)
**User story:** As an organizer, I need to configure registration within CampusOps and maintain the resulting participant records.

**Acceptance criteria:**
- An authorized organizer can configure a registration form with supported required and optional fields.
- Submissions are validated and linked to the correct event.
- Organizers can view, search, and export authorized participant records.
- The system prevents unintended duplicate submissions according to a documented duplicate-handling rule; it does not silently merge people based on uncertain matches.
- Registration status and check-in status are separate concepts.
- Participant data access, retention, export, and deletion follow documented privacy rules.

#### CO-FR-009 — Verify participants and record check-in (P0)
**User story:** As registration staff, I need to verify a participant quickly and reliably at the event entrance.

**Acceptance criteria:**
- Authorized staff can find a participant by a supported identifier and use QR scanning if enabled.
- The result distinguishes valid registration, no matching registration, cancellation/ineligibility where applicable, and already-checked-in status.
- Duplicate check-ins are prevented under concurrent use.
- Authorized staff can resolve an exception through a defined, auditable workflow.
- Each check-in records the event, time, and acting account or operational identity, subject to the system's identity model.
- If a manual override is permitted, its reason and authorizing user are recorded.

#### CO-FR-016 — Integrate selected external registration sources (Product requirement; implementation priority P1 until a provider is chosen)
**User story:** As an organizer, I need to use a supported external registration source when it is already part of my workflow.

**Acceptance criteria:**
- CampusOps documents which external sources and integration methods are supported; unsupported sources are not presented as working integrations.
- Imported or synchronized records retain source identifiers and a timestamp/status indicating when they were last updated.
- Field mapping is explicit; unmapped or invalid records are surfaced for review instead of being silently discarded.
- Repeated imports/sync retries do not create duplicate participant records when a stable source identifier exists.
- Conflicting changes and failed synchronizations are surfaced clearly and can be resolved by an authorized user.
- The system defines the source of truth for each data field and whether the integration is one-way or two-way before enabling synchronization.
- Integration credentials and personal data are protected; access can be revoked.

**Open decision:** The first external source/provider, import versus live sync, one-way versus two-way behavior, and initial-release timing remain undecided. Supporting “both” does not mean promising every provider or full two-way synchronization in the first release.

### E. Event-day operations

#### CO-FR-010 — Display operational status (P0)
- Authorized users can view relevant current tasks, important updates, open issues, and ownership in a shared event-day view.
- The view identifies items needing attention and shows when its data was last updated where timeliness matters.
- Users see only the events and information permitted by their access scope.

#### CO-FR-011 — Coordinate staff reassignment (P0)
- Authorized users can change a coordinator or volunteer's assignment when event-day needs change.
- The updated assignment is visible to affected authorized team members.
- The system records the previous assignment, new assignment, actor, timestamp, and reason when required by policy.
- Reassignment does not silently erase the history or completion state of the original task.

#### CO-FR-012 — Track operational issues (P0)
- Authorized staff can create an issue with a description, status, priority, and owner.
- Issues can be updated and resolved; important transitions are recorded.
- Unresolved and unassigned issues remain visible to the appropriate leads.
- The system does not imply that a request has been handled simply because an acknowledgment was sent.

### F. Post-event documentation and reporting

#### CO-FR-013 — Complete event report (P0)
- An authorized organizer can record the event date, venue, duration, registration count, attendance count, notes, and evidence links/files according to configured policy.
- Registration and attendance counts are distinct and traceable to the underlying records when available.
- If totals differ from system records, the discrepancy can be explained rather than silently overwritten.
- Photo/evidence uploads respect permission, storage, and retention rules.

#### CO-FR-014 — Track event closure (P0)
- Required close-out items have defined completion states and responsible owners where appropriate.
- Missing reports, evidence, and required tasks remain visible.
- Closing an event with mandatory items outstanding requires an authorized exception and recorded reason.

#### CO-FR-015 — Consolidated program reporting (P0 for program workflow; exact reports to be validated)
- Authorized users can view status and completion of child events in a parent program.
- Summary counts identify their aggregation method and avoid accidental double-counting.
- Event-level participant records remain attributable to their specific event.

### G. Supporting capabilities

#### CO-FR-019 — Notifications (P1, provider/channel undecided)
- Important assignments, invitation events, deadlines, proof-review decisions, schedule changes, and operational status changes can trigger configurable notifications where justified.
- Delivery failures and user preferences are handled appropriately.
- Notifications do not expose sensitive participant or operational information to unauthorized recipients.
- Critical state remains available in the application even if a notification is missed.

#### CO-FR-020 — Reusable event templates (P2/conditional)
- An authorized organizer can reuse a prior event's selected structure/checklists without automatically copying outdated dates, personal data, or obsolete rules.
- Copied items are clearly identified for review before they are treated as current.
- Template reuse preserves the historical record of the prior event.

## 4. Non-functional, security, and privacy requirements

| ID | Requirement | Verification approach |
|---|---|---|
| CO-NFR-001 | Responsive and accessible UI | Test key workflows on desktop/mobile, keyboard navigation, labels, focus, contrast, and validation feedback. |
| CO-NFR-002 | Data integrity | Test simultaneous updates, duplicate submissions, retries, invalid transitions, and failed requests. |
| CO-NFR-003 | Useful error handling | Verify loading, empty, success, failure, retry, and offline/connection-loss states. |
| CO-NFR-004 | Operational reliability | Define performance, availability, backup/restore and degraded-network expectations before real event data is used. |
| CO-SEC-001 | Server-side authorization | Test direct API calls with users lacking appropriate permissions. |
| CO-SEC-002 | Tenant/event isolation | Test attempts to access another organization's or event's records. |
| CO-SEC-003 | Personal data minimization | Collect only necessary attendee/staff information; document purpose, access, retention, export and deletion. |
| CO-SEC-004 | Auditability | Verify that relevant role, approval, assignment, check-in override, sync-conflict and issue-resolution changes have attributable history. |
| CO-SEC-005 | Integration security | Protect and revoke credentials; scope permissions; log sync failures without exposing tokens or unnecessary personal data. |
| CO-SEC-006 | Invitation and roster privacy | Verify that invitations are bound to the intended workspace/email/scope and that personal contact details are visible only as permitted by the roster policy. |

Quantitative service targets, retention durations, backup recovery objectives and exact performance limits remain open; they must be set before production use based on risk and expected volume.

## 5. Risks and mitigations

Likelihood and impact below are preliminary assessments, not measured probabilities.

| ID | Risk | Likelihood / impact | Proposed mitigation and decision gate |
|---|---|---|---|
| CO-R-001 | Integration scope expands to too many external registration tools | High / High | Choose the first supported provider based on target-user evidence. Define supported operations explicitly; do not promise universal compatibility. |
| CO-R-002 | Duplicate, stale, or conflicting registration records across native and external systems | High / High | Define a source of truth per field, stable source IDs, idempotent imports, conflict review, and clear sync status. Test with synthetic conflicting records before real event use. |
| CO-R-003 | Configurable roles become too difficult to understand or secure | Medium-High / High | Start with a small set of templates plus controlled customization. Use permission scopes and least privilege; require tests for privilege escalation and equivalent-role behavior. |
| CO-R-004 | Separate standalone and program workflows duplicate features or diverge | Medium / High | Separate the user journeys but prefer shared underlying event concepts/services. Run the same acceptance tests against both paths. Revisit the model only if evidence supports a different architecture. |
| CO-R-005 | Invitation, deadline, or proof-review updates fail to reach the responsible team member | Medium / High | Track invitation state and review outcome in-app; define retry/failure states for email notifications; ensure the application remains the source of truth. |
| CO-R-006 | Participant personal data or internal event information is exposed | Medium / High | Minimize data collection; enforce server-side role/event access; test tenant isolation; define retention and deletion; separate public information from internal records. |
| CO-R-007 | Connectivity problems disrupt check-in or event-day work | Medium-High / High | Research venue connectivity and peak check-in volume. Test degraded-network behavior and define whether offline mode is necessary before selecting an implementation. Do not promise offline operation until verified. |
| CO-R-008 | Duplicate check-ins or concurrent updates create inaccurate attendance | Medium / High | Use atomic/idempotent operations, unique constraints where appropriate, concurrency tests, and an auditable manual-override process. |
| CO-R-009 | The all-in-one goal produces an overwhelming interface | High / High | Use role- and stage-specific views; test a standalone workshop and complex festival; hide irrelevant setup steps without removing capabilities from users who need them. |
| CO-R-010 | Feature scope outgrows the time and academic constraints available | High / High | Separate the long-term product from the first release. Validate the highest-value workflow, estimate work, and phase delivery around academic commitments. |
| CO-R-011 | Post-event metrics are inconsistent or double-count participants across events | Medium / High | Define metric meanings and aggregation rules; keep event-level source records; distinguish registrations, check-ins and unique people. |
| CO-R-012 | External provider changes or API limits break synchronization | Medium / Medium-High | Confirm current API capabilities before choosing providers, handle rate limits/retries, surface failures and maintain an export/recovery path. |

## 6. Decisions still open

1. **External registration source:** Which provider should be integrated first, based on the current workflow of target users?
2. **Sync direction:** Import-only, one-way synchronization, or two-way synchronization for the initial provider?
3. **Identity and duplicate handling:** What identifier is reliable enough to match imported participants without unsafe automatic merging?
4. **Role model:** Which scopes are required at organization, program, event, and team level? Which actions need explicit approval?
5. **Member roster visibility:** Which roster fields (name, role, department, event scope, contact email) are visible to all workspace members, and which require narrower access?
6. **Invitation security:** What invitation lifetime, resend, cancellation, duplicate-account, and email-change rules are required?
7. **Offline operations:** Does the first target environment require check-in to work through an internet interruption, or is a documented degraded-mode process sufficient?
8. **First-release sequence:** Which P0 requirements should be delivered together as a coherent vertical workflow, given available time and technical capacity?
9. **Evidence and storage:** How will photo evidence be stored, who can access it, and how long should it be retained?
10. **Acceptance thresholds:** What baseline and target should be used for setup time, check-in speed, closure time, and unresolved-task visibility?

## 7. End-to-end workflow scenarios

These scenarios test whether the same product vision works for a small standalone event and a complex multi-event program. They are proposed workflow tests, not evidence that a customer problem has been validated.

### WF-001 — Standalone workshop

**Scenario:** One organizer creates a workshop with a small team, registration, a venue, an event-day check-in process, and post-event documentation. No parent program is required.

**Primary journey:**
1. Create a standalone event using a short setup flow.
2. Add event details, an owner, relevant team members, dates, venue, and required operational tasks.
3. Configure native registration or select a supported external registration source.
4. Assign task owners and deadlines; track progress and blockers.
5. Prepare the event-day briefing and check-in process.
6. On the day, authorized staff look up or scan registered attendees, record check-ins, and handle exceptions.
7. Authorized staff execute the event-day runbook, record internal operational blockers, and complete required task/check-in steps. Attendee-facing doubt/request submission is outside the product scope.
8. Complete the event report, reconcile registrations against attendance, attach approved evidence, and close required tasks.

**Acceptance checks:**
- A user can create the standalone event without first creating a program.
- Program-level fields and controls do not appear as mandatory steps.
- A registration record is distinguishable from a check-in record.
- An attendee already checked in is clearly identified; duplicate check-in is prevented under concurrent requests.
- Only authorized staff can access internal participant records and perform check-in overrides.
- Event closure shows missing required documentation and does not silently treat it as complete.

**Measures to collect in a usability test:** setup completion time; number of screens or context switches; task completion rate; check-in lookup time; error/exception handling time; time required to complete the post-event report.

### WF-002 — Multi-event college festival (E-Week-style)

**Scenario:** An organization runs a festival containing multiple events. Office bearers oversee the program; core and sub-core leads have equivalent authority for the responsibilities assigned to them; coordinators and volunteers work across event teams when authorized. Each event has its own details, team, registration, operational issues, and close-out records.

**Primary journey:**
1. Create a parent program and add child events, each with its own dates, venue, schedule, teams, tasks, registration settings, and close-out requirements.
2. Configure program administrators and event-level roles. Give equivalent lead roles equivalent permissions where appropriate, without granting unrelated administrative access.
3. Assign department/team responsibilities and tasks across the program and individual events.
4. Monitor overdue tasks, blockers, and readiness across the program while retaining drill-down into each event.
5. Keep marketing tasks outside CampusOps. Operational preparation may include approved rules, staff briefings, venue/equipment readiness, registration setup, and attendee-support preparation.
6. During event execution, show team members their current assignments. Authorized leads can reassign a coordinator from one event to another; both affected event views must reflect the change and retain the change history.
7. Each event independently records registrations, check-ins, attendance, issues, and evidence.
8. Afterward, each event completes its close-out. The parent program summarizes event status and aggregates figures only according to explicit rules.

**Acceptance checks:**
- A child event can be managed independently while still belonging to a parent program.
- Event-level task, attendee, check-in, issue, and report records remain attributable to the correct event.
- Program dashboards distinguish a child-event status from a program-level summary.
- Reassigning staff does not silently remove historical ownership or leave ambiguous active assignments.
- Users can only manage events and program data within their authorized scope.
- Aggregated registration/attendance reports label their aggregation method and do not automatically treat one person attending multiple child events as multiple unique people unless the metric explicitly counts attendances.
- The same core functions behave consistently in standalone and program workflows, while setup and overview screens differ where useful.

**Measures to collect in a usability test:** time to create the program and child events; time to locate a blocked event; accuracy of identifying who owns a task; time to reassign a coordinator; number of manual duplicate updates; completion rate for event-level and program-level reports.

### WF-003 — Native registration and external registration source

**Scenario:** An organizer can choose native CampusOps registration for a new event or connect a supported existing registration source when the team already uses one.

**Recommended first integration to investigate:** Google Forms, because the described current process uses it. This is a recommendation to test, not a commitment or claim that integration has already been implemented.

**Initial integration boundary to test:** start with a clearly scoped import/synchronization path for registration responses; do not assume two-way editing, form authoring, or real-time synchronization is required for the first integration.

**Acceptance checks:**
- The organizer can identify the connected source and the time/status of the last successful import.
- Imported records retain a stable source identifier when available and map explicitly to CampusOps fields.
- Re-running the same import is idempotent and does not create duplicates for records with the same source identifier.
- Unmapped fields, invalid rows, and conflicts are surfaced for review.
- Integration failure does not silently mark the data as current; a retry can recover without duplicating records.
- The interface makes clear which system is authoritative for each field and whether updates flow one way or both ways.
- A CSV/manual import fallback can be considered if API access or authorization prevents a reliable connection.

**Decision gate:** do not select the long-term synchronization design until the provider's current API capabilities, authorization scopes, quotas, recovery behavior, and the target user's actual need for live updates have been checked.

### WF-004 — Event-day degraded connectivity

**Scenario:** Network connectivity becomes slow or unavailable during check-in.

**Required discovery:** determine the likely venue connectivity, registration volume, device availability, and operational tolerance for delay before deciding whether offline check-in is a first-release requirement.

**Acceptance checks to define after the decision:** the system communicates connectivity status; staff do not mistake stale data for current data; duplicate check-ins and conflicts are addressed; any offline records synchronize with a clear conflict/recovery policy after reconnection.

**Decision gate:** offline check-in is not to be promised until a concrete design and concurrency/reconciliation tests demonstrate its reliability.

## 8. Recommended defaults and decision gates

These defaults are recommendations for the draft. They remain open until the relevant workflow and technical feasibility checks are complete.

| Decision ID | Area | Recommended default to evaluate | Why / gate before commitment |
|---|---|---|---|
| D-005 | Standalone vs program setup | Provide two distinct setup journeys and dashboards, backed by shared event concepts and services where appropriate. | Test a workshop and an E-Week-style program; reject needless duplicated logic. |
| D-006 | First external registration integration | Investigate Google Forms first, with import-first scope and native registration kept as the preferred fully supported workflow. | Verify API permissions, form ownership/access, response fields, quotas, user consent, and sync-failure handling. |
| D-007 | Sync direction | Default the first external integration to one-way import into CampusOps; defer write-back/two-way sync. | Avoid conflicting edits and ambiguous field ownership until a user need justifies added complexity. |
| D-008 | Duplicate records | Use stable provider IDs when available; treat uncertain matches as review cases rather than automatically merging people. | Test repeated imports, name/email variations, shared emails where possible, and manual correction. |
| D-009 | Role configuration | Start with reusable role templates and limited permission customization, not an unrestricted permission builder. | Validate whether target teams need arbitrary custom roles; security tests must cover privilege escalation. |
| D-010 | Attendee-facing requests | Removed from scope in v0.5 | Keep registration/check-in and internal team operations; do not provide an attendee question/request portal. |
| D-011 | Offline check-in | Treat as an explicit feasibility decision, not an assumed initial feature. | Test venue connectivity and event scale; compare online-only, degraded-mode, and true offline requirements. |
| D-012 | Event closure | Use configurable required close-out items and explicit exception handling. | Validate which reports/evidence are mandatory for different event types. |
| D-013 | Long-term scope vs initial release | Preserve the broad product vision but plan delivery as tested end-to-end slices. | Confirm each release slice has acceptance tests and is achievable alongside academic commitments. |

## 9. Competitive evidence and product implications

The official product documentation below shows why CampusOps cannot claim uniqueness simply because it combines event tasks, registration, check-in, budgets, or reporting.

- **Planning Pod:** its official features page describes event timelines and schedules, budgets, registration/ticketing, attendee management and check-in, vendor management, tasks, checklists, workflow automation, templates and reporting. This is evidence that broad event-workflow integration is already offered in the market. [Planning Pod features](https://planningpod.com/features) (reviewed 28 October 2026).
- **Cvent OnArrival:** Cvent documents attendee lookup, barcode scanning, walk-in registration, check-in reporting and offline check-in after an event is selected/downloaded while online; its documentation also notes that syncing and certain operations still require connectivity. This makes offline operation a concrete requirement to evaluate rather than a differentiator to assume. [Cvent OnArrival documentation](https://support.cvent.com/articles/en_US/Topic_Hub/Meet-Our-OnArrival-Check-In-App) and [offline FAQ](https://support.cvent.com/articles/en_US/FAQ/Does-OnArrival-work-without-internet) (reviewed 28 October 2026).
- **Google Forms API:** official documentation lists methods for reading forms and listing/getting responses, along with authorization requirements and usage limits. This supports investigating a Google Forms integration, but does not make it a turnkey or already-working CampusOps feature. [Forms API reference](https://developers.google.com/workspace/forms/api/reference/rest) and [usage limits](https://developers.google.com/workspace/forms/api/limits) (reviewed 28 October 2026).

**Competitive interpretation:** treat “easier connected workflow for the intended team” as a hypothesis to measure. Do not claim that a competitor lacks a capability unless current, relevant evidence supports that statement. A feature gap is meaningful only if target users care about it and the proposed workflow solves it better.

## 10. Validation plan before implementation

1. **Scenario walkthroughs:** Model a standalone workshop and a multi-event E-Week-style program using the same requirement set.
2. **Registration data test:** Use synthetic records to test native registration, an external import, duplicate matching, conflicting edits, failed sync, check-in and attendance reconciliation.
3. **Permission matrix:** List roles against specific actions and test equivalent-authority roles without assuming a fixed title hierarchy.
4. **Invitation and role walkthrough:** Test organization account setup separately from invited personal accounts, role confirmation, invitation expiry/cancellation policy, and scoped permissions.
5. **Competitor task-level review:** Compare the steps needed to complete the same workflows in selected competitors, based on verifiable documentation or hands-on access if available.
6. **Prioritization review:** Decide which end-to-end workflow should be implemented first; update the requirement priorities and decision log based on evidence.

## 11. Definition of Ready for implementation planning

The specification is ready to move into implementation planning only when:
- Critical user journeys are agreed for standalone and program workflows.
- The role/permission model and data boundaries are documented.
- The initial external registration integration and source-of-truth rules are selected, or explicitly deferred from the first release.
- Invitation acceptance, personal-account access, and team roster/contact visibility have defined ownership and privacy boundaries.
- Acceptance criteria for the first end-to-end workflow are testable.
- Security, registration integrity, recovery, and testing expectations are documented.
- The delivery scope is realistic for the founder's time and academic commitments.

**Historical status snapshot (v0.3; superseded by Section 21):** At that earlier revision, user preferences, end-to-end workflow scenarios, recommended defaults, competitor evidence, risks, and decision gates were documented. The current status is summarized in Section 21.

## 12. Release strategy: preserve the vision, deliver tested workflow slices

CampusOps remains an all-in-one event-operations product in its long-term vision. Phasing the implementation is a delivery strategy, not a reduction of the product goal. The initial release should prove that a connected operational workflow works reliably from preparation through event closure, rather than presenting a broad but incomplete set of modules.

### 12.1 Proposed first end-to-end pilot: Connected Event Operations

**Objective:** Demonstrate that an organizer can configure an event, coordinate assigned work, manage registrations and attendance, handle operational issues, and complete a close-out record in CampusOps. The underlying model must also support a parent program containing multiple events.

**Required pilot capabilities to validate:**

1. Create and edit a standalone event using a focused setup flow.
2. Create a parent program and add at least two independently managed child events using a distinct program setup flow.
3. Add team members and assign supported role templates with scoped permissions. Allow equivalent authority where intended; unrestricted custom permission construction is not assumed for the first pilot.
4. Create tasks, owners, deadlines, statuses, progress updates and blockers; record approvals where configured.
5. Offer native registration and a check-in workflow that detects unknown participants and duplicate check-ins.
6. Support one external registration source as a launch requirement only after the integration feasibility gate is passed. Google Forms is the first candidate because it matches the founder's current workflow. The recommended first API design to evaluate is one-way ingestion into CampusOps with explicit source identifiers, conflict handling and sync status. Do not promise live synchronization until tested. If API integration proves infeasible, a CSV/import fallback must be explicitly approved as a temporary pilot scope; it must not be described as a live integration.
7. Show an event-day operations view with assigned responsibilities, unresolved issues and current status.
8. Provide a role-specific team operations view and clear ownership of internal blockers; do not include an attendee-facing request portal.
9. Complete an event report with registration and attendance figures, event details, supporting evidence or evidence links, and closure status.
10. Show a program-level summary across child events while preserving separate event records and explicit aggregation rules.

**Not required for the first pilot unless validated as essential:** broad third-party integration coverage, two-way synchronization, complex finance/procurement, advanced automation, unrestricted custom role builders, full offline check-in, sophisticated analytics, and external notification channels beyond the agreed operational baseline. These remain candidates for later releases, not automatically rejected features.

### 12.2 Implementation slices

| Slice | Goal | Exit condition |
|---|---|---|
| **Slice 0 — Design and feasibility** | Finalize primary workflows, data boundaries, permission matrix, registration-source decision and written acceptance walkthroughs. Do not create a prototype unless explicitly requested. | Critical decisions are documented; risky integration and offline assumptions have been tested or explicitly deferred. |
| **Slice 1 — Core event operations** | Implement account/onboarding shell, event setup, team invitations/roles, task ownership and deadlines, proof-gated completion, native registration, individual check-in, staff-only operational blockers where validated, and close-out record. | The standalone-event acceptance scenario passes from beginning to end. |
| **Slice 2 — Program operations** | Add parent program and child events, shared team members, program summary and aggregation rules. | The multi-event acceptance scenario passes without duplicated records or incorrect totals. |
| **Slice 3 — External registration source** | Implement the first approved external registration integration and recovery/conflict handling. | Repeated imports/synchronizations are idempotent; failure and conflict scenarios pass; integration security is reviewed. |
| **Slice 4 — Operational hardening** | Test real-world volume assumptions, degraded connectivity, accessibility, backup/restore, monitoring and deployment. | Release checklist and critical security/reliability tests pass before real event data is used. |

These are logical slices, not calendar commitments. Schedule them around academic priorities and revise effort estimates after the stack and integration feasibility are known.

## 13. End-to-end acceptance test plan

The following are the proposed minimum acceptance scenarios for the pilot. They should be written as executable automated or repeatable manual tests before a release is called complete.

### AT-001 — Standalone workshop lifecycle

**Given** an authorized organizer and a new workshop, **when** the organizer creates the event, assigns a team, creates tasks, accepts native registrations, checks attendees in, records internal operational blockers where applicable, and completes the event report, **then** all records remain linked to the same event and each workflow is permission-checked.

**Pass conditions:**
- The organizer can create and save a draft without creating a program.
- Team members see the tasks and information permitted for their roles.
- A valid participant can be checked in once; a second check-in is identified.
- Registration and attendance totals are separately reported.
- Open issues and mandatory close-out items remain visible until resolved or explicitly excepted.

### AT-002 — Multi-event college festival

**Given** a parent festival with at least two child events, **when** an organizer assigns separate teams, shares selected staff across events, records event-specific registrations and progress, and reviews the program, **then** the program summary aggregates status without collapsing event-level control.

**Pass conditions:**
- Each child event has its own schedule, tasks, registrations, check-ins, issues and close-out record.
- An authorized shared coordinator can have different scoped assignments across child events.
- Updating one event does not accidentally modify the other event's records.
- Program totals show their aggregation method and do not silently double-count attendees.
- A standalone event can still be created without the program workflow.

### AT-003 — External registration import/synchronization

**Given** registrations from the approved external source, **when** CampusOps ingests them repeatedly, receives a changed record, or encounters a failed synchronization, **then** the process remains traceable and recoverable.

**Pass conditions:**
- Stable source identifiers prevent duplicates on retries.
- Ambiguous matches are sent for review rather than silently merged.
- Invalid or unmapped fields are visible to an authorized operator.
- Failed synchronization is not presented as successful or current.
- Source-of-truth rules and integration access are visible in the technical documentation.

### AT-004 — Check-in exceptions and concurrency

Test a valid participant, an unknown participant, a duplicate check-in, a cancelled/ineligible participant where applicable, and two staff members attempting to check in the same person concurrently.

**Pass condition:** The system records at most one successful check-in per participant per event unless an authorized, auditable correction procedure is used.

### AT-005 — Role and permission boundaries

Create two lead roles with equivalent authorized powers, a check-in operator, a coordinator and a user with no membership in the relevant event. Attempt both normal UI actions and direct API calls.

**Pass conditions:**
- Equivalent roles have equivalent permissions for the defined operations.
- Users cannot gain extra rights by changing UI values or making direct requests.
- Event- and organization-scoped records remain isolated.
- Sensitive permission changes and selected operational overrides are attributable in audit history.

### AT-006 — Proof-gated task completion and review

A coordinator updates a task, submits a file or link as proof, and waits for an authorized lead/core member to review it.

**Pass conditions:**
- A task requires a specific deadline and responsible assignee.
- Submitting evidence moves the task to `In review`, not directly to `Completed`.
- An authorized reviewer can approve or request changes with a note.
- Approval marks the task `Completed`; rejection leaves it non-completed, records the note, and notifies the assignee.
- The evidence reference, reviewer, decision, and timestamps remain traceable.

### AT-007 — Event closure and evidence

An organizer attempts to close an event with a missing required report or evidence item, then completes the item and tries again.

**Pass conditions:** Mandatory omissions remain visible; closure is blocked or requires a permitted exception with a reason; final registration and attendance values remain traceable and distinguishable.

### AT-008 — Degraded connectivity decision test

Before committing to offline check-in, test representative venue conditions and event volume, including latency, temporary disconnection and recovery. If offline mode is implemented, additionally test concurrent devices, local record protection, synchronization conflicts and duplicate prevention.

**Pass condition:** The product communicates stale/failed connectivity honestly and never represents unconfirmed check-ins as successfully synchronized. True offline support is only claimed after the complete reconciliation tests pass.

## 14. Updated decision register

The decision IDs below continue the IDs already introduced in Sections 2, 6, and 8. **Direction accepted** means the product intent is known; **Recommended** means a default is proposed but not approved; **Open** means evidence or an explicit decision is still required.

| Decision ID | Decision | Current status | Recommended next action |
|---|---|---|---|
| D-001 | Native registration plus selected external registration sources | Direction accepted | Keep native registration in scope; choose and validate one initial external source. |
| D-002 | Configurable roles and equivalent authority where required | Direction accepted | Start with reusable role templates plus bounded permission customization; validate against a permission matrix before designing an unrestricted role builder. |
| D-003 | Participant-facing question/issue workflow | Superseded in v0.5 | Keep attendee question/request submission out of scope; preserve registration/check-in and staff-only operational blockers. |
| D-004 | Distinct setup flows for standalone events and multi-event programs | Direction accepted | Keep distinct UX journeys, with shared underlying event concepts by default. |
| D-005 | Standalone vs program setup model | Recommended: distinct setup journeys with shared event concepts/services | Test a workshop and an E-Week-style program; avoid duplicated behavior and accidental cross-event data changes. |
| D-006 | First external registration source | Recommended: investigate Google Forms first | Verify current API access/authorization, response fields, source identifiers, quotas, ownership, and expected update frequency. |
| D-007 | Initial synchronization direction | Recommended: one-way import into CampusOps | Defer write-back/two-way sync until user need, field ownership and conflict resolution are demonstrated. |
| D-008 | Duplicate records and conflicts | Recommended: stable source IDs; ambiguous matches reviewed manually | Define exact matching/correction rules; test repeated imports and conflicting records using synthetic data. |
| D-009 | Role customization scope | Recommended: templates plus bounded overrides | Validate that target teams can model their responsibilities without excessive configuration; test privilege escalation. |
| D-010 | Attendee-facing request portal | Removed from scope in v0.5 | Keep this distinct from registration/check-in and internal team operations. |
| D-011 | Offline check-in | Open | Assess venue connectivity and latency tolerance; implement only if the need justifies reliability and reconciliation costs. |
| D-012 | Event closure | Recommended: configured mandatory items and auditable exceptions | Validate which reports/evidence are mandatory for each event type. |
| D-013 | Release sequencing | Recommended: end-to-end slices | Approve first-slice scope only after acceptance scenarios and feasibility checks are reviewed. |
| D-014 | Event evidence storage and retention | Open | Decide whether pilot evidence is uploaded, linked, or both; document access, consent where relevant, retention and deletion policy. |

## 15. Pilot readiness and Definition of Done

The pilot is not ready to use with real attendee data until all applicable points below are completed:

- The standalone and program workflows pass AT-001 and AT-002.
- Registration integrity and check-in scenarios pass AT-003 and AT-004 for every implemented ingestion path.
- Authorization, role equivalence and data isolation tests pass AT-005.
- Proof-based task completion and review tests pass AT-006.
- Close-out and audit behavior pass AT-007.
- Any claimed offline capability passes AT-008; otherwise limitations are stated clearly.
- Critical user journeys have actionable loading, empty, validation, failure and recovery states.
- Backups/restoration, data retention/deletion, secret handling, error logging and incident response expectations are documented for the deployment environment.
- No fake customer outcomes, invented efficiency gains or untested production-readiness claims appear in the product or portfolio case study.
- The pilot uses synthetic data until the privacy and security controls for genuine event data have been reviewed.

## 16. Immediate next steps

1. Review and resolve the highest-impact open decisions: external registration method, role customization scope, evidence storage/retention, and offline check-in requirements.
2. Review the written end-to-end workflow walkthroughs for one standalone workshop and one two-event festival. Validate whether the separate setup flows and roles are unambiguous; this is a requirements review, not a prototype build.
3. Perform technical feasibility checks for the chosen external registration path without building the entire app.
4. Turn AT-001 through AT-008 into a test checklist and map each test to its functional requirements.
5. Only after the workflow and decision gates are reviewed, finalize the initial PRD, data model, architecture decisions, delivery estimate and implementation backlog.

## 17. Founder workflow requirements added in v0.5

This section records the more detailed workflow supplied by the founder after reviewing prototype v0.1. It is part of the working specification; technical implementation remains unapproved. Requirements below use new IDs to preserve the earlier document's history.

### CO-FR-021 — Personal account and organization workspace onboarding (P0)
**User story:** As a club representative, I need to establish an organization workspace through my own individual account, while every other person uses their own account as well.

**Acceptance criteria:**
- The public landing page presents product information and distinct **Create your account** and **Log in** actions.
- The first-time setup collects the creator's name, personal email, password and confirmation, plus the college/institution name and club/organization name. The user identity and organization profile are separate records.
- The user's email is verified before the account is treated as verified. Organization/club verification is also required before event workspace creation; the exact verification method (for example, institutional approval or a documented manual process) remains an open decision.
- After the required verification steps, the creator signs in and completes the editable office-bearer/faculty-coordinator directory. The creator is proposed to become the initial Primary Workspace Administrator.
- The organization workspace has no separate shared login or club password. Every person authenticates through their own individual account.
- Invited leads/coordinators use an existing personal account or create one with their own name, invitation-bound email and password. Their access is granted through a separate workspace membership with role and scope; they do not use the inviter's credentials.
- Passwords are never stored in plaintext. Production requires secure authentication, email verification, session handling, password recovery, rate limiting and abuse protection. Any demo behavior, if explicitly requested, must be labelled simulated.

**Proposed admin-continuity default:** Keep at least one active Primary Workspace Administrator; prompt the organization to designate a second trusted administrator after setup, but do not block initial onboarding solely because a second administrator is not yet available.
### CO-FR-022 — Editable club leadership and faculty directory (P0)
**User story:** As a club administrator, I need to maintain the current office bearers and faculty coordinator as tenures change.

**Acceptance criteria:**
- The onboarding profile records office bearer names, positions and emails, plus faculty coordinator name, email and department/role where applicable.
- Authorized administrators can add, edit, and remove records after onboarding.
- Changes do not silently transfer account access or delete historical task approvals/ownership. Account membership and leadership directory are separate concepts.
- A production implementation records relevant changes with actor and timestamp.

### CO-FR-023 — Invitation lifecycle and personal account creation (P0)
**User story:** As an authorized inviter, I need to invite a team member by email and bind that invitation to the correct workspace, role, department and event/program scope.

**Acceptance criteria:**
- An invitation records invitee name and email, inviting user, organization workspace, assigned role, department where applicable, event/program scope, creation time, expiry, and status.
- Invitations use secure, unpredictable, expiring tokens bound to the intended email, workspace, role and scope. Tokens are single-use; acceptance, cancellation, or replacement invalidates the prior token.
- **Proposed default expiry:** seven calendar days. The final configurable policy can be decided before implementation; this duration is not yet founder-confirmed.
- If the invitee does not have a CampusOps account, they can create one using their personal name, invitation-bound email and password, verify the email, review and acknowledge the assigned role, and accept the invitation. If they already have an account, they sign in and accept without creating a duplicate account.
- The invitation presents the role and scope assigned by the inviter. The invitee cannot self-grant a more privileged role or expand event/program access. They may request a correction; an authorized inviter must update and reissue the invitation.
- Authorized users can cancel or resend a pending invitation and view `Pending`, `Accepted`, `Expired`, `Cancelled` and `Revoked` states. Resending creates a replacement token and invalidates the previous link; cancellation/revocation prevents later acceptance.
- Duplicate pending invitations to the same email and same scope are prevented or explicitly reconciled. A pending invitation's email, role or scope cannot be silently changed without invalidating the old token and notifying the intended person.
- Invitation acceptance must not occur until the intended account has authenticated and the email binding is satisfied. Email delivery failure is visible and does not falsely mark the invitation accepted.
- Expired, cancelled, revoked, already-used, mismatched-email and wrong-workspace links produce clear recovery instructions without exposing sensitive workspace details.
### CO-FR-024 — Standalone event setup and department leads (P0)
**User story:** As a club administrator, I want a direct setup flow for one event, with a lead for every department.

**Acceptance criteria:**
- The organizer selects **Standalone event** and enters an editable event name, required date, calculated day-of-week label, optional venue, and participation format (solo, team, or either).
- The venue can be left blank during setup and updated later.
- The organizer adds the departments needed for this event and enters one department lead name/email for each department.
- Saving creates the workspace and pending personal-account invitations for the department leads.
- After acceptance, a department lead can add members to that department within the standalone event scope.
- Office bearers and core members can add coordinators and assign work to department leads or directly to coordinators.
- Standalone setup does not require parent-program fields or program-wide event-lead assignments.

### CO-FR-025 — Multi-event program setup and shared departments (P0)
**User story:** As a program organizer, I need to set up several events together, share common departments and assign event leads.

**Acceptance criteria:**
- The organizer selects **Multi-event program**, enters a program name and adds at least two child events.
- Each child event has its own editable name, required date, optional venue and participation format.
- The setup defines one shared department list used by all child events; the multi-event setup does not create a separate lead for each shared department.
- An event lead is assigned to each child event. A lead may have more than one event assignment when the inviter intentionally grants that scope.
- Office bearers/core members, and event leads within their authorized event scope, can invite coordinators and assign each coordinator to a shared department and one or more permitted events.
- Authorized users can edit events, event-lead assignments, shared departments and team scopes after creation.
- Workspace members can view the workspace roster across child events (member identity, role, department and event scope). Task editing, approvals, participant records and other sensitive operations remain permission-scoped; visibility of personal contact details must follow a documented policy.
- Program summaries preserve child-event records and do not accidentally combine separate registration/check-in records.

### CO-FR-026 — Edit team members and workspace details (P0)
**User story:** As an authorized workspace administrator, I need to maintain membership and edit event setup after initial creation.

**Acceptance criteria:**
- The people view supports adding, viewing, editing and removing members where the user's role permits it.
- Editing can update permitted details such as name, invitation email while pending, role, department and event scope; changes are validated against the editor's permission and the workspace type.
- A multi-event workspace does not allow department-lead roles under the initial model; it uses event leads and department-scoped coordinators.
- Editing a member's scope cannot silently leave active tasks assigned outside that member's scope; the system blocks the change or clearly requires reassignment.
- Event names, dates, venue and participation format remain editable after workspace creation.

### CO-FR-027 — Deadline-based task assignment and proof-gated completion (P0)
**User story:** As an organizer/lead, I need to assign specific deadlines; as a coordinator, I need to submit proof; as a reviewer, I need to accept or return that proof.

**Acceptance criteria:**
- Task creation requires a title, event, department, responsible member and a specific due date. Missing deadlines are not silently accepted.
- Office bearers/core members may assign work to leads or directly to coordinators. Department/event leads may assign work only within their permitted department/event scope.
- The responsible member can update progress (at minimum, not started and in progress) and submit a file or link as completion evidence.
- Evidence submission changes the task to `In review`; it does not mark the task completed automatically.
- Authorized leads/core members can approve the proof or request changes with a note. The exact reviewer scope is defined by the permission matrix; approvals are auditable.
- Approval changes the task to `Completed`. If proof is rejected, the task remains non-completed and returns to its prior non-completed working state; the rejection note is recorded and the responsible member is notified. If the task was not in progress before submission, the system preserves its prior non-completed state where appropriate.
- The task retains proof reference, submitter, submission timestamp, reviewer, decision, decision note, and decision timestamp.
- If a task's assignee, department or event scope changes, the system validates assignment consistency and flags or blocks invalid combinations.

### CO-FR-028 — Solo/team registration and individual member verification (P0)
**User story:** As registration staff, I need to verify every person attending, even when registration was submitted as a team.

**Acceptance criteria:**
- Each event declares its participant format: solo, team, or either.
- Native registration is supported in the product direction, with supported external registration/import paths handled under CO-FR-016.
- For solo registration, each person has an individual participant record and check-in state.
- For team registration, each team has a team identity and every team member has an individual participant record linked to that team.
- At the venue, staff verify each member individually. Checking in one team member does not automatically check in the rest of the team.
- The UI shows members verified versus remaining for each team, while reporting both individual attendance and any derived team-completion state clearly.
- Duplicate check-in is prevented; unknown or mismatched entries are handled via an authorized exception path.
- Attendance counts reconcile to individual check-in records and remain attributable to the relevant event.

### CO-FR-029 — Marketing and attendee-request exclusions (P0 scope boundary)
- CampusOps does not provide marketing campaign management, promotional visit tracking, poster/reel creation, or social media publishing.
- CampusOps does not provide a public attendee-facing portal for raising doubts, questions, or issues. Remove the previously proposed attendee-facing information/request module and related prototype navigation.
- Registration and check-in remain in scope because they are event-operational workflows.
- Staff-only internal blockers/issues may be retained if useful to event operations; they are not a participant-facing submission channel.


### CO-FR-030 — Workspace administrator transfer, member status and access removal (P0)
**User story:** As an organization, we need to maintain control of the workspace when office bearers change, without shared credentials or loss of historical accountability.

**Acceptance criteria:**
- The initial creator becomes the initial Primary Workspace Administrator only after the applicable account and organization verification gates pass.
- The workspace always has at least one active administrator. The system blocks removal/demotion of the last administrator unless an authorized transfer/recovery flow first establishes another active administrator.
- A transfer can only be made to an existing, active, verified member of the same organization workspace. The proposed recipient must explicitly accept the transfer; the current administrator must confirm it when they still have access.
- After transfer, the system records who initiated it, the previous and new administrator, timestamp, and outcome. Historical tasks, approvals, evidence decisions and other audit records remain attributed to the person who performed them.
- If the current administrator has lost access, recovery must verify both control of the individual account/email and the organization's legitimacy using a documented recovery procedure. A claimed club name alone is not sufficient proof.
- Membership states include at least `Invited`, `Active`, `Suspended` and `Removed`. Removing a person revokes their access to that workspace and its scopes but does not delete their personal CampusOps account or historical actions.
- Updating the office-bearer/faculty directory does not automatically grant or revoke workspace permissions. An authorized administrator must separately update the person's membership/role when a real access change is required.
- The application records relevant membership, role and administrator-transfer changes in an audit history.

**Proposed default:** Use a Primary Workspace Administrator plus other explicitly authorized administrators. Encourage a second administrator for continuity. Exact recovery verification and whether transfer requires a two-person approval in all cases remain open.

### CO-FR-031 — Personal account recovery and membership separation (P0)
**User story:** As a team member, I need to recover my personal account securely without using a shared club credential; as an administrator, I need to remove workspace access without deleting the person's wider account.

**Acceptance criteria:**
- Password reset is available through a verified account recovery channel and does not reveal whether arbitrary email addresses have accounts.
- Personal account identity is distinct from membership in any one organization. One person may participate in multiple organizations through the same personal account, with a separate role and scope for each.
- Revoking a membership prevents future access to that workspace and invalidates that user's active authorization for the workspace; it does not automatically remove memberships in unrelated organizations.
- Rejoining after removal requires a new authorized invitation or membership grant; old invitation links cannot restore access.
- A member changing their personal email must verify the new address. An accepted workspace membership is not silently transferred to a different email identity.
- High-impact operations (administrator transfer, role elevation, invitation scope expansion and sensitive roster access) require explicit authorization and must be auditable. Stronger controls such as multi-factor authentication for administrators should be evaluated before production deployment.

### Account and invitation lifecycle — recommended state flow (v0.8)
1. **Creator signup:** Create a personal account → verify its email → submit college/club details → complete the defined organization-verification step → activate the organization workspace with the creator as initial Primary Workspace Administrator.
2. **Invite:** An authorized member selects a person, role and scope → system sends a scoped invitation → invitee signs in or creates a personal account → invitee acknowledges the assigned role → invitation is accepted → scoped membership becomes active.
3. **Role/scope change:** Authorized administrator changes the membership/role/scope → system validates permissions and records the change → notify the affected member; require acknowledgement/acceptance again when access is materially expanded.
4. **Leadership tenure change:** Update the editable leadership directory and separately review workspace memberships/roles → transfer administrator duties where required → preserve historical action attribution.
5. **Member departure:** Suspend or remove the workspace membership → revoke access to that workspace → retain required audit history and records according to the retention policy.

**Not yet finalized:** Organization verification evidence/process, invitation expiry configurability, email changes for pending invites, emergency administrator recovery, admin MFA requirements, and whether role/scope changes always require member re-acceptance.
## 18. Updated decisions and risks from v0.5

| ID | Decision / risk | Current position | Remaining validation / mitigation |
|---|---|---|---|
| D-015 | Organization workspace with individual named accounts; no shared club login | Confirmed by founder | Every human actor uses an individual account; organization membership, role and event/program scope determine authorization. Still define session management, verification, recovery, account linking, initial workspace administrator and ownership transfer. |
| D-016 | Invitation token behavior | Open | Define token entropy, expiry, single-use semantics, cancellation, resend, email change and duplicate-account handling. |
| D-017 | Standalone team model | Direction accepted | Each department has a department lead; lead can add members within that department; office bearers/core members can manage wider team assignments. Validate permission boundaries. |
| D-018 | Multi-event team model | Direction accepted | Common department list; event-specific leads; coordinators assigned by department and permitted event scope; no department-lead role in this path. Validate multi-event lead scope and shared-staff reassignment. |
| D-019 | Task completion proof workflow | Direction accepted | Agree accepted proof types, file limits, link safety, review scope, reviewer conflicts, resubmission and notification failure handling. |
| D-020 | Participant verification granularity | Direction accepted | Every team member has an individual check-in record. Define team registration data model and reconciliation rules. |
| D-021 | Participant-facing questions/issues | Removed from scope | Keep operational staff workflows distinct; do not reintroduce a public request portal without a new scope decision. |
| CO-R-013 | Account types or invitations are confused | Medium / High | Make the organization account and personal invite flow visually distinct; bind invitations to the intended workspace, email, role and scope. |
| CO-R-014 | Incorrect team/department/event assignments create unauthorized access or orphaned tasks | Medium / High | Validate assignment scope on the server; test edits, removals and cross-event reassignment; block or require resolution for orphaned assignments. |
| CO-R-015 | Proof review is bypassed or rejected work appears complete | Medium / High | Enforce state transitions server-side, keep tasks non-completed until approval, and audit all proof decisions. |
| CO-R-016 | Team registration creates an all-or-nothing attendance record | Medium / High | Store/check in each person individually; aggregate to team completion only as a derived state; test partial check-in and concurrency. |

## 19. Updated acceptance scenarios

### AT-009 — Organization signup, verification and personal invitation accounts

**Scenario:** A person creates their own named account and establishes an organization workspace, completes required verification, maintains office-bearer/faculty details, creates an event and invites a department/event lead. The invitee follows the invitation and creates or links their own personal account.

**Pass conditions:**
- The initial registrant uses individual credentials; the club does not have a shared password used by multiple people.
- Organization signup captures college and club details and verifies the required account/contact information before the workspace is treated as verified.
- The club leadership profile can be edited after onboarding.
- Invited members authenticate with their own accounts, separate from organization details.
- The invitation identifies the intended workspace, role, department and event/program scope; acceptance grants membership within that scope and does not allow privilege escalation.

### AT-010 — Standalone and multi-event team setup

**Scenario:** Create one standalone event and one two-event program.

**Pass conditions:**
- Standalone setup collects event details, departments and a lead for each department; invitations are created for those leads.
- Multi-event setup collects each event's details, applies one shared department list, and assigns a lead to each child event.
- Multi-event setup has no department-lead assignment step.
- Coordinators can be assigned to departments and permitted events after creation.
- All workspace members can see the roster across program events while operational permissions remain scoped.
- Names, dates, venues, participation formats, departments and member assignments can be edited by authorized users.

### AT-011 — Task deadline, evidence, approval and rejection

**Scenario:** An authorized user creates a task with a specific due date and assigns it to a coordinator. The coordinator submits proof; a reviewer approves it or requests changes.

**Pass conditions:**
- Task cannot be created without a responsible member and specific deadline.
- Submission requires a file or link and moves the task to `In review`.
- Approval alone marks the task `Completed`.
- Rejection leaves the task non-completed, records reviewer feedback and creates a notification for the responsible person.
- Reassignment or scope changes do not leave invalid owner/event/department combinations.

### AT-012 — Solo and team check-in

**Scenario:** Check in a solo participant and a registered team with multiple members, including a partial check-in where one teammate has not arrived.

**Pass conditions:**
- Every person has a distinct participant/check-in record.
- Checking in a team member updates that person only.
- Team status reflects verified count versus total members and does not claim full check-in while anyone remains unverified.
- Duplicate check-in is rejected/recognized.
- Unknown or mismatched people are not silently treated as registered.

### AT-013 — Participant request exclusion and internal issue distinction

**Scenario:** Review all navigation, registration and event-day flows.

**Pass conditions:**
- No attendee-facing question/doubt/issue submission portal is exposed.
- Registration, check-in and authorized staff-only operational blocker tracking remain available where implemented.
- No public user can access internal team records through a hidden or direct route.

## 20. Requirements and implementation readiness gates

This document is a requirements artifact, not an instruction to build a prototype or application. The founder has explicitly clarified that workflow descriptions are intended to communicate product requirements; no further prototypes, application code, setup commands, or implementation should be initiated unless explicitly requested.

Before implementation is considered ready to plan, the following requirements must be documented and reviewed:

1. **Public entry and organization onboarding:** landing page purpose, create-account/login paths, organization signup fields, email verification, login, and recovery expectations.
2. **Editable leadership directory:** office bearers and faculty coordinators can be added, updated, and removed by authorized users as tenures change; historical task attribution is preserved.
3. **Personal team accounts and invitations:** invitations bind a member's email, intended role, department and event/program scope; invitees create their own accounts rather than using the organization's credentials. Invitation expiry, cancellation, resend, existing-account, email-change, and duplicate-invitation behavior is specified.
4. **Standalone workflow:** editable event name, date/day-of-week display, optional venue, participation format, configurable departments, one department lead per department, and authorized team-member additions.
5. **Multi-event workflow:** create a program and child events, use one shared department list, appoint event leads rather than department leads, assign coordinators by department and permitted event(s), and allow workspace members to see the cross-event roster under documented privacy rules.
6. **Task assignment and proof review:** each task has an event, department, responsible person and specific deadline; authorized roles can assign work within scope; completion requires evidence and approval; rejection leaves the task non-completed, records a note, and notifies the responsible person.
7. **Registration and individual check-in:** each event declares solo/team/either participation; every team member has an individual record and check-in; checking in one team member never checks in all teammates.
8. **Scope boundaries:** marketing and attendee-facing doubt/question/issue submission remain excluded. Internal staff-only task blockers can remain where they support event operations.
9. **Risk decisions:** implement the confirmed organization-workspace/individual-account model; finalize role-permission boundaries, invitation security, workspace-administrator transfer, proof-storage/retention rules, first external-registration integration and synchronization policy, and offline-check-in expectations before architecture is finalized.
10. **Acceptance plan:** map AT-009 through AT-013 and the earlier acceptance scenarios to requirements; record test results only after actual tests are executed.

No item above should be described as implemented merely because the acceptance criteria have been documented.

## 21. Proposed organization, invitation, and recovery policies for review (v0.9)

**Status:** Recommendations for founder review, not confirmed product decisions. These proposals are intended to make the existing requirements actionable without starting implementation.

### 21.1 Organization verification

**Proposed default:** Separate verification of the person's email ownership from verification that the college/club workspace represents a legitimate organization.

1. The creator creates a personal named account and verifies control of the email address using a single-use, time-limited verification token.
2. The creator submits the college name, club/organization name, and a small set of supporting details. Suggested details: an official college/club webpage or public reference where available, and the faculty coordinator's name and institutional contact where applicable. Do not require a college-domain email in every case because some legitimate student organizers may not have one.
3. The workspace remains `Pending verification` until an approved verification path is completed. The creator may be allowed to sign in to view verification status or correct the submission, but event workspace creation and invitations remain disabled until verification succeeds.
4. For an early pilot, support a documented manual review path; additionally evaluate faculty-coordinator confirmation as a lower-friction path. Do not build a broad automated verification service until the pilot shows it is needed.
5. A reviewer records `Approved`, `Needs information`, or `Rejected`, a decision timestamp, and an internal reason. The user receives a clear status and next step; internal review notes are not exposed by default.
6. Re-verification is required for a material organization identity change (for example, changing to a different college or transferring the workspace to a different organization), not for ordinary edits to an event or leadership directory.

**Acceptance criteria:** personal email verification does not by itself mark the organization as verified; unverified workspaces cannot send team invitations or create active event workspaces; review decisions are auditable; there is a correction/appeal path; and verification requests are rate-limited to prevent abuse.

**Still to decide:** whether faculty-coordinator confirmation is mandatory, whether a public reference is mandatory, who performs manual review during the pilot, and what evidence is acceptable when a club has no public page.

### 21.2 Invitation lifecycle

**Proposed default:** Use a secure, single-use invitation bound to the invitee's email, organization workspace, role, and permitted department/event/program scope. Expire the invitation after **7 calendar days** unless the founder chooses a configurable or different policy.

- The invitee sees the workspace and assigned role/scope before accepting.
- The invitee may sign in to an existing personal account or create a new personal account. A second account must not be created just because the person joins another workspace.
- The invitee cannot grant themselves additional permissions. If the role or scope is wrong, they can request correction from the inviter/administrator.
- Resending creates a new valid invitation and invalidates the earlier token; cancelling an invitation prevents later acceptance.
- Expired links show a helpful message and an authorized inviter can issue a replacement.
- Email delivery failure is tracked as `Delivery failed` or equivalent, and the inviter can retry without creating multiple active invitations.
- Invitation tokens are not logged in plaintext and are invalid after use, cancellation, or expiration.

**Acceptance criteria:** an invite cannot be accepted by a different email identity; a token cannot be replayed; an expired/cancelled token cannot grant membership; and membership permissions are assigned server-side from the invitation record, not from user-editable form values.

**Still to decide:** whether the seven-day expiry is fixed or configurable, and whether a materially expanded role/scope always requires the member to accept again.

### 21.3 Primary workspace administrator and continuity

**Proposed default:** The initial creator becomes the Primary Workspace Administrator only after required organization verification. Workspace roles remain separate from current office-bearer directory entries.

- Encourage the organization to designate a second active administrator after onboarding; do not force a second administrator before a tiny organization can complete initial setup, but surface the continuity risk until one exists.
- Do not permit ordinary removal or deactivation of the only active administrator without completing a transfer or recovery path.
- Transfer to another active, email-verified workspace member requires the current administrator to initiate the transfer and the recipient to explicitly accept it.
- Transfer does not rewrite previous action attribution. Historical tasks, approvals and audit records continue to identify the people who performed those actions.
- After transfer, the former administrator's role is changed or removed separately; transfer does not silently grant permanent access to the former administrator.
- Leadership tenure changes update the directory and membership/permissions as separate operations. Changing a person's title alone must not silently grant or revoke account access.

**Acceptance criteria:** no normal UI path leaves a verified workspace with zero active administrators; an administrator transfer is logged and accepted by the recipient; historical records remain attributable; and the system notifies relevant parties of the transfer.

### 21.4 Lost administrator access and account recovery

**Proposed default:** Use personal-account recovery for password or login loss; use a separate organization recovery process only when the current administrator cannot be reached or no active administrator remains.

- Password reset uses a cryptographically random, single-use, time-limited token; the application does not automatically sign the user in after reset.
- Recovery responses must not disclose whether an email address is registered. Reset requests are rate-limited.
- Organization recovery requires independent evidence of authority over the workspace. Possible evidence can include confirmation from an already verified faculty coordinator or review by an authorized CampusOps support reviewer against previously established organization evidence. A claimed club name or access to a newly added email alone is insufficient.
- A recovery decision records the reviewer/actor, evidence type, decision, time and affected workspace. Sensitive evidence is access-controlled and retained only as long as necessary under the future retention policy.
- On suspected compromise or successful high-risk recovery, revoke outstanding reset/invitation tokens as appropriate, review active sessions, and notify the established account/workspace contacts through a safe channel.
- If evidence is insufficient, the system does not transfer ownership automatically; it provides a documented escalation path.

**Acceptance criteria:** ordinary password reset never changes workspace ownership; a person cannot take over a workspace solely by claiming to be a new office bearer; a recovery transfer requires documented review and audit; and old recovery tokens or active sessions cannot silently retain authority after a confirmed compromise.

### 21.5 Strong authentication for high-impact operations

**Proposed default:** Before handling real participant data in production, require re-authentication for high-impact actions and support multi-factor authentication (MFA) for workspace administrators. Decide whether MFA must be mandatory for all workspace administrators before production launch; do not require MFA for every volunteer account by default without evaluating usability and provider capabilities.

High-impact actions include primary-administrator transfer, recovery, privilege elevation, changing authentication email, and access to particularly sensitive records. Authorization must still be checked server-side on every request; MFA does not replace permission checks.

**Acceptance criteria:** a recently authenticated, authorized actor is required for defined high-impact actions; administrator MFA enrollment and recovery are documented; role/permission checks cannot be bypassed from the client; and security-sensitive events are logged without recording passwords, raw tokens, or full verification URLs.

### 21.6 Security basis and source-derived guidance

The detailed implementation controls should be checked against current security guidance during architecture and implementation planning. OWASP recommends email ownership verification before account activation, time-limited single-use verification/reset tokens, secure account-recovery flows, generic responses to avoid account enumeration, and deny-by-default authorization enforced for protected actions. Sources reviewed on 28 October 2026:

- [OWASP Email Validation and Verification Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Email_Validation_and_Verification_Cheat_Sheet.html) — email ownership verification, single-use/time-limited tokens, email-change safeguards, rate limiting and avoiding account enumeration.
- [OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html) — secure reset tokens, recovery safeguards, session considerations and non-enumerating responses.
- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) — deny-by-default access and permission validation for every protected request.

These sources support the security controls, but they do not determine CampusOps-specific choices such as seven-day invitation expiry or the accepted evidence for verifying a college club. Those remain product decisions.

### 21.7 Decision checklist for founder review

| Decision | Recommended default | Status |
|---|---|---|
| Personal email verification | Required before account activation | Proposed; not yet confirmed |
| Organization verification | Separate from personal email; manual review for pilot, with faculty confirmation evaluated | Proposed; verification evidence and reviewer remain open |
| Unverified workspace access | Allow sign-in to view/correct status; block invitations and active event creation | Proposed |
| Invitation expiry | Seven calendar days; single-use and bound to email/workspace/role/scope | Proposed; fixed vs configurable remains open |
| Existing personal account | Sign in and accept invitation; do not create duplicate identity | Proposed |
| Initial workspace administrator | First creator becomes Primary Workspace Administrator after organization verification | Proposed |
| Administrator continuity | Encourage a second admin; block ordinary removal of the last admin | Proposed |
| Ownership transfer | Current admin initiates; recipient explicitly accepts; preserve history | Proposed |
| Emergency organization recovery | Separate, reviewed process requiring independent evidence and audit | Proposed; service-review process remains open |
| MFA | Support MFA for workspace admins; require re-authentication for high-impact actions; decide mandatory MFA before production | Proposed; final launch policy open |

## 22. Status summary

**Current status (v0.9):** The founder-defined workflow is recorded as a working requirements specification. It covers public landing and organization onboarding, editable office-bearer/faculty details, personal invited accounts, distinct standalone and multi-event team structures, task deadlines, proof-gated completion, solo/team registration with individual check-in, and the exclusion of marketing and participant-facing request submission.

**Not yet approved or validated:** detailed permission matrix, organization verification method, invitation expiry/configurability and recovery edge cases, administrator transfer and emergency recovery, exact role/scope-change acknowledgement rules, accepted proof types and file/link limits, first external registration provider and synchronization direction, evidence retention, offline-check-in expectations, technical architecture, delivery estimates, and first-release commitment. The organization workspace with individual named accounts and no shared club login is confirmed product direction. v0.8 and v0.9 add proposed account, invitation, organization-verification, and recovery policies; those detailed defaults are recommendations, not yet founder-confirmed.

**Implementation status:** This update creates and revises documentation only. It does not build or modify a prototype or application code, install dependencies, connect integrations, or verify production behavior. Earlier prototype files may exist from prior iterations, but they are not the current task and are not evidence of validated or production-ready functionality.

## 23. Version history

| Version | Summary |
|---|---|
| 0.5 | Captured detailed founder workflow requirements for organization onboarding, invitations, standalone and multi-event team structures, proof review, and individual check-in. |
| 0.6 | Reaffirmed documentation-only working mode; made the organization-workspace versus shared-login question explicit; corrected task state language so proof-gated tasks cannot be marked complete before approval; replaced prototype-dependent readiness language with requirements and implementation decision gates. |
| 0.7 | Confirmed the organization workspace model with individual named accounts for every office bearer and team member; removed the shared club login as an unresolved identity choice; clarified onboarding and acceptance-test wording. |
| 0.8 | Added proposed primary-administrator continuity, invitation expiry/reissue, existing-account acceptance, member removal, recovery and historical-attribution defaults; these are recommended policies pending founder review. |
| 0.9 | Added a proposed organization-verification, invitation, administrator-continuity, recovery, and high-impact authentication policy package, with OWASP references and explicit founder decision gates. No policy defaults are marked confirmed. |
