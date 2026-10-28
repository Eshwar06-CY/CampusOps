# CampusOps — Foundational Workflow Reconciliation

**Version:** 0.1  
**Status:** Working recommendation package; not an approval record  
**Mode:** Documentation and product planning only. No prototype or application code is authorized by this document.

## 1. Purpose

Reconcile the founder's described workflows with the current requirements specification, role-and-permission matrix, logical data model, architecture decision record, and foundational workflow decision matrix. This document identifies consistent rules, recommended defaults, and the edits that must be made before API contracts and a physical database schema are treated as ready.

## 2. Founder-confirmed product directions

The following are treated as established directions because they were explicitly described by the founder:

1. CampusOps is an event-operations platform for standalone events and multi-event programs. It focuses on preparation, backend coordination, event-day operations, registration/check-in, and post-event documentation.
2. Marketing campaign management, poster/reel creation, promotional activity tracking, and social publishing are out of scope.
3. Participant-facing doubt/question/issue submission is out of scope. Staff-only operational blockers may remain a team-management capability only if clearly distinguished from participant support.
4. Each organization has a workspace; every office bearer and team member has an individual account. The organization is not a shared login.
5. Members are invited by email into an organization/workspace and have an individual account. Invitees must not be able to self-grant a role or permissions beyond the invitation.
6. Standalone workflow: the organizer defines event departments and assigns a department lead to each required department. Department leads can manage their department's members and tasks within their permissions. Office bearers and authorized core members can assign work to leads or coordinators.
7. Multi-event workflow: a parent program contains several event records. The program has common departments; leads are assigned to specific events; coordinators are assigned to departments and to the event/work they support. There are no department leads by default in this workflow.
8. In both workflows, tasks have specific deadlines, assigned owners, progress updates, evidence submission (file or link), review, rejection notes, and notification. A proof-required task is not completed until accepted by an authorized reviewer.
9. Members can view the roster across events in the same workspace. What personal contact details appear in that roster is not yet confirmed.
10. Registration can be native or through an external integration. A solo registration or team registration does not replace the requirement to verify each actual participant individually at check-in.
11. Post-event records include event details, registrations, actual attendance, supporting photos/evidence, and completion of required documentation.
12. No prototype, code, installation, or implementation work should begin unless the founder explicitly requests it.

## 3. Recommended foundational rules

These are proposed defaults to make requirements testable. They are not marked founder-approved.

### FWD-001 — Proof review and task completion

- Use a distinct evidence-submission record and review record.
- A proof-required task becomes `Completed` only after an authorized reviewer approves the current evidence submission.
- The task submitter cannot approve their own submission, including when they also hold a lead or office-bearer role.
- Reviewer authority is explicit and scope-bound: standalone department lead for their department; multi-event lead for the assigned event; office bearer/core member only within granted workspace/program/event scope.
- A rejection requires a note, preserves the rejected version and review history, returns the task to a non-completed state (recommended label: `Changes Requested`), and notifies the responsible assignee.
- Define an eligible backup reviewer for cases where the usual reviewer is unavailable or has submitted the evidence.

**Open confirmation:** Whether lead roles receive review permission automatically within their scope or whether that permission must always be explicitly granted. Recommended default: grant within lead scope, excluding self-review.

### FWD-002 — Role and scope permissions

- Role names are labels; authorization uses explicit permission grants and scope.
- A role assignment must identify its scope: organization, program, event, department, or task as applicable.
- Permission inheritance from a parent scope to child events is never implicit. Any inheritance must be explicitly configured and tested.
- In a multi-event program, common departments provide shared organizational structure only. A shared department membership does not grant access to every child event's tasks, attendee records, private files, or check-ins.
- A person may have multiple active assignments; effective access is the union of those explicit grants, not a workspace-wide elevation.
- Removing one membership/assignment revokes that scope without deleting the personal account or unrelated memberships.

### FWD-003 — Team registration and individual attendance

- Separate the registration submission/team grouping from the individual people who are registered.
- Solo registration links to one participant; team registration links to a group and one participant record for every member.
- Check-in is recorded separately for every participant and event.
- A team QR code may locate the group or its roster, but scanning it must not mark all members present by default. Each person is verified and checked in individually.
- Repeated or near-simultaneous check-ins must not create duplicate successful attendance records.
- External imports should be idempotent and keep source identifiers/sync status. Email alone should not automatically merge people without a defined matching policy.
- Changes to the roster after registration should preserve prior values and follow a defined cutoff/review policy.

**Open confirmation:** Required participant fields, roster editing cutoff, and primary lookup method. Recommended starting point: unique registration/participant identifier or QR plus name/search fallback; define any roster cutoff per event.

### FWD-004 — Workspace member directory and privacy

- All active workspace members can discover who is in the workspace and which events/departments people are assigned to, consistent with the founder's cross-event visibility requirement.
- Directory visibility does not grant editing, invitation, participant-record, evidence-file, audit-log, or private-contact access.
- Recommended default public within the workspace: display name, assigned role, department, event/program assignment, and membership status needed for coordination.
- Recommended default restricted: personal email/phone, account-recovery/security data, attendee contact fields, private evidence, and sensitive audit data.

**Open confirmation:** Whether email addresses should be visible to every workspace member or only to authorized operational roles. Recommended default: restricted to people with an operational need.

### FWD-005 — Task deadlines and changes

- A task that is ready for assignment must have an explicit deadline. Support date-only/all-day deadlines where hour precision is not needed and date-time deadlines for operationally time-sensitive work.
- Interpret times in the event's configured time zone; record the effective timestamp and display context consistently.
- Assigned users can request a deadline change; authorized leads/owners can approve or change the deadline within scope.
- A deadline change after assignment requires a reason, audit entry, and notification to assignees and relevant leads.
- Preserve the original deadline and each subsequent change. Do not silently overwrite deadline history.

**Open confirmation:** Which roles may directly edit deadlines in standalone and multi-event workflows. Recommended default: event creator/authorized office bearer, relevant lead within scope, and a specifically granted task owner; assignees request changes.

## 4. Cross-document consistency map

| Rule | Requirements specification | Role/permission matrix | Logical data model | Architecture / test impact |
|---|---|---|---|---|
| Personal accounts plus organization workspace | Signup, membership, invitation, transfer, and recovery requirements | Separate account identity from membership and role scope | `User`, `Organization`, `Membership`, `Invitation`, scoped `RoleAssignment` | Authentication is separate from authorization; test multiple memberships and revocation |
| Standalone department-lead structure | Standalone event setup and work assignment | Department lead limited to the standalone event/department | Event-scoped `Department`, scoped role assignment, tasks | Test access to own department versus another department |
| Multi-event event-lead/shared-department structure | Program creation and shared department workflow | Event lead scoped to assigned child event; coordinators have explicit department/event assignment | `Program`, child `Event`, shared `ProgramDepartment` or equivalent, event-scoped assignments | Test that department membership never grants child-event access implicitly |
| Proof-required completion | Submission, review, rejection and notification requirements | Review permission separate from submit permission | `EvidenceSubmission`, `TaskReview`, `TaskStatusHistory`, audit record | Enforce transition server-side; test self-review and stale evidence approval |
| Specific deadline and change history | Deadline requirements and notifications | Who can edit/request within role scope | `Task.deadline`, timezone context, `TaskDeadlineChange` or equivalent history | Test changes, notification delivery, time-zone interpretation and overdue calculation |
| Team registration, individual check-in | Registration and individual verification requirements | Registration staff can access only assigned event scope | `Registration`, team/group registration, `Participant`, `RegistrationParticipant`, `CheckIn` | Test partial team arrival, duplicate scans, concurrency and import idempotency |
| Cross-event directory | Members visible across events | Read roster does not imply other permissions | Membership and scoped role assignments; private profile fields separate | Test roster visibility versus contact/participant/evidence access |
| Post-event documentation | Reports, actual attendance, photos/evidence, closure | Editing/viewing reports is scope-bound | `PostEventReport`, `ReportEvidence`, attendance relations | Reconcile attendance; report completion and rollups must not double-count |
| Scope exclusions | No marketing module and no participant-facing doubt/issue submission | No permission for excluded participant-facing issue route | Do not add marketing entities; staff-only operational issue entity may remain if clearly bounded | Negative tests verify excluded functions/routes are absent |

## 5. Key corrections to apply before API contracts

1. **Make role scope explicit throughout.** Avoid a single global `lead_user_id` field on an event or department; model assignments so multiple eligible leads, shared permissions, and role changes remain auditable.
2. **Separate program departments from child-event task scope.** The program can define common departments, while assignments and tasks remain attached to the specific event where work happens.
3. **Model evidence approval as a state transition.** A boolean `task.completed` is insufficient for proof-required tasks; keep evidence versions, reviewer decisions, and status history.
4. **Model a team/group separately from individual participants.** Attendance belongs to each person in each event.
5. **Separate directory profile from account security and private contact information.** This supports cross-event visibility without exposing unnecessary data.
6. **Preserve deadline history.** Do not store only the latest deadline if the workflow needs traceability of changes.
7. **Keep participant issue submission out of scope.** If internal operational blockers remain, label them as staff-managed operational records—not participant support tickets.
8. **Distinguish proposed from confirmed policy.** The provider/technical choices and defaults above remain provisional until reviewed.

## 6. Readiness gates

### Gate A — Required before freezing API contracts and physical schema

- Reviewer permissions and self-review prohibition.
- Program/event/department relationship and scope inheritance.
- Team registration, individual participant required fields, roster edits, and check-in lookup.
- Member roster fields versus private contact details.
- Deadline editing authority, date-only versus date-time behavior, and time zones.
- Task proof-required versus proof-optional rule and task status transitions.

### Gate B — Required before selecting integration/provider implementation

- First external registration integration and one-way/two-way sync direction.
- Authentication, invitation email and notification providers.
- File storage provider, types/size limits, malware scanning, private access and retention.
- Hosting budget/region, backups and restoration procedure.
- Offline/degraded-network policy for check-in.

### Gate C — Required before a real-world pilot

- Negative authorization tests for every organization/program/event/department scope.
- Duplicate and concurrent check-in tests.
- Proof review, rejection, resubmission and self-approval tests.
- External-import replay, failure recovery and record matching tests.
- Privacy checks for rosters, participant records, evidence files and audit history.
- Backups and restore tested; retention/export/deletion policy documented.
- Event-day fallback and operator instructions reviewed.

## 7. Recommended next artifact

After the open Gate A choices are approved or explicitly kept provisional, prepare **API Contract Draft v0.1** with resource definitions and endpoints grouped by domain: identity/organization, invitations/memberships, events/programs/departments, tasks/evidence/reviews, registrations/participants/check-ins, and post-event reports. Contracts should not encode provider-specific authentication or external-registration behavior until those decisions are settled.

## 8. Status statement

The founder-confirmed workflow is documented. The policies in Section 3 are recommendations, not confirmations. This reconciliation is a review artifact; it does not approve implementation, create a physical schema, or authorize coding.
