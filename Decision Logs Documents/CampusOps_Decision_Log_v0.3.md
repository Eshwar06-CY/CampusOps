# CampusOps — Product Decision Log

**Version:** 0.3  
**Status:** Working log; records confirmed product directions and proposed account/invitation defaults awaiting review  
**Purpose:** Preserve product choices, unresolved questions, rationale, and validation requirements.

## Confirmed product direction

| ID | Decision | Current status | Notes |
|---|---|---|---|
| D-001 | CampusOps covers event preparation/backend operations, event-day execution, and post-event documentation. | Confirmed direction | It is intended for standalone events and multi-event programs. |
| D-002 | Marketing management is outside product scope. | Confirmed | No campaign management, promotional visit tracking, poster/reel creation, or social publishing. |
| D-003 | Attendee-facing doubts/questions/issues submission is outside product scope. | Confirmed | Registration/check-in remain in scope. Staff-only internal operational blockers can remain where useful. |
| D-004 | Native registration and selected external registration integrations are in the product direction. | Direction accepted; implementation open | Provider, field ownership and sync method remain undecided. |
| D-005 | Team roles and permissions should be configurable, including equivalent authority where roles share responsibilities. | Direction accepted | Final permission matrix and customization limits remain open. |
| D-006 | Standalone and multi-event setup are distinct user journeys. | Confirmed direction | Recommended architecture uses shared event concepts/services where appropriate; separate screens do not automatically mean separate data models. |
| D-007 | Office bearer and faculty coordinator directory can be edited after onboarding. | Confirmed direction | Leadership changes must not silently rewrite historical task ownership or approvals. |
| D-008 | Team members invited as leads/coordinators create personal accounts separately from organization signup. | Confirmed direction | The organization workspace and individual named-account model is confirmed; members do not share club credentials. |
| D-009 | Standalone setup has event-specific departments and a lead for each department. | Confirmed direction | A department lead may add members within authorized scope; office bearers/core members can assign work to leads or directly to coordinators. |
| D-010 | Multi-event setup has a common department list and event-level leads, not individual leads for each shared department. | Confirmed direction | Coordinators are assigned to shared departments and one or more permitted child events. |
| D-011 | Workspace members can view the cross-event roster in a multi-event workspace. | Confirmed with privacy boundary open | Base fields such as name, role, department and event scope can be visible; broader contact details require an explicit policy. |
| D-012 | Each task has a specific deadline and proof is required before completion. | Confirmed direction | File or link evidence; a lead/core member reviews; approval marks complete; rejection keeps it non-completed, records a note and notifies the responsible person. |
| D-013 | Solo/team registration must verify every person individually. | Confirmed direction | A team is not checked in as a single all-or-nothing attendance record. |
| D-014 | Requirements work should precede implementation. | Confirmed instruction | Do not create or revise prototypes, code, installations, or integrations unless the founder explicitly requests them. |
| D-015 | The club is an organization workspace and every office bearer/team member uses an individual named account with appropriate permissions; no shared club login. | Confirmed by founder | v0.8 recommends the first verified creator becomes the initial Primary Workspace Administrator; transfer and emergency recovery rules are proposed, not yet confirmed. |

## Open decisions and recommended defaults

| ID | Open decision | Recommended default to evaluate | Why it remains open / decision gate |
|---|---|---|---|
| O-001 | Who administers and transfers workspace control? | Proposed: initial verified creator is Primary Workspace Administrator; allow explicitly authorized additional administrators; encourage a second admin; prevent removal of the last admin; transfer to an active verified member with explicit acceptance. | Founder has confirmed individual accounts but has not yet approved these specific administration/transfer policies. Emergency recovery must not rely on a claimed club name alone. |
| O-002 | What does an invitee's role selection mean? | Proposed: invitation is bound to the role and scope chosen by an authorized inviter; invitee reviews/acknowledges that role. They may request a correction but cannot self-grant privileges. | Preserves the founder's invitee role-confirmation step without allowing privilege escalation. Exact UX remains to be reviewed. |
| O-003 | How long do invitations remain valid, and how are cancellation/resend handled? | Proposed default: secure, single-use invite bound to email/workspace/role/scope, expiring after 7 calendar days; cancel/reissue invalidates old token; an existing account signs in and accepts rather than creating a duplicate. | Seven days is a recommended default only; expiry configurability and detailed edge cases require review. |
| O-016 | How is the organization/club verified? | Require account email verification plus a separate organization verification step; record pending/approved/rejected state; do not enable event workspace creation until required verification passes. | The founder expects college/club details to be verified, but the evidence and verification mechanism have not been specified. |
| O-017 | How should account and workspace membership be separated? | One personal account can belong to multiple organization workspaces, with separate memberships/roles/scopes; removing one membership does not delete the personal account or unrelated memberships. | Recommended identity model for accountability and future use across clubs; must be reflected in data model and authorization. |
| O-018 | What happens when a member leaves or an office bearer changes tenure? | Update directory and membership separately; remove/suspend access when appropriate; preserve historical actions; transfer workspace administration before disabling the last administrator. | Avoid confusing the directory of current leaders with actual login permissions. |
| O-019 | How is lost administrator access recovered? | Use individual account recovery and a documented organization-verification procedure; require documented checks before changing the primary administrator. | Prevent unauthorized takeover and avoid dependence on one person's availability. |
| O-004 | Can the same person be assigned to multiple departments/events? | Allow multiple scoped memberships/assignments where authorized. | Must prevent ambiguous ownership, conflicts and access leakage. |
| O-005 | Should a department lead in the standalone workflow be able to assign tasks to anyone in the whole event or only within their department? | Restrict to their department by default; allow broader scope only through explicit permissions. | Validate against the founder's intended operational hierarchy and prevent excessive access. |
| O-006 | Who may approve proof submitted by a lead? | Permit only reviewers explicitly authorized for that task scope; require a different reviewer when separation of duties is needed. | Avoid self-approval conflicts while allowing efficient operations for small clubs. |
| O-007 | What proof formats and limits are accepted? | File attachments and HTTPS links initially; define supported file types, size limits, malware checks, and link handling before production. | Storage, safety and review effort depend on the formats. |
| O-008 | What happens if a task's proof is rejected? | Preserve the task as non-completed, record the reviewer note, notify the owner, and allow resubmission. | The workflow must not make rejection look like completion or erase history. |
| O-009 | Which external registration source is first? | Investigate Google Forms first because it matches the currently described workflow. | Verify current API access, permissions, quotas, stable IDs, form ownership, sync schedule and error recovery. Do not promise the integration before feasibility is verified. |
| O-010 | What is the source of truth for imported registrations? | Start by evaluating one-way import into CampusOps; defer two-way sync. | Reduces conflicts until a specific two-way editing need is demonstrated. |
| O-011 | How are team participants represented? | Team record plus individual participant records linked to the team; each individual has an independent check-in state. | Enables partial arrival and accurate attendance. |
| O-012 | Does check-in need to work offline? | Keep offline mode undecided until venue network, volume and recovery needs are researched. | Offline operation requires conflict resolution and trustworthy synchronization; do not claim support until tested. |
| O-013 | Can all workspace members see each other's email addresses? | Show basic roster information by default; limit contact details to roles that need them unless the organization chooses a documented wider policy. | The founder requests cross-event roster visibility, but contact-detail visibility is a separate privacy decision. |
| O-014 | How long are attendee records and proof files retained? | Define retention by data type and organization/event needs before real data is stored. | Data minimization, privacy, storage cost and deletion obligations depend on the policy. |
| O-015 | Which capabilities belong in the first implementation slice? | Prioritize a complete standalone workflow, then program/multi-event workflow, while retaining architecture compatibility. | Finalize only after requirements review, security planning and effort estimates; academic workload is a constraint. |

## Requirement conflicts or ambiguities to resolve

1. **Workspace administration and individual authority:** The organization-workspace and individual-account model is confirmed. Remaining work is to specify who can create, administer, recover, and transfer ownership of the workspace, while preserving action attribution when office bearers change.
2. **Invitee role selection:** An invitation should tell the invitee their assigned role, but they should not be able to grant themselves elevated permissions. Confirm if the role shown is only acknowledged or if invited users can request a change.
3. **“Everyone can see all members” vs email privacy:** Define whether the shared roster shows names/roles/departments/events only, or also email addresses.
4. **Task rejection state:** The task must remain non-completed and preserve its working state and review history; a rejected proof must never mark it complete.
5. **Multi-event shared departments:** The department list is common to child events, but each coordinator's event assignment and permissions must remain explicit. Shared department names do not imply access to every event automatically.

## Proposed account/invitation lifecycle defaults (v0.3)

These are **recommendations for review, not founder-confirmed decisions**:

1. **Account model:** the first creator uses a personal account. The club is an organization workspace/profile, not a separate login. The first verified creator becomes the initial Primary Workspace Administrator.
2. **Verification:** verify the user's email and separately verify the club/organization. The organization-verification method remains open. A workspace is not treated as verified until the required organization check passes.
3. **Admin continuity:** retain at least one active administrator; prompt the organization to add a second trusted administrator; do not allow removal of the last administrator without a transfer/recovery path.
4. **Invitations:** bind invitations to one email, organization workspace, role, and allowed department/event/program scope; proposed expiry is seven calendar days; tokens are single-use; cancel/resend invalidates the old link.
5. **Existing accounts:** invitees who already have a personal account sign in and accept; do not create a second account for the same person merely to join a new organization.
6. **Role confirmation:** the invitee reviews and acknowledges the inviter-assigned role. They can request correction but cannot elevate their own privileges.
7. **Membership versus directory:** the current office-bearer/faculty directory and actual workspace membership are separate. Updating a title does not silently change access, and removing a membership does not delete the person's account or historical actions.
8. **Transfer and recovery:** transfer primary administration only to an active verified member with explicit acceptance; emergency recovery must verify control of the individual account and legitimacy of the organization.
9. **Auditability:** record invitation creation/cancellation/acceptance, role and scope changes, member suspension/removal, and administrator transfers with actor and timestamp.

## Updated account-related decision gates

- Choose the acceptable evidence and process for verifying a college/club workspace.
- Confirm whether seven-day invitation expiry is acceptable or should be configurable by policy.
- Define whether role/scope increases require explicit re-acceptance by the member.
- Specify emergency administrator recovery and the status of the former administrator after transfer.
- Specify whether administrator MFA is required at initial release or mandatory before production with sensitive records.

## Risk register summary

| Risk ID | Risk | Mitigation |
|---|---|---|
| R-001 | Workspace administration is lost or mishandled when the initial administrator or office bearers change. | Use individual identities and scoped workspace membership; define a workspace-administrator transfer/recovery path; preserve historical action attribution. |
| R-002 | Invitation link is forwarded or role/scope is changed. | Bind secure expiring token to the invitee, workspace, role and scope; enforce server-side. |
| R-003 | Incorrect department/event assignments leave tasks orphaned or expose restricted records. | Validate assignment scope on every write; block invalid edits or require reassignment. |
| R-004 | Task marked complete without approval. | Enforce allowed state transitions server-side and audit the reviewer decision. |
| R-005 | Team registration is incorrectly treated as all members present. | Individual participant records and individual check-in states. |
| R-006 | External registration import creates duplicates or stale records. | Stable source IDs, idempotent import, sync status, review queue and recovery tests. |
| R-007 | Cross-event roster exposes unnecessary personal data. | Separate basic roster visibility from contact details and operational permissions. |
| R-008 | Product scope expands beyond available time. | Documentation-first, phased implementation after requirements are reviewed; no prototype/code work without explicit request. |

## Change log

| Version | Change |
|---|---|
| 0.1 | Captures current product direction, founder-specific workflow decisions, unresolved questions and recommended defaults after Requirements Specification v0.5. |
| 0.2 | Recorded the founder's confirmation that CampusOps uses an organization workspace with individual named accounts and no shared club login; closed the identity-model decision and retained workspace administration/recovery as open. |
| 0.3 | Added recommended account onboarding, primary-administrator continuity, secure invitation expiry/reissue, existing-account acceptance, membership separation, transfer and recovery policies. These are explicitly proposals pending founder confirmation. |
