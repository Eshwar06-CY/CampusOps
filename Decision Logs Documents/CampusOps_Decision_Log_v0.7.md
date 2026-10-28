# CampusOps — Product Decision Log

**Version:** 0.7  
**Status:** Current working log; confirmed directions separated from recommendations.  
**Working mode:** Product planning and documentation only.

## Confirmed product direction

1. CampusOps supports event preparation, backend operations, event-day registration/coordination, and post-event documentation.
2. Marketing campaign management, promotional activity tracking, poster/reel creation, and social publishing are out of scope.
3. Participant-facing doubts/questions/issue raising is out of scope. Any staff-only operational blocker feature must be clearly internal and must not become a participant support ticketing module.
4. CampusOps supports standalone events and multi-event programs. Their setup and team structures differ but can share core operational concepts.
5. Organizations use workspaces; each office bearer and team member has an individual account. No shared club login.
6. Standalone workflow: event departments are defined and department leads are assigned. Leads manage their department's members/tasks within granted permissions. Office bearers/core members can assign work to leads or coordinators.
7. Multi-event workflow: one program contains multiple event records; departments are common across the program; leads are assigned to individual events; coordinators are assigned to departments and specific work. There are no department leads by default.
8. Tasks require explicit deadlines and progress tracking. Proof-required completion requires a file/link submission and authorized review; rejection must keep the task non-completed, include a note, preserve history, and notify the responsible person.
9. Workspace members can view members across the other events in the workspace. Exact visibility of email/contact details remains unconfirmed.
10. Registration can be native or integrated with an external source. Team and solo registrations must still lead to individual participant verification and check-in.
11. Post-event records cover event details, registration and attendance, supporting evidence, reports, and closure status.
12. Do not build prototypes, write application code, install dependencies, or implement integrations unless the founder explicitly asks.
13. The user selected an organization workspace with individual accounts and appropriate permissions.

## Recommended defaults, not yet founder-approved

| ID | Topic | Recommended default | Status |
|---|---|---|---|
| FWD-001 | Proof review | Authorized reviewer within scope; submitter cannot approve their own evidence; rejected evidence retains history and sends a note/notification. | Proposed |
| FWD-002 | Role inheritance | Explicit role-based permissions with organization/program/event/department/task scope. Parent permissions do not automatically extend to private child-event data. | Proposed |
| FWD-003 | Team registration | Separate team/group registration from individual participant records; check-in per person per event; idempotent duplicate handling. | Proposed |
| FWD-004 | Roster privacy | Workspace-wide directory shows names, role, department and event assignments; personal email/phone remain restricted by default. | Proposed |
| FWD-005 | Deadline changes | Assigned tasks have a specific date or date-time deadline; authorized changes require a reason, history and notification; assignees request changes. | Proposed |
| O-001 | Review permissions | Give leads default review permission only within their scope, excluding their own submissions; authorized office bearers can be explicit reviewers. | Proposed; needs approval |
| O-002 | Backup reviewer | Define an eligible backup reviewer when the usual reviewer is unavailable or is the submitter. | Proposed |
| O-003 | Roster edits after registration | Allow roster changes under a documented policy; changes after an event-defined cutoff require review and history. | Proposed |
| O-004 | Check-in lookup | Support QR/unique registration identifier and name/search fallback; confirm the actual required methods. | Proposed |
| O-005 | Deadline editing authority | Event creator/authorized office bearer and relevant lead can edit within scope; assignees request changes unless separately granted permission. | Proposed |
| O-006 | Contact visibility | Basic roster visibility is workspace-wide; email/phone visibility is limited to operational need by default. | Proposed; founder decision needed |

## Cross-document reconciliation v0.1

Created `CampusOps_Foundational_Workflow_Reconciliation_v0.1.md` to map founder-confirmed workflow directions and proposed defaults across the requirements specification, role/permission matrix, logical data model, architecture decisions, and acceptance-test gates.

Key reconciliation notes:
- Use scoped role assignments rather than hard-coded single-lead fields.
- Program-level shared departments do not grant implicit access to every child event.
- Proof-required task completion is a server-enforced review transition, not a client-only status toggle.
- Team registration and individual attendance must be separate.
- Directory visibility must not grant private contact, evidence, participant-record, or audit access.
- Deadline changes require history if accountability is to be preserved.
- Keep marketing and participant-facing issue submission out of scope.

## Remaining decision gates

### Gate A — Before API contracts and physical schema

- Reviewer authority, self-review prohibition, backup review flow.
- Role inheritance and program/event/department scopes.
- Participant fields, team roster changes, check-in lookup and duplicate handling.
- Workspace roster fields versus private contacts.
- Deadline edit permissions, date-only/date-time semantics and time zones.
- Proof-required rule and exact task state transitions.

### Gate B — Before selecting providers/integrations

- First external registration integration and sync direction.
- Authentication/email/notification providers.
- File storage, evidence retention and size/type controls.
- Hosting budget/region, backups and restore requirements.
- Offline/degraded-connectivity check-in policy.

### Gate C — Before pilot

- Organization/program/event/department authorization tests.
- Evidence review, rejection and self-approval tests.
- Team roster, duplicate/concurrent check-in, and external-import replay tests.
- Private file and participant-data access tests.
- Retention/export/deletion policy, backups and restore verification.
- Event-day fallback procedure.

## Change log

| Version | Change |
|---|---|
| 0.7 | Added reconciliation of confirmed product behavior, proposed workflow defaults, document-level corrections, and readiness gates. No implementation decision was made. |
