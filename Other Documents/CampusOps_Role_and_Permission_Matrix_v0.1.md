# CampusOps — Role & Permission Matrix

**Version:** 0.1  
**Status:** Proposed design artifact for founder review  
**Related document:** `CampusOps_Requirements_Specification_v0.9.md`  
**Working mode:** Documentation only. This document does not authorize prototype or application implementation.

## 1. Purpose

Define who can do what in CampusOps without forcing every organization into a rigid title hierarchy. CampusOps uses an organization workspace with individual user accounts. A person's effective permissions come from their workspace membership, role permissions, and the scope of their assignment (organization, program, event, or department).

The user-facing setup paths remain distinct:

- **Standalone event:** department leads are assigned to the required departments. Each department lead can add members to that department and assign departmental work.
- **Multi-event program:** the program contains several event records. Leads are assigned to individual events; departments are shared across the program, and there are no separate department-lead roles by default. Coordinators are assigned to departments and specific work.

Both paths share task tracking, evidence review, registration, individual check-in, and post-event documentation foundations.

## 2. Authorization principles

1. **Individual identity:** every person signs in through their own account; no shared club password.
2. **Role title is not enough:** permissions must be explicit. Two differently named roles can have equivalent permissions when appropriate.
3. **Scope matters:** a user may lead one event without automatically leading every event in the organization.
4. **Least privilege:** grant the minimum permissions necessary for a role's responsibilities.
5. **Server-side enforcement:** every protected action must be authorized by the backend; hiding a control in the interface is not security.
6. **Audit consequential changes:** preserve who changed a role, assignment, deadline, approval, or attendance record and when.
7. **No self-approval by default:** a task submitter cannot approve their own proof. A separately authorized reviewer must review it.
8. **Directory visibility is not equal to data access:** seeing that a person belongs to another event does not automatically grant access to their private contact details, credentials, participant records, or task evidence.

## 3. Role templates

These are suggested starting roles, not a fixed hierarchy. Organizations can configure supported permissions while preserving security boundaries.

| Role template | Typical scope | Intended responsibility |
|---|---|---|
| Primary Workspace Administrator | Organization | Manage workspace configuration, membership, role assignments, organization details, and administrator continuity. This is an account/workspace administration role, not simply an event title. |
| Office Bearer / Authorized Core Member | Organization, program, or assigned event scope | Oversee preparation and execution, create or manage workspaces within permission, assign tasks, add team members, review task evidence, and monitor relevant progress. Office bearers and core members may be given equivalent permissions when required. |
| Event Lead | One or more assigned events within a multi-event program | Lead the assigned event, coordinate its work, assign coordinators to shared departments, assign/reassign event tasks, review submissions within scope, and report progress. |
| Department Lead | A department within a standalone event | Manage the department's membership and tasks, assign departmental work, review evidence within scope if granted, and report progress. This role is not used by default in the multi-event workflow. |
| Coordinator / Team Member | Assigned department, event, or task | View relevant plans, work on assigned tasks, update progress, submit proof, and see the workspace member directory according to access rules. |
| Registration Staff | One or more assigned events / check-in stations | Find registration records and record an individual participant's check-in. Access to participant details is limited to what is needed for verification. This can be an additional permission set on a coordinator account, not necessarily a separate account type. |
| Faculty Coordinator | Organization or explicitly assigned scope | A directory/contact record does not automatically grant platform access. If invited as a member, permissions must be explicitly assigned and may include oversight or approval rights where the organization chooses. |

**Platform support administrator:** if CampusOps later needs an internal support role, it must be separate from organization roles, limited in scope, and auditable. It is not assumed to exist in the initial release.

## 4. Permission matrix — recommended starting defaults

Legend:
- **Yes** — permitted within the stated scope.
- **Scoped** — permitted only for the events, departments, or resources assigned to the user.
- **Grant explicitly** — available only when the organization grants that permission.
- **No by default** — not permitted unless an explicitly designed permission says otherwise.

| Action | Primary Workspace Admin | Office Bearer / Authorized Core Member | Event Lead (multi-event) | Department Lead (standalone) | Coordinator / Team Member | Registration Staff permission |
|---|---|---|---|---|---|---|
| Edit organization profile and verification information | Yes | Grant explicitly | No by default | No by default | No by default | No by default |
| Manage workspace membership and invite users | Yes | Grant explicitly | Scoped / grant explicitly | Scoped to own department if granted | No by default | No by default |
| Configure roles and permissions | Yes | Grant explicitly | No by default | No by default | No by default | No by default |
| Create standalone event workspace | Yes / grant by policy | Yes if granted | No by default | No by default | No by default | No by default |
| Create a multi-event program and add event records | Yes / grant by policy | Yes if granted | No by default | No by default | No by default | No by default |
| Edit event details, schedule, or venue | Grant explicitly | Scoped | Scoped | Scoped to standalone event if granted | No by default | No by default |
| Create or manage departments | Grant explicitly | Scoped | Uses the program's shared departments; edits only if granted | Scoped to their department | No by default | No by default |
| Add coordinator/member to a department | Grant explicitly | Scoped | Assign people to departments within assigned events, subject to program policy | Yes within own standalone-event department | No by default | No by default |
| Assign tasks directly to leads or coordinators | Grant explicitly | Scoped | Scoped to assigned events | Scoped to own department; cross-department assignment only if granted | No by default | No by default |
| Update progress on own assigned task | Yes if also assignee | Yes if also assignee | Yes if also assignee | Yes if also assignee | Yes | Yes if assigned a task |
| Submit task proof (file or link) | If assigned | If assigned | If assigned | If assigned | Yes for assigned task | If assigned |
| Review/approve task proof | Only if granted and not submitter | Yes within granted scope, not own submission | Yes within assigned event if granted, not own submission | Yes within own department if granted, not own submission | No by default | No by default |
| Request changes / reject proof with a note | Same as review permission | Same as review permission | Same as review permission | Same as review permission | No by default | No by default |
| See workspace-wide member directory | Yes | Yes | Yes | Yes | Yes, with privacy limits | Yes, with privacy limits |
| See member private contact details | Grant explicitly / operational need | Grant explicitly / operational need | Scoped / operational need | Department-scoped / operational need | No by default | Only minimum needed for check-in |
| View participant registrations | Grant explicitly | Scoped | Scoped if required | Scoped if required | No by default | Yes for assigned event/check-in scope |
| Record or correct individual check-in | Grant explicitly | Scoped | Scoped if required | Scoped if required | No by default | Yes within assigned event/station |
| View post-event report | Yes | Scoped | Assigned event | Assigned event | Grant explicitly or summary-only | No by default |
| Edit/submit post-event documentation | Grant explicitly | Scoped | Assigned event | Assigned event if granted | Assigned items only if granted | No by default |
| View organization/program audit history | Yes, subject to privacy policy | Grant explicitly | Assigned event history if granted | Department/event history if granted | No by default | No by default |
| Transfer primary workspace administration | Yes, through controlled transfer flow | No by default | No by default | No by default | No by default | No by default |

This matrix proposes defaults for discussion. It does not supersede permissions explicitly confirmed by the founder; any mismatch must be recorded and resolved before requirements are frozen.

## 5. Workflow A — Standalone event

1. An authorized workspace member creates a standalone event, supplies event details, and selects the required departments.
2. The authorized organizer assigns a Department Lead to each department, entering the intended person's name and email and sending an invitation.
3. The invitation is bound to the organization, intended email, assigned role, department, and event scope. An existing CampusOps user signs in and accepts; a new user creates an individual account and then accepts the invitation. The invitee cannot grant themselves a higher role.
4. Once accepted, the Department Lead can manage membership in their department and assign departmental work within the granted scope.
5. Office bearers and authorized core members can add coordinators and assign work directly to either leads or coordinators, subject to their permissions.
6. A task is assigned with an explicit deadline. The assignee updates progress and submits completion proof as a file or link.
7. The task enters a review-required state. An authorized lead/core member reviews the proof. Approval moves the task to `Completed`; rejection leaves it non-completed, records a review note, and notifies the assignee.

## 6. Workflow B — Multi-event program

1. An authorized workspace member creates a program and enters details for multiple events. Each event keeps its own dates, venue, event-specific details, tasks, registration/check-in records, and close-out report.
2. The program defines the shared department set used across its events. By default, it does not create a separate Department Lead role for every event department.
3. Authorized office bearers/core members assign Event Leads to specific events. The same person may lead more than one event if assigned and if workload permits.
4. Office bearers/core members add coordinators and assign them to one or more shared departments and relevant event tasks. The assignment must identify both the department and the event/task scope.
5. Members can view the workspace-wide member directory, including members assigned to other events. Private contact details and participant records remain permission-controlled.
6. Tasks follow the same deadline, progress, proof-submission and review workflow as standalone events. Review authority is limited to the assigned event/program scope.
7. Program-level summaries aggregate child-event status without merging their underlying task, registration, check-in or report records.

## 7. Task proof and approval state machine

Recommended states:

`Not Started` → `In Progress` → `Submitted for Review` → (`Completed` if approved, or `Changes Requested` if rejected)

- `Submitted for Review` is not completion.
- If proof is rejected, the task remains non-completed, returns to a workable state (recommended: `Changes Requested`), and includes a reviewer note.
- The assignee is notified when review is completed and when additional proof is needed.
- Approval records reviewer, timestamp, decision, and the evidence version reviewed.
- If proof is updated after rejection, the newest submission is clearly distinguished from prior submissions.
- A user cannot approve their own submission by default, even if they also hold a lead role.
- The precise notification channel (in-app, email, or both), file size/type limits, evidence retention period, and link-access policy remain open.

## 8. Workspace-wide member visibility

Founder requirement: members participating in a multi-event workspace can see who is on their own event and the other events.

Recommended interpretation to protect privacy:
- All workspace members may see a directory of members' display names, workspace roles, departments, and assigned event(s), subject to organization policy.
- Email addresses and other contact details should be displayed only when needed for coordination or when explicitly authorized.
- Registration/participant records, submitted proof files, account security details, and audit records do not become visible merely because the roster is visible.
- A user removed from an organization immediately loses workspace access, but their historical task submissions and approvals remain attributed to the original account.

Confirm whether the directory should expose member email addresses to everyone in the workspace or only to authorized roles.

## 9. Cross-cutting check-in rule

For both standalone and multi-event setups, participant attendance is recorded per individual person:
- A solo registration maps to one participant record.
- A team registration maps to the team/group record plus distinct participant records for every member expected to attend.
- Checking in the team name alone does not mark all members present.
- Each person is checked in individually. A repeated scan/search must show `Already checked in` and must not silently create another attendance record.
- The data model must distinguish registration status from attendance status and allow authorized staff to handle exceptions with a recorded outcome.
- For external registrations, define how team membership is imported or collected, and how missing member details are resolved before the event.

## 10. Decisions still required

| ID | Decision needed | Recommended default | Why it matters |
|---|---|---|---|
| RPM-D01 | Who can finally approve proof in standalone events? | Assigned Department Lead or explicitly authorized core member/office bearer; never the submitter. | Prevents approval ambiguity and self-approval. |
| RPM-D02 | Who can finally approve proof in multi-event programs? | Assigned Event Lead or explicitly authorized core member/office bearer; never the submitter. | Keeps review rights scoped to the correct event. |
| RPM-D03 | Does the workspace directory expose email addresses to all members? | Show names, roles, departments and event assignments workspace-wide; restrict emails to operational need or permission. | Balances founder's requested visibility with personal data minimization. |
| RPM-D04 | Can leads add any workspace member to their team or only invite/assign within scope? | Allow adding existing workspace members within authorized scope; new external members require a scoped invitation. | Avoids duplicate personal accounts and uncontrolled privilege changes. |
| RPM-D05 | Who can edit a deadline after a task has started or proof has been submitted? | Assignee cannot change it unilaterally; authorized assigner/lead may change it with an audit record and notify the assignee. | Preserves accountability and history. |
| RPM-D06 | Can a member hold different roles on different events? | Yes, permissions are scoped by assignment; effective access is the union of valid grants, constrained by organization policies. | Necessary for shared coordinators and leads across events. |
| RPM-D07 | Who can change a person’s role or remove them from a workspace? | Workspace administrator or explicitly delegated membership manager; scoped lead can only manage members in their authorized scope. | Defines secure offboarding and role changes. |

## 11. Acceptance checks for the permission model

Before implementation is approved, the design must pass at least these tests:

1. A Department Lead in a standalone event can add a member to their own department but cannot edit another department unless granted permission.
2. An Event Lead in a multi-event program can manage assigned event operations but cannot automatically change another event's roles or participant records.
3. A coordinator can submit proof but cannot self-approve it by changing their role in the interface or making a direct API request.
4. A core member with review authority can approve or request changes within their scope, and the assignee receives a notification and reason when changes are requested.
5. A workspace member can see the workspace directory, but cannot access restricted registration data or private records without permission.
6. A member removed from an organization loses access promptly, while prior submissions and approvals remain in the audit history.
7. A team check-in process records each participant separately and prevents duplicate attendance.
8. A member assigned to multiple events sees only the event/program actions permitted by each assignment.
9. Role changes and permission grants take effect server-side and are recorded with actor and timestamp.
10. The system prevents removal of the last active workspace administrator until a transfer/recovery route is completed, once that proposed policy is approved.

## 12. Status summary

### Founder-confirmed directions used here
- Organization workspace with individual accounts and no shared club login.
- Two distinct setup workflows: standalone event and multi-event program.
- Standalone: department leads are assigned to departments and can add departmental members and assign work.
- Multi-event: leads are assigned to events; shared departments apply across events; no separate department leads by default; coordinators are assigned departments and work.
- Office bearers and authorized core members can add coordinators and assign work to leads or coordinators.
- Task proof is submitted as a file or link and reviewed before completion; rejected proof requires a note and notification.
- Workspace members can view people assigned across the other events as well as their own event.
- Every participant in a solo or team event must be checked in individually.
- Participant-facing doubt/question/issue-raising is out of scope.

### Still proposed or unresolved
- Exact permissions of the Primary Workspace Administrator and faculty coordinator.
- Which roles have approval authority by default and whether an alternate reviewer is required.
- Whether member emails are visible workspace-wide.
- Who can alter deadlines and role assignments in edge cases.
- Invitation expiry, verification and recovery policies in the related requirements document remain recommendations until confirmed.
- Notification channel, evidence file limits/retention, external registration sync rules and offline check-in behavior.

---

**Next recommended artifact:** a data model and relationship map aligned with the approved permissions and both event setup workflows. It should define Organization, User, Membership, Program, Event, Department, Role/Permission, Invitation, Task, Evidence Submission, Review, Registration, Participant, Team Registration, Check-in, and Post-event Report relationships before the technical architecture is finalized.
