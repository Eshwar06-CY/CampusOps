# CampusOps — Requirements Specification

**Version:** 0.2  
**Status:** Working draft — preferences incorporated; validation and implementation decisions remain open  
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

## 7. Validation plan before implementation

1. **Scenario walkthroughs:** Model a standalone workshop and a multi-event E-Week-style program using the same requirement set.
2. **Registration data test:** Use synthetic records to test native registration, an external import, duplicate matching, conflicting edits, failed sync, check-in and attendance reconciliation.
3. **Permission matrix:** List roles against specific actions and test equivalent-authority roles without assuming a fixed title hierarchy.
4. **Attendee assistance walkthrough:** Test public information, a submitted request, assignment, response, resolution, and restricted data access.
5. **Competitor task-level review:** Compare the steps needed to complete the same workflows in selected competitors, based on verifiable documentation or hands-on access if available.
6. **Prioritization review:** Decide which end-to-end workflow should be implemented first; update the requirement priorities and decision log based on evidence.

## 8. Definition of Ready for implementation planning

The specification is ready to move into implementation planning only when:
- Critical user journeys are agreed for standalone and program workflows.
- The role/permission model and data boundaries are documented.
- The initial external registration integration and source-of-truth rules are selected, or explicitly deferred from the first release.
- The attendee information and assistance process has defined ownership and privacy boundaries.
- Acceptance criteria for the first end-to-end workflow are testable.
- Security, registration integrity, recovery, and testing expectations are documented.
- The delivery scope is realistic for the founder's time and academic commitments.

**Current status:** Requirements draft updated to reflect preliminary preferences. No code has been generated and no implementation-ready architecture has been approved.
