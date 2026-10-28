# CampusOps — Founder Approval Checklist

**Version:** 0.1  
**Status:** Awaiting founder review  
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

**Founder response:** ☐ Approve default  ☐ Change needed  
**If changing, specify:** ______________________________________________

### FA-002 — How should permissions and role inheritance work?

**Recommended default**
- Permissions are explicit and scoped to organization, program, event, department, or task as appropriate.
- An organization-level role does not automatically grant access to every participant record, evidence file, or private field in every event.
- Multi-event members can see the cross-event basic directory (name, assigned role, department, and event assignment), consistent with the founder's stated workflow.
- Private contact details and protected operational records are restricted to users with an operational need and suitable permission.
- Role names can be customized, but each role maps to a defined permission set; users cannot grant themselves extra permissions.

**Founder response:** ☐ Approve default  ☐ Change needed  
**If changing, specify:** ______________________________________________

### FA-003 — Which contact details can workspace members see?

**Recommended default**
- All active members of a multi-event program can view basic member identity, role, department, and event assignments.
- Email address and phone number are visible only to authorized roles or users who need them to coordinate assigned work.
- Participant personal data is not exposed through the team directory.

**Founder response:** ☐ Approve default  ☐ Change needed  
**If changing, specify:** ______________________________________________

### FA-004 — How should task deadlines be handled?

**Recommended default**
- Every active task has a specific deadline. A task cannot be active without an owner and a due date/time.
- The event's configured timezone is the reference for displaying and interpreting deadlines.
- An assignee requests a deadline change with a reason; an authorized lead/office bearer decides within scope.
- A specially authorized administrator may change a deadline directly, but the change must record old value, new value, actor, time, reason, and notify affected people.
- Deadline edits use an explicit audited operation; generic task edits cannot bypass the rule.

**Founder response:** ☐ Approve default  ☐ Change needed  
**If changing, specify:** ______________________________________________

### FA-005 — What is the check-in lookup and correction policy?

**Recommended default**
- Staff can check in a person using a registration ID or QR code, with a name/search fallback for exceptions.
- Check-in is stored per individual participant per event, including participants who registered as part of a team.
- Duplicate check-ins are blocked or handled idempotently with a clear “already checked in” state.
- A mistaken check-in is corrected/voided with a reason and audit history, not physically deleted.
- Walk-ins are entered as new or staff-created registrations under the event's permitted policy; they must not be treated as verified registrations without the required fields/approval.

**Founder response:** ☐ Approve default  ☐ Change needed  
**If changing, specify:** ______________________________________________

### FA-006 — What should happen when the network is unavailable at check-in?

**Recommended default for the first pilot**
- Do not promise a full offline-capable check-in system in the first release until it is designed and tested.
- Document a manual fallback process for event staff and a safe reconciliation process afterward.
- Before a real pilot, test degraded connectivity and make the limitation visible to organizers.

**Choose one:**
- ☐ Approve the online-first approach with documented manual fallback.
- ☐ Offline-capable check-in is a requirement for the first release.
- ☐ Other: _________________________________________________________

### FA-007 — How should external registrations match internal participants?

**Recommended default**
- Native and imported registration records pass through one internal validation/persistence path.
- Preserve the external provider's record/form identifier and import history.
- Use a stable provider record ID to prevent replay duplicates where available.
- Do not merge records solely because email addresses match. Potential matches/conflicts should be reviewed according to a documented rule.
- Group/team registration is separate from its individual participant records; check-in remains individual.
- Define a roster-edit cutoff per event if needed; changes after the cutoff are audited and may require authorized review.

**Founder response:** ☐ Approve default  ☐ Change needed  
**Roster-edit cutoff:** ☐ Event-configurable  ☐ No cutoff, but every change audited  ☐ Other: __________

### FA-008 — Should internal staff-only blockers remain in scope?

The participant-facing issue/question submission module is confirmed out of scope. This is a separate question: whether team members need a private way to record an operational blocker (for example, a room is locked or required equipment has not arrived) and assign it to staff.

**Recommended default:** Keep a lightweight staff-only operational blocker record linked to an event/task, with an owner, status and resolution history. Do not expose it as a participant-facing ticket or query portal.

**Founder response:** ☐ Keep staff-only blockers  ☐ Remove blocker tracking too  ☐ Revisit later

### FA-009 — Invitation expiry

**Recommended default**
- Invitation links are single-use, bound to the intended email, organization/workspace and granted scope, and can be revoked.
- Suggested expiry: seven days. Resending issues a new token or safely refreshes the invitation without creating duplicate membership.
- Invitation delivery status is distinct from acceptance; failed delivery must not create membership.

**Founder response:** ☐ Approve seven days  ☐ Choose another expiry: ______ days  ☐ Keep expiry configurable

## Defer until provider/hosting evaluation

These decisions do not need to block product-policy approval and should not be guessed now:

- Authentication/identity provider.
- Transactional email/notification provider.
- Private evidence/file-storage provider and maximum file size/type policy.
- Hosting provider/region and cost limits.
- Backup schedule, recovery objectives, and verified restore procedure.
- First external registration integration (Google Forms is a candidate, not yet selected) and its supported read/write direction.
- Exact API route names and final physical database schema.

## Recommended order after approval

1. Record founder responses in the decision log.
2. Update the requirements specification, role/permission matrix, data model, architecture decisions, and API contract consistently.
3. Run a final traceability check for mismatched role scopes, task states, registration identities, and check-in behavior.
4. Produce the PRD and implementation-ready acceptance criteria only after unresolved blockers are closed or explicitly deferred.
5. Do not begin implementation unless separately authorized by the founder.

## Approval record

| Decision ID | Status | Notes |
|---|---|---|
| FA-001 | Awaiting founder review | Reviewer authority and backup review |
| FA-002 | Awaiting founder review | Permission scope/inheritance |
| FA-003 | Awaiting founder review | Directory contact-field privacy |
| FA-004 | Awaiting founder review | Deadline authority and timezone |
| FA-005 | Awaiting founder review | Check-in lookup/corrections/walk-ins |
| FA-006 | Awaiting founder review | Offline/degraded connectivity |
| FA-007 | Awaiting founder review | External matching and roster edits |
| FA-008 | Awaiting founder review | Internal staff-only blockers |
| FA-009 | Awaiting founder review | Invitation expiry |
