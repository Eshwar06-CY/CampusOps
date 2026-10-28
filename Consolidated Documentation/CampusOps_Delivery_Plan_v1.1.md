# CampusOps — Delivery Plan v1.1

**Version:** 1.1  
**Status:** Proposed staged plan; calendar dates and effort estimates not yet committed  
**Companion documents:** `CampusOps_PRD_v1.1.md`, `CampusOps_Technical_Specification_v1.1.md`, `CampusOps_Decision_Log_v1.3.md`  
**Current authorization:** Documentation and planning only. This plan does not authorize coding, installs, integrations, or deployment.

## 1. Delivery approach

CampusOps should be delivered as small, reviewable end-to-end slices. The long-term product vision remains comprehensive, but the first release should prove a connected operating workflow rather than shipping isolated screens or every possible module.

The order below is dependency-led, not a fixed calendar schedule. Dates, estimates and provider choices must be revisited after the environment is inspected and the remaining technical decisions are closed. Schedule must remain sustainable alongside the founder's academic work and examinations.

## 2. Proposed release objective

**First connected pilot objective:** An authorized organization can create a standalone event and a multi-event program, invite individuals into appropriately scoped roles, plan tasks with deadlines, submit and review completion evidence, register participants, check each person in individually, and complete event reports. Program summaries must preserve child-event records and correct scoping.

External registration integration may follow the native path after provider feasibility is proven; the product requirement remains native registration plus selected external integrations. Full offline check-in is not promised; the first pilot uses online operation with a documented manual fallback.

## 3. Workstreams and phases

### Phase 0 — Documentation baseline and decision gates

**Objective:** Establish a single source of truth for product behavior before implementation.

**Deliverables:**
- PRD v1.0 and technical specification v1.0 reviewed.
- FA-001–FA-009 recorded as approved.
- FPC-01–FPC-05 are founder-approved: read-only attendee info scope; organization verification; initial Primary Workspace Administrator; Supabase Auth preferred candidate pending feasibility/security evaluation; MFA and account-recovery policy. Remaining provider, storage, email, hosting, retention and external connector decisions are closed or explicitly deferred per the affected implementation slice.
- Requirements-to-test traceability matrix.
- Initial release scope and acceptance criteria.

**Dependencies:** Founder review of consolidated documents.

**Exit criteria:** No conflicting rules in the PRD, role matrix, data model and API contract for task states, permission scopes, individual check-in or external import handling. No coding in this phase.

### Phase 1 — Technical feasibility and environment inspection

**Objective:** Confirm candidate providers and tooling are feasible without building the full product.

**Activities:**
- Inspect the actual repository and development environment before changing files or installing packages.
- Compare managed-auth providers for individual accounts, invitations, verification, recovery, MFA and cost/region.
- Compare PostgreSQL hosting and backup/restore options.
- Validate private evidence storage and controlled file access.
- Evaluate transactional email invite delivery and failure handling.
- Perform a small technical feasibility check for the first external registration source (Google Forms is a candidate) using synthetic data; verify current API permissions/limitations and expected sync direction.
- Define performance/connectivity test scenarios for event-day check-in.

**Deliverables:** Provider evaluation, cost/risk notes, selected or deferred technical decisions, feasibility outcomes, updated technical spec and risk register.

**Exit criteria:** Any provider-dependent feature is either proven feasible, explicitly deferred, or removed from the first slice. No claim of implementation success without a test result.

### Phase 2 — Identity, organization workspace and authorization foundation

**Objective:** Establish the secure organization workspace model.

**Scope:** Public landing page basics; personal account entry; organization/club details; verification state; workspace membership; editable office-bearer/faculty directory; roles and scopes; invite acceptance/revocation/expiry; workspace and member administration; audit foundation.

**Key acceptance tests:**
- No shared club login exists.
- Existing members accept invites without duplicate identity/membership.
- Invited users cannot self-grant a different role/scope.
- Directory/tenure edits do not silently grant/revoke platform access.
- Revoked membership loses access, while historical authored records remain attributed.
- Cross-organization and unauthorized scope access is denied at the server.

**Exit gate:** Critical organization/authorization tests pass before event workflows depend on the identity model.

### Phase 3 — Event structure, teams and planning tasks

**Objective:** Support both event setup journeys and accountable task execution.

**Standalone scope:** Create/edit event; optional venue; define event-specific departments; assign department leads; invite individual members; permit department leads to add members within scope; allow authorized office bearers/core members to assign tasks to leads or coordinators.

**Program scope:** Create program and child events; define shared departments; assign leads to child events; assign coordinators to shared departments and specific work; provide basic workspace-wide directory visibility while restricting private fields and event records.

**Task scope:** Task owners, specific deadline/date-time, event timezone, progress updates, blockers, deadline change request/approval, reassignment and audit.

**Key acceptance tests:** Standalone event does not require a program; program's shared departments do not erase child-event scopes; assignment and permission differences are correct; due date changes are audited and communicated.

### Phase 4 — Evidence submission and task approval

**Objective:** Implement the proof-gated task lifecycle.

**Scope:** File/link evidence submission, versioning, reviewer eligibility, no self-review, assigned backup reviewer/escalation, approve/reject with note, rejection notification, audit history and safe file access.

**Key acceptance tests:**
- Submitted for review is not completed.
- Only a permitted reviewer can approve within scope.
- Submitter cannot approve own evidence.
- Rejection has a reason and remains non-completed.
- Re-review applies to the latest evidence version.
- Unauthorized users cannot access a private evidence file by guessing/altering its URL or identifier.

**Exit gate:** File storage/retention policy and permitted formats must be set before handling real event evidence.

### Phase 5 — Native registration and individual check-in

**Objective:** Complete an end-to-end event day using the native registration model.

**Scope:** Registration form configuration/submission, registration and participant models, solo/team registration, QR/registration identifier, lookup/search fallback, per-person check-in, duplicate/concurrent handling, audited correction/void, configured walk-in policy, registration-versus-attendance counts.

**Key acceptance tests:**
- Team registration creates/references individual participant records.
- A team arriving together still generates individual check-in outcomes.
- Duplicate and concurrent check-ins do not inflate attendance.
- Corrections require authority and reason, and preserve history.
- Unknown/walk-in cases follow event policy and are not falsely represented as verified registrations.

**Exit gate:** Check-in data integrity and staff instructions pass before any real pilot.

### Phase 6 — Event-day view, internal blockers and close-out

**Objective:** Connect planning and event execution with final documentation.

**Scope:** Role-scoped operational view; live status; staff reassignment; internal operational blockers; event report; photos/supporting evidence; registration/attendance reconciliation; mandatory closure checklist; program summaries with defined aggregation.

**Excluded:** Attendee-facing doubt/question/issue submission, marketing campaign work, poster/reel creation and social publishing.

**Key acceptance tests:** authorized staff can identify important open work; blocker records remain internal; report totals trace to source records; event closure exposes omissions; program summary does not merge or silently double-count child-event records.

### Phase 7 — First external registration connector

**Objective:** Add one selected external source only after source access and field mapping are proven.

**Scope:** Provider adapter, auth/permissions, sync run state, stable source identifiers, idempotent imports, conflict review, field ownership/source-of-truth, retries and recoverable failures.

**Key acceptance tests:** replay is idempotent; ambiguous matches are not silently merged; failed sync is visible; tokens are protected; source changes do not overwrite native-owned fields without explicit policy.

**Exit gate:** Provider, access scope, sync direction and quota assumptions are documented. Google Forms remains a candidate until proven.

### Phase 8 — Operational hardening and pilot readiness

**Objective:** Verify safe behavior in realistic conditions before real participant data is used.

**Scope:** Accessibility and responsive testing; security tests; backup/restore exercise; logs/monitoring; secret management; retention/deletion policy; failed provider and check-in scenarios; degraded connectivity and manual fallback; runbook and incident/recovery expectations.

**Exit gate:** All required acceptance tests pass; no critical authorization/data integrity issue remains open; pilot data handling and rollback/manual fallback are approved.

## 4. Proposed backlog epics

| Epic | Contents | Depends on |
|---|---|---|
| E-01 Identity and organization workspace | Personal accounts, workspace, verification state, directory/tenure records | Phase 0–1 decisions |
| E-02 Membership, invitations and roles | Invite token, membership states, scoped roles, audit, member removal | E-01 |
| E-03 Event/program setup | Standalone and parent/child program structures, departments and leads | E-02 |
| E-04 Task management | Owners, status, deadlines, dependencies, progress, reassignment | E-03 |
| E-05 Proof and review | Evidence versions, reviews, rejection and notification | E-04; storage decision |
| E-06 Registration model | Native forms, registrations, participants, solo/team structure | E-03 |
| E-07 Event-day check-in | Scan/lookup, individual check-ins, corrections and attendance counts | E-06 |
| E-08 Operations and blockers | Event-day status, staffing, internal blockers | E-04/E-07 |
| E-09 Close-out/reporting | Report, evidence, checklist, program summaries | E-05/E-07/E-08 |
| E-10 External registration adapter | First provider, sync/conflict handling | E-06 and provider feasibility |
| E-11 Hardening/observability | Security, backups, recovery, accessibility, monitoring | Depends on deployed slices |

## 5. Test strategy and release criteria

Automate critical domain and API rules, then verify the complete user journeys end to end.

Minimum acceptance suite:
1. Standalone workshop lifecycle.
2. Multi-event program with two child events and shared departments.
3. Invite acceptance, expiration, revocation, existing account and duplicate membership.
4. Role equivalence, scope boundaries and cross-organization denial.
5. Task deadline change, proof submission, self-approval denial, approve/reject and re-submission.
6. Solo/team registration and individual check-in.
7. Duplicate/concurrent check-in and audited correction.
8. External import/replay/conflict/provider failure once selected.
9. Post-event report, missing evidence and closure exception.
10. Degraded connectivity, manual fallback and honest pending/failure states.
11. File access control and retention/deletion policy.
12. Backup/restore and recovery check.

A test is passed only when actually executed with a recorded result. A planned test is not a passed test. Synthetic data must be used until privacy/security readiness is approved.

## 6. Project controls

Maintain these artifacts during delivery:
- Product roadmap and prioritized backlog.
- Requirement-to-test traceability matrix.
- Risk register and dependency log.
- Architecture decision record and decision log.
- Sprint goal and lightweight weekly status.
- Definition of Ready and Definition of Done.
- Release checklist, test evidence and retrospective.

### Definition of Ready
A work item is ready when it has a stable requirement/ID, user value, scope, acceptance criteria, permission/data implications, dependencies, error states, test approach and an estimate or explicitly recorded uncertainty.

### Definition of Done
A work item is done only when implementation is reviewed, required tests are executed, authorization/data integrity/error states are checked, accessible UX states exist where relevant, documentation is updated, and no result is claimed without evidence.

## 7. Risks and mitigations

| Risk | Mitigation / trigger |
|---|---|
| Scope creep | Prioritize end-to-end vertical slices; keep marketing and participant issue portal excluded |
| Academic workload pressure | Use flexible milestone cadence; re-estimate after exams and major deadlines; avoid fixed-date commitments until effort is known |
| Unchosen providers delay architecture | Make provider-dependent work conditional; run feasibility checks early |
| Permission mistakes | Test each role and scope through direct API, not UI alone |
| Evidence or participant data exposure | Private storage, minimal fields, scoped access, retention and deletion policy |
| Check-in failure at venue | Manual fallback, staff instructions, connectivity test; no offline promise until verified |
| Cross-event confusion | Separate program and child-event records; clear role scope and context in UI |
| Unreliable metrics | Define baseline and calculation before claiming impact |

## 8. Milestones and sizing

Calendar dates and person-week estimates are intentionally not committed here. They depend on the selected providers, current repository/environment, implementation capacity, integration feasibility and academic schedule. Estimate each phase after those inputs are known; attach an explicit confidence range and buffer to high-risk tasks.

Suggested milestone exit gates:
- **M0:** PRD/technical spec decisions reviewed; requirements traceable.
- **M1:** Identity/workspace and scoped authorization pass tests.
- **M2:** Standalone and multi-event setup and task assignment pass tests.
- **M3:** Proof-gated task review passes tests.
- **M4:** Native registration and individual check-in pass integrity tests.
- **M5:** Close-out and program summary pass tests.
- **M6:** First external connector passes repeat/failure/conflict tests (or is formally deferred).
- **M7:** Security, restore, accessibility and manual fallback readiness reviewed before pilot.

## 9. Governance and authorization boundary

The founder has approved FA-001 through FA-009. Provider choices and several account/organization verification details remain open. This plan is an ordered proposal, not permission to start implementation. Inspect the actual project repository/environment before changing files or installing anything, and begin implementation only after explicit authorization.

## 10. Version history

| Version | Change |
|---|---|
| 1.0 | First consolidated delivery plan based on the PRD, technical proposal and approved foundational decisions. Defines phases, epics, dependencies, tests, risk controls, milestone gates and release readiness. No calendar promise or implementation authorization. |
