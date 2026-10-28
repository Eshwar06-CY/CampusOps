# CampusOps — Foundational Workflow Decision Matrix

**Version:** 0.1  
**Status:** Recommendations for founder review — not yet approved  
**Purpose:** Resolve the permission and workflow questions that must be defined before the requirements and data model can be finalized.  
**Working mode:** Documentation only. This document does not authorize prototype or application implementation.

## 1. Decision summary

| ID | Decision area | Recommended default | Status |
|---|---|---|---|
| FWD-001 | Task-proof approval | A different, explicitly authorized reviewer approves proof within the correct event/department scope; no self-approval. | Proposed |
| FWD-002 | Role and permission inheritance | Permission grants are role-based and scope-bound. Inheritance across organization → program → event → department is explicit, not automatic. | Proposed |
| FWD-003 | Solo/team registration model | Keep a registration/group record separate from individual participant records; attendance is always recorded per person per event. | Proposed |
| FWD-004 | Workspace roster privacy | All workspace members can see basic roster fields across the workspace; email/contact details are limited to operationally relevant roles and scopes. | Proposed |
| FWD-005 | Task deadline changes | An active/assigned task needs a specific deadline. Authorized owners/leads may revise it with a reason, history and notification; assignees request changes rather than silently changing deadlines. | Proposed |

These choices are recommendations based on the founder's described workflows. They are not treated as confirmed until the founder approves or modifies them.

## 2. FWD-001 — Proof review and approval authority

### Proposed policy

1. A task that requires proof cannot enter `Completed` until an authorized reviewer approves the current evidence submission.
2. The submitter cannot approve their own submission, even if they hold multiple roles.
3. **Standalone event:** the assigned Department Lead may review proof for tasks within their department if review permission is granted. An office bearer or core member may also review if explicitly authorized for that event/task scope.
4. **Multi-event program:** the assigned Event Lead may review proof for tasks in that event if review permission is granted. An office bearer or core member may review within their explicitly authorized program/event scope.
5. Review authority does not automatically extend to every department or child event because a person is a lead somewhere in the workspace.
6. Rejection changes the task to `Changes Requested` (or another defined non-completed state), requires a reviewer note, preserves the submission/history, and notifies the responsible assignee.
7. The approval record stores the reviewer, timestamp, decision, note where applicable, and exact evidence submission/version reviewed.
8. Each event/workspace should identify an eligible backup reviewer for cases where the task owner is also the only available lead. The backup must have explicit authority.

### Acceptance checks

- A coordinator cannot mark a proof-required task complete through the interface or a direct request without an approved review.
- A submitter cannot approve their own evidence by switching roles in the interface.
- A Department Lead cannot review tasks outside their permitted department scope unless separately granted access.
- An Event Lead cannot review another event's tasks merely because it is in the same program.
- A rejected submission includes a reason and remains available in history; the task is not completed.

### Remaining choice

Confirm whether Department Leads/Event Leads should receive review permission by default for their scope, or whether review permission must always be granted separately. Recommended default: grant review permission within their lead scope, excluding their own submissions.

## 3. FWD-002 — Role inheritance and scope rules

### Proposed policy

CampusOps roles should be permission bundles rather than hard-coded authority derived from role titles. Every role assignment includes a scope, such as:

- organization workspace;
- program (multi-event workspace);
- individual event;
- department within a standalone event or shared program department;
- task-specific assignment, where needed.

Use these rules:

1. A user must have an active organization membership to access that organization's workspace.
2. A permission applies only to the scope stated in the grant.
3. Parent-scope permissions extend to child scopes only when the permission grant explicitly says they do. A general program-level membership must not automatically reveal all participant records or grant every event-editing action.
4. A shared department in a multi-event program defines a common organizational grouping; it does not automatically grant access to every child event's tasks, registrations, check-ins or private evidence.
5. A user assigned to multiple events receives the union of their valid active grants only within each grant's scope. Role changes or removal take effect server-side and are audited.
6. Display names such as “Lead”, “Core Member” or “Coordinator” do not confer permissions by themselves. Permission settings and scope determine effective access.
7. Where two roles need equivalent powers, configure equivalent permissions explicitly rather than assuming two role titles are interchangeable.

### Acceptance checks

- A person assigned to Event A cannot edit Event B just because both belong to the same program.
- A coordinator assigned to a shared department can see their assigned events and authorized team context but does not automatically access all child-event participant lists.
- An organization-level administrator can perform only the administrative and operational actions granted to that role; sensitive actions remain logged.
- Removing an event assignment revokes that event's access without deleting the person's account or unrelated organization memberships.

## 4. FWD-003 — Solo and team registration data

### Proposed policy

Keep the registration/grouping record separate from the people expected to attend.

- **Solo registration:** one registration record linked to one individual participant record.
- **Team registration:** one team/group registration record linked to an individual participant record for every team member expected to attend.
- Each participant has their own event-specific registration status and check-in state.
- A team name, team leader's scan, or team registration status must never mark every member as present.
- Check-in is recorded per participant and event. A repeat scan/search returns an `Already checked in` result and must not create a second successful check-in.
- Native registration and external imports should map into the same normalized participant/registration model, while retaining source-system identifiers and sync status where relevant.
- Email alone should not be treated as a guaranteed unique-person identifier. Matching/import conflicts require a defined review or merge process.
- If a team roster changes after registration, preserve the previous state in history and apply an explicit policy for adding/removing members; do not silently overwrite attendance records.

### Acceptance checks

- A team of five can have three members checked in and two not yet checked in.
- A participant registered individually is checked in only against their own record.
- Repeated check-in attempts are safely handled, including near-simultaneous attempts from two staff devices.
- An imported record is not duplicated when the same source response is imported again.

### Remaining choices

- Which fields are required for an individual participant and for a team registration?
- Is team roster editing allowed until a defined cutoff, and who approves edits after that point?
- What identifier should be used for lookup at the registration desk (QR code, registration ID, name/search, or a combination)?

Recommended default: support QR/unique registration ID plus name/search fallback, and require explicit review for roster changes after an event-defined cutoff.

## 5. FWD-004 — Cross-event roster visibility and privacy

### Proposed policy

Meet the requirement that members can view who belongs to their event and other events without exposing unnecessary personal information.

**Visible to active workspace members by default:**
- display name;
- workspace role/title;
- department membership;
- event/program assignment;
- membership status needed for operational coordination.

**Restricted by default:**
- personal email address and phone number;
- account recovery/security data;
- attendee registration fields and participant contact details;
- private evidence files and task attachments outside the user's authorized work scope;
- audit records outside the user's administrative/review scope.

Contact details should be shown to workspace administrators and members who need them for a shared operational responsibility, based on explicit permissions. Directory visibility alone does not grant permission to message, edit, invite, or access a person's records.

### Acceptance checks

- A member can identify coordinators assigned to another event by name, role, department and event.
- A general workspace member cannot export or browse everyone's email addresses by default.
- A registration staff member sees only the participant information needed for assigned check-in duties.
- Access to task evidence and participant records is checked independently from roster access.

### Remaining choice

Should all workspace members be able to see each other's email addresses? Recommended default: **no, not automatically**; provide email visibility to the person's team/leads and other authorized operational roles. The founder may choose a wider organization-level policy later, subject to privacy and least-privilege review.

## 6. FWD-005 — Task deadlines and changes

### Proposed policy

1. A task can be saved as a draft before all details are known, but it cannot be assigned/activated without a specific due date and time or an explicitly selected all-day due date where time precision is not needed.
2. Event and task dates are interpreted in the event's configured time zone; the stored representation must be unambiguous. The UI should display the time zone when cross-zone use could cause confusion.
3. The task creator/assigner and authorized leads can edit a deadline within their permitted scope.
4. Assignees cannot silently change a deadline after assignment. They can request a deadline change, provide a reason, and await an authorized decision.
5. A deadline change after work has started requires a reason, preserves the previous and new values, records who changed it and when, and notifies affected assignees/reviewers.
6. A deadline change must not erase prior progress, proof submissions, review decisions or audit history.
7. A completed task's deadline is locked by default. Reopening or correcting a completed task requires an authorized action with a reason and audit entry.
8. Tasks in `Submitted for Review` should not be silently rewritten by the assignee. A permitted deadline change can be recorded without replacing the evidence submission; if the task needs new work, the reviewer must request changes through the review flow.
9. A task cannot be made overdue or on-time solely by changing its deadline without leaving an audit trail.

### Acceptance checks

- An assigned task has a visible specific deadline.
- An assignee can request a change but cannot unilaterally overwrite the deadline.
- An authorized lead changes a deadline and provides a reason; the prior deadline remains in history and the assignee is notified.
- Changing a deadline does not automatically mark a task complete or erase a submitted proof.
- A completed task's deadline cannot be silently changed retroactively.

### Remaining choices

- Should all tasks require a time, or may routine tasks use an all-day due date? Recommended default: store date and time consistently but allow a clearly defined all-day due date for tasks that do not require hour-level precision.
- Who can approve a deadline-change request? Recommended default: the task assigner or an authorized lead/core member within the task's scope.

## 7. Related permission defaults

These rules connect the five decisions above:

| Action | Recommended authority | Scope constraint |
|---|---|---|
| Add a new member | Workspace administrator or explicitly delegated membership manager; scoped lead may invite/add within the assigned department/team if granted | Invitation must specify workspace, role and event/program/department scope |
| Reassign an existing member | Authorized membership manager or lead with team-management permission | Do not silently grant access to a new event or department; update scope and audit history |
| Assign work | Office bearer/core member with task-assignment permission; standalone Department Lead within department; multi-event Event Lead within assigned event | Task must have a responsible owner and deadline before becoming active |
| Approve proof | Eligible reviewer other than the submitter | Within assigned department/event/program review scope |
| Change a deadline | Task assigner or authorized lead/core member | Reason, audit history and notification required after work starts |
| View cross-event roster | Active workspace members | Basic roster only; contact, participant and evidence records remain separately permissioned |

## 8. Decision status and next action

**No proposed rule in this document is silently promoted to founder-confirmed status.** Once the founder confirms or edits the defaults, update the requirements specification, permission matrix, data model and decision log together so they remain consistent.

The high-value confirmations needed first are:

1. Lead review permissions by default, with self-review prohibited.
2. Explicit scope inheritance rather than automatic access across all program events.
3. Individual records for every team member and individual check-in.
4. Basic cross-event directory visible to all workspace members, with email/contact details restricted by default.
5. Specific deadlines required before a task becomes active; deadline edits are authorized, recorded and communicated.
