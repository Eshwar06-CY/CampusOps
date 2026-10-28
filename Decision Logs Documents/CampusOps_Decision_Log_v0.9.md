# CampusOps — Product Decision Log

**Version:** 0.9  
**Status:** Working log; confirmed directions separated from recommendations.  
**Mode:** Product planning and documentation only.

## Confirmed product direction

1. CampusOps supports event preparation, backend operations, event-day coordination and registration/check-in, and post-event documentation.
2. Marketing campaign management, promotional activity tracking, poster/reel creation, and social publishing are out of scope.
3. Participant-facing doubts, questions, or issue submission are out of scope. A staff-only operational blocker capability is not included in the core API draft pending a separate decision.
4. CampusOps supports standalone events and multi-event programs with different setup and team structures, backed by connected operational concepts.
5. Each organization has a workspace and every office bearer/team member has an individual account. No shared club login.
6. Standalone workflow: event departments are defined; leads are assigned to departments; leads can manage their department members and tasks within granted permissions; office bearers/core members can assign work to leads or coordinators.
7. Multi-event workflow: a parent program contains child events; departments are common to the program; leads are assigned to individual events and there are no department leads by default; coordinators are assigned to departments and specific event work.
8. Tasks have specific deadlines, owners and progress tracking. Proof-required completion needs file/link evidence and authorized review. Rejection needs a note, preserved history, a non-completed status and notification.
9. Workspace members can view people across the workspace's events. Exact exposure of email/phone remains unconfirmed.
10. Registration can be native or integrated with an external source. Team/solo registration must lead to individual participant records and per-person check-in.
11. Post-event records include event details, registration and actual attendance, supporting evidence, reports and closure status.
12. The founder asked for requirements/documentation planning; do not build prototypes, write application code, install dependencies or implement integrations unless explicitly requested.
13. Organization workspace with individual accounts and appropriate permissions is confirmed.

## Recommended defaults, not yet founder-approved

| ID | Topic | Recommended default | Status |
|---|---|---|---|
| FWD-001 | Proof review | Authorized reviewer within scope; submitter cannot approve own evidence; rejection requires a note; history and notification retained. | Proposed |
| FWD-002 | Permission scope | Explicit organization/program/event/department/task scope; no implicit inheritance into private child-event records. | Proposed |
| FWD-003 | Team registration | Separate group registration from individual participants; check-in per individual per event; idempotent duplicate handling. | Proposed |
| FWD-004 | Roster privacy | Workspace-wide basic member directory; personal email/phone restricted by default. | Proposed |
| FWD-005 | Deadlines | Explicit date or timestamp with timezone context as needed; changed deadlines require actor, reason, history and notification. | Proposed |
| O-001 | Reviewer authority | Leads get review permission within assigned scope, excluding self-review; authorized office bearers can be reviewers if explicitly granted. | Proposed; needs approval |
| O-002 | Backup review | Define backup reviewer for unavailable/conflicted primary reviewers. | Proposed |
| O-003 | Registration roster changes | Maintain change history; changes after an event-defined cutoff may require review. | Proposed |
| O-004 | Check-in lookup | Unique registration/participant ID or QR plus name/search fallback. | Proposed |
| O-005 | Deadline authority | Authorized office bearer or relevant lead can change within scope; assignees request changes unless granted authority. | Proposed |
| O-006 | Contact visibility | Email/phone visibility restricted to operational need by default. | Proposed; founder decision needed |
| O-007 | Invitation expiry | Suggested seven-day expiry, single-use tokens bound to email and scope. | Proposed; founder decision needed |
| O-008 | Organization verification | Email verification separately from organization/club verification; approval process remains to be designed. | Proposed |
| O-009 | Identity provider | Managed identity provider preferred, provider not selected. | Proposed |
| O-010 | Registration integration | Google Forms is a candidate due to the current workflow; provider, sync direction and matching policy are not selected. | Proposed |
| O-011 | Offline check-in | Policy required before pilot; no offline guarantee assumed. | Open |

## API contract draft v0.1

Created `CampusOps_API_Contract_Draft_v0.1.md` as a provider-neutral REST-style contract proposal. It includes:
- Common path, pagination, response, error, and idempotency conventions.
- Identity, organization, verification, membership, invitations and role assignment.
- Standalone event, department lead, and team workflows.
- Multi-event program, shared departments, event-specific leads and coordinator assignment.
- Tasks, deadlines, proof submissions, review transitions and notifications.
- Native/external registrations, groups, individual participants, individual check-ins and correction paths.
- Post-event close-out and reporting.
- Security invariants, data-integrity rules, acceptance-test categories and remaining decision gates.

The API contract is a draft, not implementation authorization. Route names, providers, exact schemas, role bundles and unresolved rules remain subject to review.

## Remaining decision gates

### Before implementation-ready API/schema
- Reviewer authority, self-review prohibition, and backup review flow.
- Exact role/permission bundles and scope inheritance.
- Roster contact-field visibility.
- Registration participant fields, roster edit cutoff and identity matching.
- Check-in lookup, correction authority, walk-in handling and offline/degraded network policy.
- Proof-required vs proof-optional behavior and deadline editing authority/timezone handling.

### Before provider selection
- Identity/auth, email/notification, file storage, hosting region/budget, backups/restore, and external registration integration.

### Before pilot
- Authorization boundary tests, registration import replay, evidence review and self-review tests, concurrent check-in tests, privacy tests, data retention/deletion policy, backup/restore verification and event-day fallback instructions.

## Change log

| Version | Change |
|---|---|
| 0.8 | Added the provider-neutral API contract draft and separated its proposed endpoint/resource behavior from unresolved permissions and provider choices. No implementation decision made. |


## API contract traceability review — v0.9

Reviewed API contract v0.1 against Requirements Specification v0.9, Data Model and Relationship Map v0.1, Role and Permission Matrix v0.1, and Foundational Workflow Reconciliation v0.1. The resulting baseline is `CampusOps_API_Contract_Draft_v0.2.md`, supported by `CampusOps_API_Contract_Traceability_Review_v0.1.md`.

### Changes recommended/applied in API draft v0.2
- Separate office-bearer/faculty tenure records from account membership and access grants.
- Rename standalone department member routes to department assignments.
- Clarify cross-event basic roster visibility for active program-workspace members, without implying access to protected records.
- Make deadline and assignee changes use explicit auditable operations instead of generic PATCH.
- Align the canonical API task state to `submitted_for_review` with UI-label mappings.
- Clarify a single internal registration/participant model for native, staff-entered and imported registrations.
- Use auditable check-in void/correction rather than physical deletion.
- Add staff-only operational blocker routes to match CO-FR-012 while preserving the exclusion of public participant issue submission.
- Add invite-token secret hygiene and file-upload lifecycle to the explicit review gates.

### Findings requiring founder or later product decision
| ID | Decision/finding | Recommended treatment | Status |
|---|---|---|---|
| API-REV-011 | Proof reviewer authority | Leads in their permitted scope and authorized core members can review, but a submitter cannot approve own evidence; define backup reviewers. | Scope indicated by founder workflow; exact role mapping pending |
| API-REV-005 | Cross-event directory visibility | All active program-workspace members can see basic member identity, roles, departments and assigned events; private contacts and event records remain scoped. | Founder direction present; field-level privacy policy pending |
| API-REV-004 | Registration creation path | One canonical validation/persistence service; decide whether separate staff-created team registration endpoint is needed. | Open |
| API-REV-012 | Deadline policy | Specific deadline required for active tasks; direct changes audited; assignees request changes unless granted permission. | Open/pending confirmation |
| API-REV-008 | File upload lifecycle | Specify initiation, upload, completion, scan status, private retrieval and retention independently of provider choice. | Open |
| API-REV-014 | Invitation delivery failure | Delivery state/retry should not equal acceptance and must not duplicate membership. | Open |
| API-REV-003 | Staff-only operational blockers | Keep internal-only tracking if CO-FR-012 remains P0; never create public participant issue submission. | Recommended to preserve consistency; confirm in PRD |

### Status after review
- API contract remains **draft, not approved for implementation**.
- No providers are selected.
- No source code or prototype work was authorized by this review.
- Before freezing the API/schema, align task state enums, assignment entities, roster/tenure identity semantics, and operational blocker scope across all documents.

## Version history
| Version | Change |
|---|---|
| 0.9 | Added API contract traceability review findings and recorded API contract draft v0.2 as the next review baseline. |
