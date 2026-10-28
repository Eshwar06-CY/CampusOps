# CampusOps — Founder Approval Checklist

**Version:** 0.2  
**Status:** Founder approval recorded for FA-001–FA-009  
**Purpose:** Resolve the small set of product-policy decisions that materially affect the requirements, permissions, data model, and API contract.  
**Mode:** Documentation and product planning only. This document does not authorize implementation.

## Confirmed product directions (not reopened by this checklist)

- CampusOps covers event preparation, backend operations, event-day execution and registration/check-in, and post-event documentation.
- Marketing/promotion management is out of scope.
- Participant-facing doubt/question/issue submission is out of scope.
- Every organization uses a workspace with individual accounts; no shared club login.
- A workspace supports both standalone events and multi-event programs, with different setup/team workflows.
- Standalone events have event-specific departments and department leads.
- Multi-event programs have shared departments, event leads assigned to individual events, and coordinators assigned to departments and relevant work.
- Active tasks have specific deadlines and owners. A completion submission requires file or link evidence and authorized review; approval is required before status becomes completed, and rejection requires a note and notification.
- Solo and team registrations result in individual participant records and each participant is checked in individually.
- Native registration and external registration integrations are both desired; provider and synchronization design remain open.
- The founder has asked for requirements/documentation work only. No prototype, implementation, installation or integration work is authorized unless explicitly requested.

## Decisions requiring approval

For each item, reply **Approve default** or provide a change. These recommendations are not treated as approved until the founder confirms them.

### FA-001 — Who can review task evidence?

**Recommended default**
- A lead can review tasks inside the scope assigned to them.
- Authorized office bearers/core members can review if they have explicit review permission for that scope.
- A person cannot approve their own evidence submission.
- A backup reviewer is explicitly assigned for each task/department/event scope or is resolved through a documented escalation rule.
- Rejection requires a reason; the submission and decision remain in the history; the assignee is notified.

**Founder response:** ✅ Approved default — 28 October 2026  
**Change:** None recorded.

### FA-002 — How should permissions and role inheritance work?

**Recommended default**
- Permissions are explicit and scoped to organization, program, event, department, or task as appropriate.
- An organization-level role does not automatically grant access to every participant record, evidence file, or private field in every event.
- Multi-event members can see the cross-event basic directory (name, assigned role, department, and event assignment), consistent with the founder's stated workflow.
- Private contact details and protected operational records are restricted to users with an operational need and suitable permission.
- Role names can be customized, but each role maps to a defined permission set; users cannot grant themselves extra permissions.

**Founder response:** ✅ Approved default — 28 October 2026  
**Change:** None recorded.

### FA-003 — Which contact details can workspace members see?

**Recommended default**
- All active members of a multi-event program can view basic member identity, role, department, and event assignments.
- Email address and phone number are visible only to authorized roles or users who need them to coordinate assigned work.
- Participant personal data is not exposed through the team directory.

**Founder response:** ✅ Approved default — 28 October 2026  
**Change:** None recorded.

### FA-004 — How should task deadlines be handled?

**Recommended default**
- Every active task has a specific deadline. A task cannot be active without an owner and a due date/time.
- The event's configured timezone is the reference for displaying and interpreting deadlines.
- An assignee requests a deadline change with a reason; an authorized lead/office bearer decides within scope.
- A specially authorized administrator may change a deadline directly, but the change must record old value, new value, actor, time, reason, and notify affected people.
- Deadline edits use an explicit audited operation; generic task edits cannot bypass the rule.

**Founder response:** ✅ Approved default — 28 October 2026  
**Change:** None recorded.

### FA-005 — What is the check-in lookup and correction policy?

**Recommended default**
- Staff can check in a person using a registration ID or QR code, with a name/search fallback for exceptions.
- Check-in is stored per individual participant per event, including participants who registered as part of a team.
- Duplicate check-ins are blocked or handled idempotently with a clear “already checked in” state.
- A mistaken check-in is corrected/voided with a reason and audit history, not physically deleted.
- Walk-ins are entered as new or staff-created registrations under the event's permitted policy; they must not be treated as verified registrations without the required fields/approval.

**Founder response:** ✅ Approved default — 28 October 2026  
**Change:** None recorded.

### FA-006 — What should happen when the network is unavailable at check-in?

**Recommended default for the first pilot**
- Do not promise a full offline-capable check-in system in the first release until it is designed and tested.
- Document a manual fallback process for event staff and a safe reconciliation process afterward.
- Before a real pilot, test degraded connectivity and make the limitation visible to organizers.

**Founder response:** ✅ Approved online-first approach with documented manual fallback — 28 October 2026. Full offline capability is not promised unless designed and tested.

### FA-007 — How should external registrations match internal participants?

**Recommended default**
- Native and imported registration records pass through one internal validation/persistence path.
- Preserve the external provider's record/form identifier and import history.
- Use a stable provider record ID to prevent replay duplicates where available.
- Do not merge records solely because email addresses match. Potential matches/conflicts should be reviewed according to a documented rule.
- Group/team registration is separate from its individual participant records; check-in remains individual.
- Define a roster-edit cutoff per event if needed; changes after the cutoff are audited and may require authorized review.

**Founder response:** ✅ Approved default — 28 October 2026. All roster changes are audited. A cutoff may be configured per event; if configured, post-cutoff changes require authorized review. External provider and sync direction remain open.

### FA-008 — Should internal staff-only blockers remain in scope?

The participant-facing issue/question submission module is confirmed out of scope. This is a separate question: whether team members need a private way to record an operational blocker (for example, a room is locked or required equipment has not arrived) and assign it to staff.

**Recommended default:** Keep a lightweight staff-only operational blocker record linked to an event/task, with an owner, status and resolution history. Do not expose it as a participant-facing ticket or query portal.

**Founder response:** ✅ Keep lightweight staff-only operational blockers — 28 October 2026. Participant-facing issue/question/request submission remains out of scope.

### FA-009 — Invitation expiry

**Recommended default**
- Invitation links are single-use, bound to the intended email, organization/workspace and granted scope, and can be revoked.
- Suggested expiry: seven days. Resending issues a new token or safely refreshes the invitation without creating duplicate membership.
- Invitation delivery status is distinct from acceptance; failed delivery must not create membership.

**Founder response:** ✅ Approve seven-day expiry — 28 October 2026.

## Additional founder-approved closure policies (FPC-01–FPC-05)

On 28 October 2026, the founder explicitly approved all five closure defaults.

### FPC-01 — Passive attendee information
**Approved:** Event schedule, venue, rules and instructions may be published as read-only attendee information. No attendee-submitted questions, doubts, issues or requests; no ticket portal.

### FPC-02 — Organization verification
**Approved:** Creator must verify email and provide organization/club details. A CampusOps platform administrator reviews an official institution/club page or domain, or faculty-coordinator confirmation when public evidence is insufficient. Minimize evidence; no identity-document upload by default. Rejections give a reason and resubmission path.

### FPC-03 — Initial workspace administrator
**Approved:** The verified-email creator becomes Primary Workspace Administrator of the pending workspace, with privileged actions limited until organization verification passes. Workspace verification does not validate later members' roles automatically.

### FPC-04 — Authentication candidate
**Approved:** Evaluate Supabase Auth as the preferred candidate for email/password, email verification, password recovery and TOTP MFA; FastAPI validates access tokens server-side. Business permissions remain in CampusOps tables. This approval does not bypass the required feasibility/security check before final provider lock.

### FPC-05 — MFA and account recovery
**Approved:** MFA is required for CampusOps platform operators; workspace primary administrators must enrol MFA before real participant data is used in a pilot. Ordinary recovery uses provider-managed verified-email recovery. Sensitive workspace recovery requires documented review using independent organization evidence, notification of established contacts, session revocation, and invalidation of outstanding invitations/reset links.

**Implementation caveat:** Operational runbooks, technical tests and provider feasibility remain to be completed. Approval of these policies does not authorize implementation.

## Defer until provider/hosting evaluation

These decisions are outside FA-001–FA-009 and remain open; they should not be silently inferred from the approval:

- Authentication/identity provider.
- Transactional email/notification provider.
- Private evidence/file-storage provider and maximum file size/type policy.
- Hosting provider/region and cost limits.
- Backup schedule, recovery objectives, and verified restore procedure.
- First external registration integration (Google Forms is a candidate, not yet selected) and its supported read/write direction.
- Exact API route names and final physical database schema.

## Post-approval result

The nine FA decisions and FPC-01–FPC-05 have been recorded in `CampusOps_Decision_Log_v1.3.md`, `CampusOps_PRD_v1.1.md` and `CampusOps_Technical_Specification_v1.1.md`. Supabase Auth remains the preferred candidate pending feasibility/security evaluation; email/storage/hosting providers, physical schema/API contracts, performance/recovery targets and operational runbooks remain open. Implementation is not authorized by this checklist.

## Approval record

| Decision ID | Status | Recorded outcome |
|---|---|---|
| FA-001 | Approved | Scoped review, no self-approval, backup/escalation, reason/history/notification on rejection |
| FA-002 | Approved | Explicit scoped permissions; role-to-permission mapping; no self-grant or implicit private child-event access |
| FA-003 | Approved | Basic directory workspace-wide; email/phone limited by operational need; participant data excluded |
| FA-004 | Approved | Required owner and deadline; event timezone; requested changes approved within scope; direct admin changes audited/notified |
| FA-005 | Approved | QR/registration ID plus search fallback; individual check-in; duplicate prevention; audited corrections; controlled walk-ins |
| FA-006 | Approved | Online-first with documented manual fallback; no offline claim before design/testing |
| FA-007 | Approved | Stable source IDs, idempotent imports, no merge solely by email, review ambiguous matches, audit roster edits and optionally configure cutoff |
| FA-008 | Approved | Staff-only internal blockers remain; participant-facing request/issue portal excluded |
| FA-009 | Approved | Single-use, scoped, revocable invitation with seven-day expiry; safe resend and separate delivery/acceptance states |


**Version history:** v0.2 recorded founder approval of FA-001–FA-009. Version 0.3 records the founder’s explicit approval of FPC-01–FPC-05 on 28 October 2026. Supabase Auth is approved as the preferred candidate pending feasibility/security evaluation; other technical choices remain open. Neither approval authorizes implementation.
