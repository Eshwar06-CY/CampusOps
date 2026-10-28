# CampusOps — Product Decision Log v1.2

**Version:** 1.2  
**Updated:** 28 October 2026  
**Status:** Consolidated; FA-001–FA-009 approved by founder; implementation-readiness review recommends NO-GO until gates close and explicit authorization is given.  
**Working mode:** Product documentation only; implementation has not been authorized by this log.

## 1. Confirmed product direction

1. CampusOps covers event preparation, backend operations, event-day execution and registration/check-in, and post-event documentation.
2. Marketing/promotion management, poster/reel creation and social-media publishing are out of scope.
3. Participant-facing doubt/question/request/issue submission is out of scope.
4. Staff-only operational blocker tracking remains in scope as an internal workflow, distinct from a participant ticket portal (FA-008).
5. Each organization uses a workspace with individual accounts; no shared club login.
6. Standalone-event and multi-event program setup use different user journeys but shared concepts where appropriate.
7. Standalone: event-specific departments and department leads; leads manage their departments and assigned work within scope.
8. Multi-event: a program contains child events, common shared departments, and leads assigned to individual child events; no separate department lead is created by default for each shared department.
9. Office bearers and authorized core members can add coordinators and assign tasks to leads or coordinators within granted permissions.
10. Active tasks require owners and specific deadlines; assignees submit proof as a file or link; authorized review is required before completion. Rejection requires a reason and notification.
11. Workspace members can see basic people/role/department/event assignments across the workspace; private email/phone details and participant records are restricted by need and permission (FA-003).
12. Native registration and selected external registration integrations are desired. Provider/sync direction remains open.
13. Solo/team registration must preserve individual participant records and an individual check-in per person.
14. The founder asked for documentation and planning, not prototypes or application implementation unless explicitly authorized.

## 2. Founder-approved foundational decisions

On 28 October 2026, the founder responded **“Approve all defaults”** to the nine decisions in `CampusOps_Founder_Approval_Checklist_v0.2.md`. Record these as approved:

| ID | Approved policy | Required treatment in all artifacts |
|---|---|---|
| FA-001 | Evidence reviews are done by authorized leads or core members within scope; submitters cannot approve their own proof; backup reviewer or documented escalation exists; rejection requires a reason; preserve history and notify assignee | Model review eligibility/state transitions; no self-approval; keep rejection non-completed |
| FA-002 | Explicit organization/program/event/department/task scopes; no implicit access to unrelated child-event private records; roles map to a defined permission set; users cannot grant themselves permissions | Enforce server-side scoped authorization and test privilege escalation |
| FA-003 | Basic workspace directory visible to members: name, role, department and event assignments; email/phone limited to authorized operational need; participant data excluded from general directory | Separate directory, contact and participant access |
| FA-004 | Active tasks require owner and specific deadline; event timezone is authoritative; assignee requests deadline changes with reason; authorized lead/office bearer decides; a specially authorized admin can make direct changes only with full audit and notification | Explicit, audited deadline-change operation; generic edits cannot bypass it |
| FA-005 | QR/registration ID lookup with name/search fallback; individual check-in per participant/event; duplicates blocked or idempotent; corrections/voids require reason and audit; walk-ins follow event rules and required validation | Atomic/idempotent check-in; retain correction history; no false “verified” state |
| FA-006 | Online-first with documented manual fallback; do not promise full offline check-in until designed and tested; test degraded connectivity before pilot | Offline is not a first-release promise; communicate pending/failed states honestly |
| FA-007 | Normalize native/external data; preserve stable source IDs/import history; idempotent imports; do not merge solely by email; review ambiguous matches; group and individual registration separate; audit roster edits; support configurable roster cutoff and require review for post-cutoff changes if a cutoff is configured | Provider/sync direction remains open; implement safe import/conflict rules once provider selected |
| FA-008 | Keep lightweight staff-only operational blockers; no participant-facing issue/question/request portal | Do not add public ticket/request endpoints |
| FA-009 | Invitations are single-use, bound to intended email/workspace/role/scope, revocable, expire after seven days; resend safely issues/refreshes invitation; failed email delivery does not create membership | Token state machine and unique membership constraints; delivery and acceptance are separate states |

## 3. Proposed account/security rules that remain open

These were written in requirements v0.9 but were **not part of the nine approved decisions** and must not be silently marked confirmed:

- Exact college/club verification evidence, verification reviewer, rejection/appeal and renewal/update path.
- Authentication provider and exact sign-up/email verification flow.
- Who becomes the initial Primary Workspace Administrator after organization verification.
- Detailed administrator transfer, emergency recovery evidence and service review path.
- Whether workspace administrator MFA is mandatory before production; re-authentication for high-impact actions should be evaluated.
- Personal account recovery controls and session-revocation policy.

The organization workspace with individual accounts/no shared login is confirmed; these detailed procedures are not.

## 4. Technical decisions still open

- Authentication/identity provider (managed identity is a recommendation, not selected).
- Database hosting/region and deploy provider; PostgreSQL is proposed but hosting selection remains open.
- File/object storage provider, allowed file types/size, malware scanning, link-access rules and retention/deletion policy.
- Transactional email/notification provider and channel/retry behavior.
- First external registration connector; Google Forms is a candidate, not selected.
- External integration direction (one-way import vs bidirectional); field ownership/source-of-truth mapping.
- Offline check-in: full offline is not promised; test online-first with manual fallback before pilot.
- Detailed permission bundles, role customization boundaries, exact backup reviewer fallback behavior, and API/physical schema names.
- Performance, backup recovery objectives, hosting cost envelope and data region.

## 5. Consolidated baseline artifacts

- `CampusOps_PRD_v1.0.md` — product vision, scope, requirements and acceptance tests.
- `CampusOps_Technical_Specification_v1.0.md` — proposed architecture, domain model, API/security principles and open technical gates.
- `CampusOps_Delivery_Plan_v1.0.md` — phases, epics, dependencies, tests, milestones and release gates.
- `CampusOps_Founder_Approval_Checklist_v0.2.md` — source of FA-001–FA-009 decisions and the founder's approval context.
- Earlier artifacts remain detailed design/history references: Requirements Specification v0.9, Role and Permission Matrix v0.1, Data Model v0.1, API Contract v0.2, Architecture Decision Record v0.2, and prior traceability reviews.

## 6. Change control

New decisions should record: decision ID, date, owner, context, options, chosen direction, rationale, affected requirements/data/API/tests/plan, risks and whether the decision is reversible. Changing an approved FA decision requires an explicit new decision and traceability updates. Do not treat a technical recommendation as founder approval.

## 7. Version history

| Version | Change |
|---|---|
| 1.1 | Records founder's explicit approval of FA-001–FA-009; separates them from account/security defaults and provider decisions that remain open; identifies consolidated PRD, technical specification and delivery plan as the current baseline. |


## 8. Implementation-readiness review outcome

**Review artifact:** `CampusOps_Implementation_Readiness_Review_v1.0.md`  
**Review date:** 28 October 2026  
**Outcome:** **NO-GO for application implementation at this time.** This is a readiness recommendation, not a new founder-approved product-policy decision. The founder has not authorized implementation.

The product direction and FA-001–FA-009 are stable. Before reconsidering implementation, close or explicitly defer the following gates with safe policies:

- Organization verification, initial workspace administrator and account recovery.
- Authentication/session policy and administrator MFA conditions.
- Final permission bundles and endpoint-to-acceptance-test traceability.
- Physical database constraints/migrations and final first-slice API operations.
- Evidence storage and transactional notifications (or safe deferral before those routes are shipped).
- Hosting, cost/data region, backups/restore and initial reliability targets appropriate to the test/pilot stage.
- Clarification of passive/read-only attendee information versus the excluded participant-facing question/issue/request portal.
- Reinspection of the development repository/environment at the time implementation is explicitly authorized.

The Google Forms integration and full offline check-in may remain deferred from the first native vertical slice if the deferment and interim workflow are documented. No code, prototype, installation, integration or deployment is authorized by the review or this log.

## 9. Change history

| Version | Change |
|---|---|
| 1.2 | Adds the 28 October 2026 implementation-readiness review recommendation and gates. Does not alter founder-approved FA-001–FA-009 or grant implementation authorization. |
