# CampusOps — Product Decision Log

**Version:** 0.1  
**Status:** Working log; decisions and recommendations are not all approved  
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
| D-008 | Team members invited as leads/coordinators create personal accounts separately from organization signup. | Confirmed direction | The organization-vs-personal identity model still needs clarification. |
| D-009 | Standalone setup has event-specific departments and a lead for each department. | Confirmed direction | A department lead may add members within authorized scope; office bearers/core members can assign work to leads or directly to coordinators. |
| D-010 | Multi-event setup has a common department list and event-level leads, not individual leads for each shared department. | Confirmed direction | Coordinators are assigned to shared departments and one or more permitted child events. |
| D-011 | Workspace members can view the cross-event roster in a multi-event workspace. | Confirmed with privacy boundary open | Base fields such as name, role, department and event scope can be visible; broader contact details require an explicit policy. |
| D-012 | Each task has a specific deadline and proof is required before completion. | Confirmed direction | File or link evidence; a lead/core member reviews; approval marks complete; rejection keeps it non-completed, records a note and notifies the responsible person. |
| D-013 | Solo/team registration must verify every person individually. | Confirmed direction | A team is not checked in as a single all-or-nothing attendance record. |
| D-014 | Requirements work should precede implementation. | Confirmed instruction | Do not create or revise prototypes, code, installations, or integrations unless the founder explicitly requests them. |

## Open decisions and recommended defaults

| ID | Open decision | Recommended default to evaluate | Why it remains open / decision gate |
|---|---|---|---|
| O-001 | Does “club account” mean a shared login or an organization workspace administered by named users? | Treat the club as a workspace and each human actor as an individual account; grant office bearers/core members permissions through membership/roles. | Shared credentials make attribution, revocation, audit logs and account recovery difficult. Confirm the intended access pattern before freezing authentication requirements. |
| O-002 | Which people can administer the leadership directory and transfer workspace administration? | Limit to authorized organization administrators; require a documented transfer flow when tenures change. | Leadership changes should not accidentally remove the only administrator or transfer historical ownership. |
| O-003 | What does an invitee's stated role mean? | Role is assigned by the inviter and shown for acknowledgment; invitee cannot self-select elevated permissions. | User's workflow says invitee selects the informed role; allowing unconstrained choice would permit privilege escalation. |
| O-004 | How long do invitations remain valid, and how are cancellation/resend handled? | Expiring, single-use invitation token bound to email, workspace, role and scope. | Exact expiry, resend, duplicate invite, existing-account and email-change behaviors must be specified. |
| O-005 | Can the same person be assigned to multiple departments/events? | Allow multiple scoped memberships/assignments where authorized. | Must prevent ambiguous ownership, conflicts and access leakage. |
| O-006 | Should a department lead in the standalone workflow be able to assign tasks to anyone in the whole event or only within their department? | Restrict to their department by default; allow broader scope only through explicit permissions. | Validate against the founder's intended operational hierarchy and prevent excessive access. |
| O-007 | Who may approve proof submitted by a lead? | Permit only reviewers explicitly authorized for that task scope; require a different reviewer when separation of duties is needed. | Avoid self-approval conflicts while allowing efficient operations for small clubs. |
| O-008 | What proof formats and limits are accepted? | File attachments and HTTPS links initially; define supported file types, size limits, malware checks, and link handling before production. | Storage, safety and review effort depend on the formats. |
| O-009 | What happens if a task's proof is rejected? | Preserve the task as non-completed, record the reviewer note, notify the owner, and allow resubmission. | The workflow must not make rejection look like completion or erase history. |
| O-010 | Which external registration source is first? | Investigate Google Forms first because it matches the currently described workflow. | Verify current API access, permissions, quotas, stable IDs, form ownership, sync schedule and error recovery. Do not promise the integration before feasibility is verified. |
| O-011 | What is the source of truth for imported registrations? | Start by evaluating one-way import into CampusOps; defer two-way sync. | Reduces conflicts until a specific two-way editing need is demonstrated. |
| O-012 | How are team participants represented? | Team record plus individual participant records linked to the team; each individual has an independent check-in state. | Enables partial arrival and accurate attendance. |
| O-013 | Does check-in need to work offline? | Keep offline mode undecided until venue network, volume and recovery needs are researched. | Offline operation requires conflict resolution and trustworthy synchronization; do not claim support until tested. |
| O-014 | Can all workspace members see each other's email addresses? | Show basic roster information by default; limit contact details to roles that need them unless the organization chooses a documented wider policy. | The founder requests cross-event roster visibility, but contact-detail visibility is a separate privacy decision. |
| O-015 | How long are attendee records and proof files retained? | Define retention by data type and organization/event needs before real data is stored. | Data minimization, privacy, storage cost and deletion obligations depend on the policy. |
| O-016 | Which capabilities belong in the first implementation slice? | Prioritize a complete standalone workflow, then program/multi-event workflow, while retaining architecture compatibility. | Finalize only after requirements review, security planning and effort estimates; academic workload is a constraint. |

## Requirement conflicts or ambiguities to resolve

1. **Organization account vs individual authority:** The phrase “account for the club” could mean a shared login, while the workflow requires office bearers and core members to perform attributable actions. This must be resolved explicitly.
2. **Invitee role selection:** An invitation should tell the invitee their assigned role, but they should not be able to grant themselves elevated permissions. Confirm if the role shown is only acknowledged or if invited users can request a change.
3. **“Everyone can see all members” vs email privacy:** Define whether the shared roster shows names/roles/departments/events only, or also email addresses.
4. **Task rejection state:** The task must remain non-completed and preserve its working state and review history; a rejected proof must never mark it complete.
5. **Multi-event shared departments:** The department list is common to child events, but each coordinator's event assignment and permissions must remain explicit. Shared department names do not imply access to every event automatically.

## Risk register summary

| Risk ID | Risk | Mitigation |
|---|---|---|
| R-001 | Shared login prevents reliable accountability or safe access revocation. | Prefer individual identities with organization membership; confirm before architecture freeze. |
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
