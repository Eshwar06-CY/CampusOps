# CampusOps — Product Decision Log

**Version:** 1.0  
**Status:** Working log; confirmed directions separated from proposed defaults.  
**Mode:** Documentation and product planning only.  

## Confirmed product direction

1. CampusOps covers event preparation, backend operations, event-day execution and registration/check-in, and post-event documentation.
2. Marketing campaign management, promotional activity tracking, poster/reel creation, and social publishing are out of scope.
3. Participant-facing doubts, questions, or issue submission are out of scope.
4. CampusOps supports standalone events and multi-event programs with different setup and team structures, backed by connected operational concepts.
5. Each organization has a workspace and every office bearer/team member has an individual account. No shared club login.
6. Standalone workflow: event departments are defined; leads are assigned to departments; leads can manage their department members and tasks within granted permissions; office bearers/core members can assign work to leads or coordinators.
7. Multi-event workflow: a parent program contains child events; departments are common to the program; leads are assigned to individual events and there are no department leads by default; coordinators are assigned to departments and specific event work.
8. Tasks have specific deadlines, owners and progress tracking. Proof-required completion needs file/link evidence and authorized review. Rejection needs a note, preserved history, a non-completed status and notification.
9. Workspace members can view people across the workspace's events. Exact exposure of email/phone remains unconfirmed.
10. Registration can be native or integrated with an external source. Team/solo registration must lead to individual participant records and per-person check-in.
11. Post-event records include event details, registration and actual attendance, supporting evidence, reports and closure status.
12. The founder asked for requirements/documentation planning; do not build prototypes, write application code, install dependencies or implement integrations unless explicitly requested.
13. An organization workspace with individual accounts and appropriate permissions is confirmed.
14. The founder explained that participant-facing doubt/issue raising should be removed; whether a separate staff-only operational blocker tracker remains in scope is not yet confirmed.

## Current artifact baseline

- Requirements Specification v0.9.
- Role and Permission Matrix v0.1.
- Data Model and Relationship Map v0.1.
- Architecture Decision Record v0.2.
- Architecture Traceability Review v0.1.
- Foundational Workflow Decision Matrix v0.1.
- Foundational Workflow Reconciliation v0.1.
- API Contract Draft v0.2.
- API Contract Traceability Review v0.1.

These are working drafts; they have not all been finalized together for implementation.

## Founder approval gate

Created `CampusOps_Founder_Approval_Checklist_v0.1.md` to consolidate nine implementation-relevant policy choices:

- FA-001 reviewer authority, self-review and backup review.
- FA-002 permission scopes/inheritance.
- FA-003 member contact visibility.
- FA-004 deadline authority, audit and timezone handling.
- FA-005 check-in lookup, corrections and walk-ins.
- FA-006 offline/degraded-network policy.
- FA-007 external registration matching and roster changes.
- FA-008 staff-only operational blockers versus no issue tracking.
- FA-009 invitation expiry.

All nine are **awaiting founder review**. The recommendations in the checklist must not be treated as approved decisions until the founder confirms them.

## Recommended defaults (not yet founder-approved)

| ID | Topic | Recommended default | Status |
|---|---|---|---|
| FWD-001 | Proof review | Authorized reviewer within scope; submitter cannot approve own evidence; rejection requires a note; history and notification retained. | Proposed |
| FWD-002 | Permission scope | Explicit organization/program/event/department/task scope; no implicit inheritance into private child-event records. | Proposed |
| FWD-003 | Team registration | Separate group registration from individual participants; check-in per individual per event; idempotent duplicate handling. | Proposed |
| FWD-004 | Roster privacy | Workspace-wide basic member directory; personal email/phone restricted by default. | Proposed |
| FWD-005 | Deadlines | Specific deadline with event-timezone context; changed deadlines require actor, reason, history and notification. | Proposed |
| O-001 | Reviewer authority | Leads and authorized core members review within scope, excluding self-review; backup review flow defined. | Awaiting founder review |
| O-002 | Backup review | Explicit backup reviewer or documented escalation rule. | Awaiting founder review |
| O-003 | Registration roster changes | Audited changes; event-configured cutoff if selected. | Awaiting founder review |
| O-004 | Check-in lookup | Registration ID/QR with name/search fallback. | Awaiting founder review |
| O-005 | Deadline authority | Assignees request changes; authorized reviewers decide; designated admins may have audited direct-change authority. | Awaiting founder review |
| O-006 | Contact visibility | Basic directory fields visible to program members; private contacts restricted by operational need. | Awaiting founder review |
| O-007 | Invitation expiry | Single-use, scope-bound invitation; proposed seven-day expiry. | Awaiting founder review |
| O-008 | Organization verification | Email verification separately from club/organization verification; process not selected. | Open |
| O-009 | Identity provider | Managed identity provider preferred; provider not selected. | Open |
| O-010 | Registration integration | Google Forms is a candidate; provider, sync direction and matching policy not selected. | Open |
| O-011 | Offline check-in | Online-first with manual fallback is recommended for first pilot; not approved. | Awaiting founder review |
| O-012 | Internal staff-only blockers | Separate from participant-facing issue submission; scope decision pending. | Awaiting founder review |

## Change log

| Version | Change |
|---|---|
| 0.8 | Added API contract draft and separated proposed endpoint/resource behavior from unresolved permissions and provider choices. |
| 0.9 | Added API traceability review findings and recorded API contract draft v0.2 as the review baseline. |
| 1.0 | Consolidated nine founder decisions into an approval checklist; no recommendation in that checklist is considered approved yet. |
