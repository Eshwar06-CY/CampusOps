# CampusOps — Final Pre-Implementation Closure Plan v1.1

**Date:** 28 October 2026  
**Status:** FPC-01–FPC-05 approved by founder; FPC-06–FPC-12 remain recommendations or deferrals pending explicit decisions  
**Purpose:** Close the remaining documentation-stage gaps without creating an endless sequence of new artifacts.

## 1. Is this the final documentation stage?

This is intended to be the final planned documentation artifact before making a fresh implementation go/no-go decision. It is not the last stage of the overall project: implementation, testing, deployment and pilot readiness would still follow if authorized.

The nine founder-approved policies FA-001 through FA-009 remain approved. The founder has now also explicitly approved the recommended defaults for FPC-01 through FPC-05. FPC-06 through FPC-12 remain recommendations or deferrals until separately approved or safely deferred for a specific implementation slice.

## 2. Product baseline — keep unchanged

CampusOps is an event-operations workspace for both standalone events and multi-event programs. It covers event preparation and backend coordination, event-day operations, registration and individual check-in, task ownership/deadlines/evidence review, staff-only operational blockers, and post-event reports/evidence/closure.

Explicit exclusions remain: marketing campaign management, poster/reel creation and publishing, promotional activity tracking, and participant-facing question/doubt/issue/request submission.

Organizer-published attendee information (schedule, venue, rules and instructions) is approved as read-only information. Participant-submitted questions, issues, doubts and requests remain out of scope; this is not a request/ticket portal.

## 3. Closure decisions and remaining recommendations

FPC-01 through FPC-05 were explicitly approved by the founder on 28 October 2026. FPC-06 through FPC-12 below remain proposed defaults or deferrals, not founder-approved decisions.

| ID | Issue | Approved policy / recommended default | Status | Must be settled before |
|---|---|---|---|---|
| FPC-01 | Passive attendee information | Include organizer-published, read-only schedule, venue, rules and instructions. Exclude participant-submitted questions, issues, doubts and requests. The organizer controls what is published. | Founder-approved | Detailed UX/API scope |
| FPC-02 | Organization verification | A new workspace begins in `pending_verification`. Require creator email verification and organization/club details. A CampusOps platform administrator reviews one reasonable evidence path: official institution/club page or domain, or faculty-coordinator confirmation when public evidence is insufficient. Collect the least information needed; do not require identity-document uploads by default. On rejection, provide a reason and resubmission path. | Founder-approved | Authentication/onboarding implementation |
| FPC-03 | Initial workspace administrator | The verified-email creator is the Primary Workspace Administrator for the pending workspace. Keep privileged actions limited until organization verification passes. Verification activates the workspace; it does not automatically verify every later member's role. | Founder-approved | Authentication/onboarding implementation |
| FPC-04 | Authentication provider | Approved preferred candidate: managed Supabase Auth for email/password, email verification, password recovery and TOTP MFA, with FastAPI validating access tokens server-side. Keep business authorization in CampusOps membership/permission tables; never trust client-supplied roles. Run a small feasibility/security check before locking the provider. | Founder-approved as preferred candidate; feasibility check required | First real sign-in implementation |
| FPC-05 | MFA and account recovery | Require MFA for CampusOps platform operators. Require workspace primary administrators to enrol MFA before real participant data is used in a pilot. Use provider-managed verified-email recovery for ordinary accounts; sensitive workspace recovery requires separate, documented review based on independent organization evidence, notification of established contacts, session revocation and invalidation of outstanding invitations/reset links. | Founder-approved | Real-data pilot |
| FPC-06 | Email delivery | Keep an email-provider adapter. Use a development/test mailbox locally. Select and test a transactional email provider before sending real invitations or recovery messages; delivery status must not be confused with invitation acceptance. | Open / defer as documented | Invitation end-to-end testing / pilot |
| FPC-07 | Evidence file storage | Use private object storage, scoped authorization and short-lived access links. Validate size/type server-side, preserve evidence/review history, avoid public object URLs, and define retention/deletion rules before real evidence is uploaded. | Open / defer as documented | File-evidence implementation / pilot |
| FPC-08 | First external registration connector | Implement and verify the native registration path first. Treat Google Forms as the first candidate for a later connector, not a committed integration until API access, field mapping, stable source IDs, sync direction, retries and conflict review are proven. | Open / defer as documented | Connector-specific phase |
| FPC-09 | Offline operation | Retain the approved online-first policy with a documented manual fallback. Full offline check-in remains out of first-release scope unless separately designed, reconciled and tested. | Open / defer as documented | Pilot runbook |
| FPC-10 | Hosting, database region and cost | Choose hosting/provider after checking the founder's budget, data-region requirements, environment separation, logs, backup/restore and likely free-tier limitations. Never store real participant data in an unreviewed free-tier setup. | Open / defer as documented | Hosted test or real-data pilot |
| FPC-11 | Physical schema and endpoint contracts | Before implementing a slice, finalize its tables, constraints, unique keys, transaction/idempotency behavior, API schemas, error responses, permissions and acceptance tests. Do not require every future feature's schema/API to be frozen before the first slice. | Open / defer as documented | Each implementation slice |
| FPC-12 | Performance/recovery targets | Define realistic expected event sizes and initial latency/recovery targets before pilot. Use synthetic data for load and failure tests; do not claim service-level objectives until measured. | Open / defer as documented | Pilot readiness |

### Notes on FPC-04 (provider candidate)

The founder approved Supabase Auth as the preferred candidate to evaluate, not as an irrevocable production-provider selection. Supabase is a candidate because it offers managed authentication and PostgreSQL within one ecosystem; its current official pricing page lists a free tier but also notes resource limits and that free projects may pause after a week of inactivity. Therefore it may be suitable for development/portfolio evaluation, but should not be assumed suitable for a real event-day production workload without a cost, availability, region and recovery review. See sources in section 8.

## 4. Permission and workflow closure rules

Use these as the first-release implementation baseline:

- Authorization is deny-by-default and checked server-side for the exact resource scope.
- Roles are configurable labels mapped to explicit permissions; membership and role grants are distinct records.
- Standalone event department leads can manage their assigned departments. Multi-event program leads are assigned to specific child events; shared departments do not automatically grant access to all child-event private records.
- Office bearers/core members can assign tasks within explicitly granted scope. Department/event leads can assign within their scope. Cross-scope assignment requires an explicit permission.
- A proof-required task is `submitted_for_review`, not `completed`, when evidence is submitted. Only a distinct authorized reviewer can approve it; no self-approval. Rejection requires a reason, preserves history, and notifies the submitter. Backup reviewer/escalation must be configured or explicitly resolved by a policy.
- Task deadline changes use a dedicated audited action. Record old/new deadline, actor, reason, time and affected users; notify assigned people.
- A team registration has group/team data plus individual participant records. Check-in is one unique record per person per event; retries are idempotent. Corrections require authority, a reason and an audit record.
- Program-wide directory visibility exposes only approved basic fields; email/phone, participant records and private evidence require separate operational permissions.
- Internal blockers are staff-only. Passive event information may be displayed read-only; no participant-facing ticket or request workflow is added.

## 5. What can safely be deferred?

The following do not need to block the first local, synthetic-data vertical slice if they are kept behind explicit interfaces and are not misrepresented as complete:

- Google Forms or any other external registration integration.
- Full offline check-in; manual fallback stays documented.
- Production email provider; use a local development mailbox until provider selection, but test invitation state independently.
- Production hosting, custom domain, real event data and public launch.
- Advanced analytics/automation beyond event status, task progress, attendance reconciliation and close-out.

The following cannot be hand-waved for an implemented slice that uses them: authentication, organization/event authorization, the physical schema/constraints for that slice, safe file access if uploading evidence, and the exact API/state transitions for the tested workflow.

## 6. First vertical slice after explicit authorization

Implement one complete workflow, then expand. The proposed first slice is:

1. Individual sign-up/sign-in with verified email using the selected or feasibility-approved identity provider.
2. Create a workspace in pending-verification state and complete the defined verification process (or use a documented test fixture in local automated tests).
3. Create a standalone event and a multi-event program with two child events; configure departments and role-scoped memberships.
4. Invite one individual team member and test acceptance, expiry, revocation and existing-account behavior.
5. Assign a task with owner and exact deadline; submit link/file proof; reject with a reason; resubmit; approve with an authorized reviewer; preserve audit history.
6. Create native solo/team registration records; check in every participant individually; verify duplicate prevention and audited correction.
7. Complete event close-out and verify program summaries do not leak, merge or double-count child-event records.

Use synthetic data until security, retention, backup/restore and pilot gates are approved. External registration connector and full offline check-in are not part of this first slice.

## 7. Final readiness gate

The documentation stage can close when these are recorded:

- [x] Product vision and scope exclusions documented.
- [x] FA-001 through FA-009 explicitly approved by founder.
- [x] PRD, technical specification, delivery plan and current decision log consolidated.
- [x] Founder approved FPC-01 through FPC-05 on 28 October 2026: passive read-only attendee information; organization verification; initial Primary Workspace Administrator; Supabase Auth as preferred candidate pending feasibility/security evaluation; and MFA/account-recovery policy.
- [ ] Role/permission matrix reconciled against exact first-slice operations and reviewer escalation.
- [ ] First-slice physical schema and API operations are finalized with acceptance/negative-authorization tests.
- [ ] Current repository/environment is inspected only when implementation is authorized.
- [ ] Provider costs/limits and data region are checked for the intended environment; real-data pilot requirements are written.
- [ ] Founder separately authorizes implementation.

**Current decision remains NO-GO for implementation until the remaining gate is resolved and implementation is explicitly authorized.** This is not a no-go on CampusOps; it is a boundary between planning and building.

## 8. Current external references reviewed

- Supabase pricing and current free-tier limitations: https://supabase.com/pricing
- Supabase explanation of inactivity pausing: https://supabase.com/kb/faqs/platform/free-project-pausing
- Supabase Auth guide: https://supabase.com/docs/guides/auth
- Supabase JWT verification: https://supabase.com/docs/guides/auth/jwts
- Supabase TOTP MFA: https://supabase.com/docs/guides/auth/auth-mfa/totp
- OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- OWASP Forgot Password Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html

These references support technical feasibility/security considerations only; they do not constitute a selection or endorsement of a provider for production.

## 9. Version history

| Version | Change |
|---|---|
| 1.0 | Consolidates the remaining pre-implementation gates and recommends closure defaults. |
| 1.1 | Records founder approval of FPC-01–FPC-05. FPC-06–FPC-12 remain open recommendations or documented deferrals; implementation remains NO-GO until slice-level contracts/tests, environment review and explicit authorization are complete. |
