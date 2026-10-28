# CampusOps — Final Technical Closure Review v1.0

**Review date:** 28 October 2026  
**Purpose:** Decide what is closed, what can be safely deferred, and what must happen before the first implementation slice.  
**Mode:** Documentation and current public-documentation review only. No repository inspection, code changes, dependency installation, prototype or deployment was performed in this review.

## 1. Executive outcome

**Documentation: conditionally ready as an implementation baseline.** The product vision, scope, nine foundational workflow policies (FA-001–FA-009), and five closure policies (FPC-01–FPC-05) are recorded as founder-approved.

**Application implementation: NO-GO until the founder explicitly authorizes it and the current repository/environment is inspected.** This is an authorization and technical-gate boundary, not a rejection of CampusOps. The next step after authorization should be a short environment/feasibility check, followed by one small, testable vertical slice—not a large application generated all at once.

**Real participant data / live event pilot: NO-GO.** Hosting region, backup/restore evidence, email delivery, file retention/access controls, monitoring and operational recovery still need implementation and validation. A design document or provider webpage is not a passed test.

## 2. Founder-approved policies retained

- One organization workspace uses individual personal accounts; no shared club login.
- Standalone events use event-specific departments and department leads.
- A multi-event program has individual child-event records, shared program departments and event-scoped leads/assignments; program summaries must not merge source records or silently double-count people.
- Tasks have a responsible owner and specific deadline; deadline changes require authorization, reason, audit history and notifications.
- Proof-required work moves to review before completion. No self-approval; rejection requires a reason, retains history and notifies the submitter.
- Native registration is a required product capability; selected external integrations may be added later. Team/group registration remains separate from individual participant records.
- Every participant is checked in individually. Duplicate check-ins are handled safely; corrections require authority, reason and history.
- Directory-wide visibility exposes only approved basic fields. Email/phone, private evidence and participant data require appropriate permission.
- Lightweight staff-only operational blockers are in scope. Participant-facing questions, doubts, issue/request tickets, and marketing management are out of scope.
- The first pilot is online-first with a documented manual check-in fallback; full offline mode is not promised.
- Organization verification, initial Primary Workspace Administrator, read-only attendee information, preferred Supabase Auth candidate, MFA and recovery policies are approved as documented in FPC-01–FPC-05.
- FA-001–FA-009 and FPC-01–FPC-05 must not be silently altered by a technical recommendation.

## 3. Current technical evidence and recommended baseline

This section separates evidence from decisions. It does not lock a production provider.

### 3.1 Supabase Auth is technically plausible, but not yet verified in this project

The current Supabase documentation describes JWT verification through its project's JWKS endpoint when asymmetric signing keys are configured, and documents TOTP MFA enrollment/challenge flows. These are compatible with the intended design in which FastAPI validates access tokens and CampusOps performs business authorization from its own membership/permission records. An implementation spike must still test token issuer/audience/signature/expiry handling, key rotation behavior, invitation acceptance, email verification, recovery, MFA enforcement and revocation/recovery semantics before the provider is locked.

Recommended constraints:
- Never treat frontend role claims, client state or form fields as authority to grant permissions.
- Verify tokens server-side; use the trusted subject ID to resolve an active CampusOps membership and scoped permissions.
- Enforce MFA policy for platform operators and require workspace primary administrators to enroll before real participant data is used in a pilot.
- Keep sensitive recovery as an independently reviewed operational workflow, with established-contact notification, session/token revocation and invalidation of outstanding invitations/reset links.

Official references:
- https://supabase.com/docs/guides/auth/jwts
- https://supabase.com/docs/guides/auth/auth-mfa

### 3.2 Region and cost

Supabase documentation lists Mumbai (`ap-south-1`) as an available specific AWS region and states that project region determines the primary location for the database and related core services. Mumbai is a reasonable candidate for an India-focused first pilot if no different data-residency requirement emerges; this is a recommendation, not a legal/compliance conclusion. Review the provider's data-processing terms and any organizational requirements before using real attendee data.

The official pricing page currently indicates that the Free plan has resource limits, no automatic backups, and may pause after one week of inactivity; the listed Pro plan starts at US$25/month. Accordingly:
- A free tier may be considered only for disposable development/synthetic-data work after feasibility is checked.
- Do not use an unreviewed free-tier deployment for a live event or real participant data.
- Before a pilot, confirm current pricing, backups, restore procedures, access/log retention, data region, support expectations and environment separation.

Official references:
- https://supabase.com/docs/guides/platform/regions
- https://supabase.com/pricing

### 3.3 Transactional email

Supabase's built-in email sender is intended for testing and is currently limited to two emails per hour, with restricted recipient behavior; its documentation recommends configuring custom SMTP for production use. Therefore:
- During local development, use a local test mailbox (for example, the supported local Auth/Mailpit workflow) and do not send real invitations.
- Before external invitations, email verification and password recovery are used with real people, select and configure an SMTP/provider adapter and test delivery failure/retry semantics.
- Invitation status must distinguish created, sent/delivery-attempted, accepted, expired and revoked. Email delivery never itself activates membership.

Official reference: https://supabase.com/docs/guides/auth/auth-smtp

### 3.4 Evidence files

Task proof may be a file or link, as specified by the founder. The implementation slice that enables file upload must use private storage, server-side authorization, size/type validation, non-public object keys, short-lived authorized access links (or authenticated proxy access), upload failure handling, retention/deletion rules and evidence-version history. Supabase Storage can be evaluated as a same-project candidate, but do not assume it is configured securely by default or expose a service-role key to the browser. If no safe file-storage implementation has been validated, file upload must remain disabled rather than ship as a fake control; the API may still support link evidence only in a clearly marked development slice, provided the slice is not misrepresented as meeting the complete proof requirement.

### 3.5 Hosting and registration connector

- Local development can proceed without choosing a production hosting provider, after environment inspection and authorization.
- Hosted staging requires selected region, secrets management, logs, backup/restore plan and cost check.
- Google Forms is a candidate external registration connector, not a committed first-slice integration. Implement native registration first. External imports must be idempotent, preserve source identifiers, surface conflicts and never merge people solely by email.
- Online-first operation with manual fallback is approved. Full offline check-in remains deferred unless separately designed and tested.

## 4. Recommended staged technical baseline

| Area | First-slice direction | Closure condition |
|---|---|---|
| Frontend | React + TypeScript + Vite remains proposed | Confirm the actual repository and installed toolchain before changing anything |
| Backend | FastAPI modular monolith remains proposed | Verify Python/tooling compatibility and establish local test command |
| Database | PostgreSQL; Supabase Postgres is a candidate, not locked | Finalize only the physical schema for the first slice, with constraints, unique keys, migrations and rollback approach |
| Authentication | Supabase Auth preferred candidate | Pass token, invitation, verification, MFA and recovery feasibility/security checks before final lock |
| Authorization | CampusOps-owned scoped membership/permission records; deny by default | Negative tests prove cross-organization, cross-event and over-privileged operations are denied |
| Evidence storage | Private object storage candidate | Validate private access, signed/authenticated download, file size/type, upload failure, retention and deletion before file uploads are enabled |
| Email | Adapter; local test sink during development | Custom SMTP/provider selected and tested before real invitations or recovery email |
| External registration | Native first; external connector deferred | Choose provider only after access scope, data mapping, sync direction, stable source ID and conflict policy are tested |
| Deployment | Local synthetic-data development first | Real-data pilot requires hosting/region/cost review, backup/restore test, monitoring and runbook |
| Offline mode | Manual fallback; no full offline promise | Separate design/acceptance tests required before any offline claim |

## 5. First implementation sequence after explicit authorization

The sequence is dependency-led. It is not permission to start now.

### Step 0 — Environment and feasibility check

- Reconfirm the current `D:\Antigravity_Projects\CampusOps` folder and whether it still contains no files; inspect rather than assume.
- Record OS, available Python/Node versions, package manager, Git state and existing files; do not install or overwrite anything until agreed.
- Test the chosen auth candidate at minimal scope using synthetic identities: JWT verification in FastAPI, email verification, invitation/acceptance path, TOTP MFA and recovery/revocation expectations.
- Confirm local database/migration workflow and local email test sink.
- Record outcomes; a documentation claim is not a successful feasibility test.

### Step 1 — Identity and organization workspace

A personal account, pending workspace, creator/Primary Workspace Administrator, email verification, organization review state, membership and scoped permissions; no real data. Define exact physical schema/API contracts and unit/security tests for this slice before coding it.

### Step 2 — Event/program structure and invitations

Create standalone event and multi-event program; common departments and child events; invitation binding to intended email, workspace and scope; acceptance/expiry/revocation; existing-account handling; permission enforcement.

### Step 3 — Tasks and proof review

Owner, specific deadline, progress history, deadline-change request/direct privileged change, evidence submission, reviewer eligibility, no self-approval, rejection reason, resubmission and notification. File evidence stays disabled until storage gate passes.

### Step 4 — Native registrations and individual check-in

Solo/team registration, individual participant records, one check-in per person/event, duplicate/concurrent handling and audited corrections.

### Step 5 — Event-day view and close-out

Role-scoped operational status, internal blockers, report evidence, registration-vs-attendance reconciliation and multi-event summaries.

### Step 6 — Hosted test and pilot gate

Provider/cost/region check, custom email, private storage, backup/restore proof, security/accessibility tests, performance expectations, incident and manual-fallback runbooks. Only then consider a real-data pilot.

## 6. Minimum first-slice gate checklist

The first slice is ready to start only after:

- [ ] Founder explicitly authorizes implementation.
- [ ] Current repository/environment is inspected and captured in a short handoff note.
- [ ] The exact slice is selected; acceptance and negative-authorization tests are enumerated.
- [ ] Schema, constraints, API request/response/error contract and migrations for that slice are finalized.
- [ ] Supabase Auth feasibility checks pass or a documented alternate provider is selected for the slice.
- [ ] Development uses synthetic data and local test email; no real participant records.
- [ ] Secret-handling, organization isolation and access-denial tests are defined before protected endpoints are built.
- [ ] File upload, external registration and full offline behavior are either separately validated or explicitly disabled/deferred—not represented by working controls if they are not implemented.

## 7. Real-data pilot gate checklist

A pilot with real attendee information is a later gate and remains **NO-GO** until all relevant items are evidenced:

- [ ] Production email provider configured and verified.
- [ ] Primary workspace administrator MFA enforcement demonstrated.
- [ ] Organization verification/recovery runbook exercised.
- [ ] Private file access, retention and deletion verified for evidence files.
- [ ] Backups configured and restore test recorded.
- [ ] Region, cost envelope, access/log retention and data-processing terms reviewed.
- [ ] Security, cross-tenant isolation, duplicate/concurrent check-in and failure-path tests passed.
- [ ] Manual check-in fallback and post-event reconciliation procedures tested.
- [ ] Pilot scope, participant-data minimization, retention period and responsible operator documented.

## 8. Final decision

**Current recommendation: NO-GO for implementation until explicit authorization.** The policy decisions are approved and the design is sufficiently mature to begin a focused implementation-readiness check, but no environment inspection, provider integration test or first-slice schema/API freeze has been performed in this review. This review does not claim that any tests passed.

**Recommended next action:** when the founder explicitly authorizes implementation, inspect the current repository/environment first and run Step 0 as a small feasibility exercise. Do not create application files, install dependencies or deploy before that authorization. The production/real-data pilot remains a separate NO-GO until Section 7 is satisfied.

## 9. Version history

| Version | Change |
|---|---|
| 1.0 | Final technical closure review. Consolidates current approval state, provider documentation findings, safe deferrals, staged implementation sequence and release gates. No implementation authorized. |
