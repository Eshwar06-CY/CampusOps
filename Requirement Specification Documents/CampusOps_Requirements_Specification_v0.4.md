# CampusOps — Requirements Specification

**Version:** 0.4  
**Status:** Working draft — includes release strategy, end-to-end acceptance scenarios, updated decision register, and pilot readiness gates; validation remains open  
**Product:** Event Operations Management SaaS  
**Scope:** Pre-event preparation, backend operations, event-day execution, registration/check-in, attendee assistance, and post-event documentation.  
**Explicit exclusion:** Marketing campaign management, promotional execution, poster/reel creation, and social media publishing.

## 1. Product direction

CampusOps is intended to help organizations plan, coordinate, execute, and document events in one connected workspace. It should support standalone events (such as workshops, seminars, and hackathons) and multi-event programs (such as college festivals), without requiring every user to operate a complex festival workflow.

The product vision is comprehensive. Requirements in this draft describe desired capabilities; they do not mean that all capabilities must be delivered in the first release.

## 2. Preliminary preferences incorporated in v0.2

| ID | Preference | Draft interpretation | Status |
|---|---|---|---|
| D-001 | Native registration and external integrations | CampusOps should provide native registration forms and participant records, while also supporting selected external registration sources. | Direction accepted; providers and sync behavior open |
| D-002 | Configurable roles and permissions | Organizations can configure roles and permissions, including equivalent authority for roles that have the same responsibilities. | Direction accepted; permission model to be designed |
| D-003 | Attendee assistance includes information and tracked requests | Attendees should be able to find approved event information and submit requests that can be assigned and tracked by staff. | Direction accepted; support workflow and response expectations open |
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
- Tasks can have a title, description, owner(s), status, deadline, priority, and optional dependencies.
- Invalid dates and invalid dependency cycles are rejected or prevented.
- Relevant users can see their own tasks; authorized leads can see tasks within their scope.
- Overdue and blocked tasks are identifiable.

#### CO-FR-006 — Record progress and blockers (P0)
- Authorized users can add dated progress updates and mark tasks blocked, in progress, completed, or in another defined status.
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

### E. Event-day operations and attendee assistance

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

#### CO-FR-017 — Publish approved event information (P0/P1 to be confirmed)
**User story:** As an attendee, visitor, participant, or guest, I need to find reliable information for the event I am attending.

**Acceptance criteria:**
- Authorized event staff can publish approved information such as schedule, venue/directions, rules, session details, and designated help contacts.
- Public/attendee-facing information is separated from internal notes, participant lists, staff-only instructions, and other restricted data.
- Authorized users can update information; the current approved version is distinguishable from drafts or superseded information.
- The attendee-facing experience works on common mobile screen sizes.
- Information required for safety or access must not rely solely on an untested integration or a notification that may not be delivered.

#### CO-FR-018 — Submit and track attendee assistance requests (Product requirement; first-release priority to be validated)
**User story:** As an attendee, I need to ask for help; as a coordinator, I need requests routed to an appropriate person and tracked through resolution.

**Acceptance criteria:**
- An attendee can submit a request through a supported channel without being given access to internal operations records.
- A request can have a category, description, status, assigned team/member, and timestamps.
- Authorized staff can claim or assign the request, update status, communicate a suitable response, and record resolution.
- Unassigned and unresolved requests are visible to authorized staff.
- Personal details are limited to what is needed to resolve the request; public access cannot browse other attendees' requests.
- The system communicates only response expectations that the event team has actually configured and can support.
- A process exists for urgent or safety-related requests; the product must not imply emergency-service replacement.

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
- Important assignments, approvals, schedule changes, and attendee requests can trigger configurable notifications where justified.
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
| CO-SEC-006 | Safe public information boundaries | Verify that attendee information pages and assistance channels never expose internal notes or other attendees' information. |

Quantitative service targets, retention durations, backup recovery objectives and exact performance limits remain open; they must be set before production use based on risk and expected volume.

## 5. Risks and mitigations

Likelihood and impact below are preliminary assessments, not measured probabilities.

| ID | Risk | Likelihood / impact | Proposed mitigation and decision gate |
|---|---|---|---|
| CO-R-001 | Integration scope expands to too many external registration tools | High / High | Choose the first supported provider based on target-user evidence. Define supported operations explicitly; do not promise universal compatibility. |
| CO-R-002 | Duplicate, stale, or conflicting registration records across native and external systems | High / High | Define a source of truth per field, stable source IDs, idempotent imports, conflict review, and clear sync status. Test with synthetic conflicting records before real event use. |
| CO-R-003 | Configurable roles become too difficult to understand or secure | Medium-High / High | Start with a small set of templates plus controlled customization. Use permission scopes and least privilege; require tests for privilege escalation and equivalent-role behavior. |
| CO-R-004 | Separate standalone and program workflows duplicate features or diverge | Medium / High | Separate the user journeys but prefer shared underlying event concepts/services. Run the same acceptance tests against both paths. Revisit the model only if evidence supports a different architecture. |
| CO-R-005 | Attendee requests are missed, misrouted, or treated as urgent without suitable handling | Medium / High | Define categories, ownership, unassigned queues, escalation rules and realistic response expectations. Establish a separate process for urgent/safety cases. |
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
5. **Attendee access:** Public event page, authenticated attendee portal, QR link, or a limited combination? What information may be visible without sign-in?
6. **Assistance workflow:** Who monitors the request queue, and what event-specific process applies to urgent or unclaimed requests?
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
7. If an attendee needs help, submit a request or direct them to approved event information; authorized staff track the request to resolution.
8. Complete the event report, reconcile registrations against attendance, attach approved evidence, and close required tasks.

**Acceptance checks:**
- A user can create the standalone event without first creating a program.
- Program-level fields and controls do not appear as mandatory steps.
- A registration record is distinguishable from a check-in record.
- An attendee already checked in is clearly identified; duplicate check-in is prevented under concurrent requests.
- Only authorized staff can access internal participant records and assistance notes.
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

### WF-004 — Attendee assistance request

**Scenario:** An attendee needs help finding a room, understanding a schedule change, or resolving a registration issue.

**Primary journey:**
1. The attendee accesses approved event information and, where enabled, submits a request.
2. The request is categorized and routed to an authorized team or queue.
3. Staff claim or assign it, update its status, and communicate a response through a supported channel.
4. The request is marked resolved with a timestamp and appropriate resolution note.
5. Unassigned or unresolved requests remain visible to the authorized operations team.

**Acceptance checks:**
- An attendee cannot browse another attendee's requests or internal staff notes.
- Each request has a status and a visible owner or an explicit unassigned state.
- Urgent/safety-related cases follow a clearly defined escalation procedure; CampusOps is not presented as an emergency-services replacement.
- Response-time claims are shown only if the event team has configured and can support them.

### WF-005 — Event-day degraded connectivity

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
| D-010 | Attendee assistance | Include approved event information and a basic tracked request queue in the product design; make channel/notification choices configurable. | Test request routing, staffing ownership, privacy boundaries, and urgent escalation handling. |
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
4. **Attendee assistance walkthrough:** Test public information, a submitted request, assignment, response, resolution, and restricted data access.
5. **Competitor task-level review:** Compare the steps needed to complete the same workflows in selected competitors, based on verifiable documentation or hands-on access if available.
6. **Prioritization review:** Decide which end-to-end workflow should be implemented first; update the requirement priorities and decision log based on evidence.

## 11. Definition of Ready for implementation planning

The specification is ready to move into implementation planning only when:
- Critical user journeys are agreed for standalone and program workflows.
- The role/permission model and data boundaries are documented.
- The initial external registration integration and source-of-truth rules are selected, or explicitly deferred from the first release.
- The attendee information and assistance process has defined ownership and privacy boundaries.
- Acceptance criteria for the first end-to-end workflow are testable.
- Security, registration integrity, recovery, and testing expectations are documented.
- The delivery scope is realistic for the founder's time and academic commitments.

**Current status (v0.3):** User preferences, end-to-end workflow scenarios, recommended defaults, competitor evidence, risks, and decision gates are documented. No code has been generated and no implementation-ready architecture has been approved.

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
8. Provide approved attendee-facing event information and a tracked assistance-request queue, with clear ownership and privacy boundaries.
9. Complete an event report with registration and attendance figures, event details, supporting evidence or evidence links, and closure status.
10. Show a program-level summary across child events while preserving separate event records and explicit aggregation rules.

**Not required for the first pilot unless validated as essential:** broad third-party integration coverage, two-way synchronization, complex finance/procurement, advanced automation, unrestricted custom role builders, full offline check-in, sophisticated analytics, and external notification channels beyond the agreed operational baseline. These remain candidates for later releases, not automatically rejected features.

### 12.2 Implementation slices

| Slice | Goal | Exit condition |
|---|---|---|
| **Slice 0 — Design and feasibility** | Finalize primary workflows, data boundaries, permission matrix, registration-source decision and low-fidelity prototype. | Critical decisions are documented; risky integration and offline assumptions have been tested or explicitly deferred. |
| **Slice 1 — Core event operations** | Implement event setup, teams/roles, task ownership and progress, native registration, check-in, operational issue tracking, attendee information/request flow and close-out record. | The standalone-event acceptance scenario passes from beginning to end. |
| **Slice 2 — Program operations** | Add parent program and child events, shared team members, program summary and aggregation rules. | The multi-event acceptance scenario passes without duplicated records or incorrect totals. |
| **Slice 3 — External registration source** | Implement the first approved external registration integration and recovery/conflict handling. | Repeated imports/synchronizations are idempotent; failure and conflict scenarios pass; integration security is reviewed. |
| **Slice 4 — Operational hardening** | Test real-world volume assumptions, degraded connectivity, accessibility, backup/restore, monitoring and deployment. | Release checklist and critical security/reliability tests pass before real event data is used. |

These are logical slices, not calendar commitments. Schedule them around academic priorities and revise effort estimates after the stack and integration feasibility are known.

## 13. End-to-end acceptance test plan

The following are the proposed minimum acceptance scenarios for the pilot. They should be written as executable automated or repeatable manual tests before a release is called complete.

### AT-001 — Standalone workshop lifecycle

**Given** an authorized organizer and a new workshop, **when** the organizer creates the event, assigns a team, creates tasks, accepts native registrations, checks attendees in, records an issue or assistance request, and completes the event report, **then** all records remain linked to the same event and each workflow is permission-checked.

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

### AT-006 — Attendee information and assistance request

An attendee opens approved event information, submits a request, and receives a response from an assigned staff member.

**Pass conditions:**
- Public information contains no internal-only notes or participant lists.
- The request has a status and an owner or explicit unassigned state.
- Authorized staff can assign, update and resolve it.
- An attendee cannot view another attendee's request or internal staff conversation.
- Urgent/safety cases follow the documented escalation process and do not imply CampusOps replaces emergency services.

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
| D-003 | Event information plus tracked attendee assistance | Direction accepted | Define request categories, request ownership, privacy boundaries and urgent escalation procedure. |
| D-004 | Distinct setup flows for standalone events and multi-event programs | Direction accepted | Keep distinct UX journeys, with shared underlying event concepts by default. |
| D-005 | Standalone vs program setup model | Recommended: distinct setup journeys with shared event concepts/services | Test a workshop and an E-Week-style program; avoid duplicated behavior and accidental cross-event data changes. |
| D-006 | First external registration source | Recommended: investigate Google Forms first | Verify current API access/authorization, response fields, source identifiers, quotas, ownership, and expected update frequency. |
| D-007 | Initial synchronization direction | Recommended: one-way import into CampusOps | Defer write-back/two-way sync until user need, field ownership and conflict resolution are demonstrated. |
| D-008 | Duplicate records and conflicts | Recommended: stable source IDs; ambiguous matches reviewed manually | Define exact matching/correction rules; test repeated imports and conflicting records using synthetic data. |
| D-009 | Role customization scope | Recommended: templates plus bounded overrides | Validate that target teams can model their responsibilities without excessive configuration; test privilege escalation. |
| D-010 | Attendee assistance workflow | Direction accepted; operating policy open | Define assignment, unassigned queue, status transitions, privacy, notification behavior and urgent escalation. |
| D-011 | Offline check-in | Open | Assess venue connectivity and latency tolerance; implement only if the need justifies reliability and reconciliation costs. |
| D-012 | Event closure | Recommended: configured mandatory items and auditable exceptions | Validate which reports/evidence are mandatory for each event type. |
| D-013 | Release sequencing | Recommended: end-to-end slices | Approve first-slice scope only after acceptance scenarios and feasibility checks are reviewed. |
| D-014 | Event evidence storage and retention | Open | Decide whether pilot evidence is uploaded, linked, or both; document access, consent where relevant, retention and deletion policy. |

## 15. Pilot readiness and Definition of Done

The pilot is not ready to use with real attendee data until all applicable points below are completed:

- The standalone and program workflows pass AT-001 and AT-002.
- Registration integrity and check-in scenarios pass AT-003 and AT-004 for every implemented ingestion path.
- Authorization, role equivalence and data isolation tests pass AT-005.
- Attendee information and assistance privacy tests pass AT-006.
- Close-out and audit behavior pass AT-007.
- Any claimed offline capability passes AT-008; otherwise limitations are stated clearly.
- Critical user journeys have actionable loading, empty, validation, failure and recovery states.
- Backups/restoration, data retention/deletion, secret handling, error logging and incident response expectations are documented for the deployment environment.
- No fake customer outcomes, invented efficiency gains or untested production-readiness claims appear in the product or portfolio case study.
- The pilot uses synthetic data until the privacy and security controls for genuine event data have been reviewed.

## 16. Immediate next steps

1. Review and resolve the highest-impact open decisions: external registration method, role customization scope, evidence storage/retention, and offline check-in requirements.
2. Build a low-fidelity clickable workflow prototype for one standalone workshop and one two-event festival. Validate whether the separate setup flows are clear while retaining consistent behavior.
3. Perform technical feasibility checks for the chosen external registration path without building the entire app.
4. Turn AT-001 through AT-008 into a test checklist and map each test to its functional requirements.
5. Only after the workflow and decision gates are reviewed, finalize the initial PRD, data model, architecture decisions, delivery estimate and implementation backlog.

## 17. Status summary

**Current status (v0.4):** The broad product scope, preliminary user preferences, workflow scenarios, requirements, competitor implications, risks, recommended defaults, release slices, acceptance scenarios and readiness gates are documented. The specific external registration implementation, data-retention rules, offline behavior, final permission design, technical architecture and MVP release commitments remain open. No code has been generated by this specification update.
