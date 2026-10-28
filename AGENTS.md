# CampusOps — Agent Governance and Project Rules

**Document version:** 1.0  
**Effective date:** 28 October 2026  
**Scope:** Universal engineering and operational rules for AI agents and human contributors working in `D:\Antigravity_Projects\CampusOps`.

---

## 1. Source of Truth & Authoritative Document Hierarchy

### 1.1 Sole Authoritative Documentation
All architectural, functional, security, and delivery baselines are governed exclusively by **`Consolidated Documentation/`**.
The defining index is:
- **`Consolidated Documentation/CampusOps_Consolidated_Documentation_Readme_v1.4.md`**

### 1.2 Authoritative Baseline Documents
When executing or planning work, the following documents constitute the active source of truth:
1. **`CampusOps_PRD_v1.1.md`**: Product intent, scope boundaries, user journeys, functional/non-functional requirements, acceptance scenarios, and success metrics.
2. **`CampusOps_Technical_Specification_v1.1.md`**: Modular monolith architecture, logical data model, authorization model, API conventions, and technical gates.
3. **`CampusOps_Delivery_Plan_v1.1.md`**: Delivery phases, workstream dependencies, test strategy, and release criteria.
4. **`CampusOps_Decision_Log_v1.4.md`**: Confirmed product directions, foundational defaults (FA-001–FA-009), closure policies (FPC-01–FPC-05), and current gate status.
5. **`CampusOps_Founder_Approval_Checklist_v0.3.md`**: Explicit founder approval record for foundational and closure policies.
6. **`CampusOps_Final_Pre_Implementation_Closure_Plan_v1.1.md`**: Policy approval status and slice-level technical deferrals.
7. **`CampusOps_Implementation_Readiness_Review_v1.1.md`**: Readiness scorecard and pre-implementation gates.
8. **`CampusOps_Final_Technical_Closure_Review_v1.0.md`**: Technical findings, staging sequence, and pilot verification gates.

### 1.3 Supporting Design References
The following files in `Consolidated Documentation/` provide detailed design history and technical context. They **must not override** the PRD or founder-approved decisions:
- `CampusOps_Role_and_Permission_Matrix_v0.1.md`
- `CampusOps_Data_Model_and_Relationship_Map_v0.1.md`
- `CampusOps_API_Contract_Draft_v0.2.md`
- `CampusOps_API_Contract_Traceability_Review_v0.1.md`
- `CampusOps_Architecture_Decision_Record_v0.2.md`
- `CampusOps_Architecture_Traceability_Review_v0.1.md`
- `CampusOps_Foundational_Workflow_Decision_Matrix_v0.1.md`
- `CampusOps_Foundational_Workflow_Reconciliation_v0.1.md`

### 1.4 Historical Archives (Non-Authoritative)
The following folders are historical records preserved for historical traceability only:
- `Requirement Specification Documents/`
- `Decision Logs Documents/`
- `Other Documents/`

**Mandatory Rule:** Never use historical archive files to override current requirements, policies, or decisions. If an authoritative file conflicts with another authoritative file, report the exact conflict immediately—do not silently reconcile it or invent a decision.

---

## 2. Product Scope & Operational Boundaries

### 2.1 Core Capabilities (In Scope)
CampusOps is designed for:
1. **Event Preparation & Internal Coordination:** Department structures, team assignments, task ownership, specific deadlines, and proof review.
2. **Event-Day Operations:** Live operational overview, staff reassignment, and lightweight staff-only operational blockers (e.g., equipment delay, room lockouts).
3. **Registration & Verification:** Native registration forms, participant records, and individual check-in at event stations.
4. **Post-Event Documentation:** Attendance-versus-registration reconciliation, photo/report evidence, closure checklists, and program-level aggregation.

### 2.2 Strict Out-of-Scope Exclusions
Agents and contributors must **never** implement, scaffold, or design routes for:
- Marketing campaign management or promotional activity tracking.
- Poster, social media asset, video, reel, or promotional presentation creation.
- Social media publishing or marketing analytics.
- Participant-facing doubt, question, or issue submission portals.
- General participant support ticketing systems.

---

## 3. Mandatory Product & Domain Rules

1. **Individual Identity & Workspace Isolation:**
   - Every person has an individual account associated with their personal email.
   - Organizations operate in isolated workspaces.
   - **Never create or support a shared club/organization login or shared password.**
   - Directory/tenure records (`OrganizationPersonRecord`) are editable contact records and do not grant system access.
2. **Dual Setup Workflows:**
   - **Standalone Event:** Event defines its own departments and assigns Department Leads. Leads manage departmental members and assign work.
   - **Multi-Event Program:** Parent program defines shared departments across child events. Leads are assigned to specific child events (no default department leads). Coordinators are assigned to shared departments and specific event tasks.
3. **Task & Proof Accountability:**
   - Active tasks must have an accountable owner and a specific deadline (evaluated in the event's configured timezone).
   - Tasks requiring proof move to `Submitted for Review` upon submission of file or link evidence.
   - **No Self-Approval:** A submitter can never approve their own task evidence, regardless of their role or administrative privileges.
   - Rejections require an explicit reason, remain non-completed (`Changes Requested`), preserve history, and trigger notifications.
   - Deadline changes require a dedicated audited operation (reason, actor, old/new value, notification) and cannot be bypassed via generic updates.
4. **Registration & Individual Check-In:**
   - Native registration is the core primary path.
   - Team/group registrations must store and maintain individual participant records.
   - **Individual Check-In:** Every attendee must be checked in individually, even when arriving as part of a team. Scanning a team QR code must never mark all members present automatically.
   - Repeated or concurrent check-in scans must resolve idempotently without inflating attendance counts.
   - Check-in corrections/voids must be audited with an explicit reason, never physically deleted.
5. **Connectivity Stance:**
   - The operational posture is **online-first with a documented manual fallback**.
   - Do not claim or implement offline functionality without explicit design, storage protection, sync conflict reconciliation, and verified automated tests.
6. **External Integrations & Third-Party Candidates:**
   - **Google Forms:** Candidate external registration connector only; not an approved implementation choice until API quotas, permissions, and sync direction are proven. Native registration must precede any connector.
   - **Supabase Auth:** Founder-approved preferred candidate for authentication; not a locked production provider until implementation-level feasibility/security checks are verified.

---

## 4. Approved Foundational Policies

### 4.1 Foundational Defaults (FA-001 – FA-009)
- **FA-001 (Task Proof Review):** Scoped review by authorized leads or core members; strict prohibition of self-approval; backup reviewer or documented escalation; rejection requires reason, notification, and preserved history.
- **FA-002 (Scoped Permissions):** Explicit scoping to organization, program, event, department, or task. No implicit administrative access to child events. Roles map to permission sets; no self-elevation.
- **FA-003 (Directory Privacy):** Workspace-wide basic directory exposes name, role, department, and event assignments. Email and phone numbers are restricted to authorized operational need. Participant data is never exposed in the member directory.
- **FA-004 (Task Deadlines):** Active tasks require owner and specific deadline. Assigned users request changes with reasons; authorized leads approve. Direct admin changes are audited and notified.
- **FA-005 (Check-In Integrity):** QR/registration ID lookup with search fallback. One check-in per person per event. Duplicate check-ins blocked idempotently. Audited corrections with reasons. Controlled walk-ins.
- **FA-006 (Degraded Connectivity):** Online-first with documented manual fallback. No offline claim without design and testing.
- **FA-007 (Registration Normalization):** Native and external imports normalize through one validation path. Stable external IDs retained. No auto-merging based solely on email. Audited roster edits with optional cutoff.
- **FA-008 (Staff Operational Blockers):** Lightweight staff-only internal blockers retained; participant-facing ticketing excluded.
- **FA-009 (Invitations):** Single-use, revocable invitation tokens bound to intended email, workspace, and scope, with a 7-day expiration. Safe reissue/refresh. Failed delivery does not grant membership.

### 4.2 Closure Policies (FPC-01 – FPC-05)
- **FPC-01 (Attendee Information):** Organizer-published schedule, venue, rules, and instructions are strictly read-only. No participant doubt/issue submission.
- **FPC-02 (Organization Verification):** Workspace begins in `pending_verification`. Creator verifies personal email and provides organization details. Platform administrator verifies via official domain/page or faculty confirmation. Minimum necessary evidence; reasoned rejection/resubmission path.
- **FPC-03 (Initial Administrator):** Email-verified creator becomes Primary Workspace Administrator with limited privileged actions until organization verification passes.
- **FPC-04 (Auth Candidate):** Evaluate Supabase Auth for email/password, email verification, password recovery, and TOTP MFA. FastAPI validates access tokens server-side. CampusOps tables enforce business authorization.
- **FPC-05 (MFA & Recovery):** MFA mandatory for platform operators. Workspace Primary Admins must enrol MFA before real participant data is handled. Ordinary recovery uses provider-managed email flow; sensitive workspace recovery requires documented independent review, notification of established contacts, session revocation, and invalidation of reset tokens/invitations.

---

## 5. Security & Privacy Requirements

1. **Server-Side Enforcement (Deny by Default):**
   - Every protected API endpoint must independently authenticate the caller, verify active workspace membership, and validate authorization for the specific target resource scope.
   - Never trust frontend claims, role strings, client-submitted user IDs, or hidden UI controls.
2. **Tenant & Scope Isolation:**
   - All database queries and operations must enforce organization boundaries.
   - Multi-event program access must not leak private records, participant details, or tasks between child events without explicit permission.
3. **Evidence & File Storage Security:**
   - Task evidence files and report attachments must reside in private object storage.
   - Never generate permanent public URLs for internal evidence.
   - Enforce server-side file type and size validation before accepting uploads.
4. **Data Minimization & Privacy:**
   - Collect only necessary operational fields for participants.
   - Separate member directory metadata from private contact fields.
   - Log no secrets, plaintext passwords, unhashed tokens, or excessive PII.
5. **Auditability:**
   - Consequential state changes (role assignments, evidence reviews, deadline alterations, check-in voids, organization transfers, and closure exceptions) must record actor, timestamp, resource ID, before/after values, and justification.

---

## 6. Small-Increment Delivery & Engineering Expectations

### 6.1 Architectural Pattern
- **Modular Monolith:** Single deployable backend application with clean module boundaries (FastAPI proposed, React + Vite proposed, PostgreSQL relational database).
- Do not introduce microservices, message queues (Kafka/RabbitMQ), Redis caches, or Kubernetes clusters without explicit, documented architectural justification approved by the founder.

### 6.2 Small Vertical Slices
Delivery proceeds in dependency-led vertical slices using synthetic/test data:
1. **Slice 1 (Identity & Organization):** Personal account sign-up/in, pending workspace creation, verification workflow mock, workspace membership, and scoped roles.
2. **Slice 2 (Event Structure & Invitations):** Standalone event and multi-event program setup, shared departments, single-use 7-day invitations, and acceptance/revocation.
3. **Slice 3 (Tasks & Evidence Review):** Task lifecycle, owners, deadlines, proof submission, review state machine, self-approval prevention, rejection reasons, and deadline audit trail.
4. **Slice 4 (Native Registration & Check-In):** Registration form, solo/team registration, individual participant records, QR/search check-in, duplicate prevention, and check-in voiding.
5. **Slice 5 (Operations & Close-Out):** Event-day status view, internal operational blockers, report generation, attendance reconciliation, and program summary rollups.
6. **Slice 6 (Operational Hardening):** Staged hosting review, backup/restore proof, MFA enforcement, and operational runbooks.

### 6.3 Definition of Ready (DoR)
A slice or feature is ready for implementation only when:
- Requirements and acceptance criteria are explicitly documented.
- Physical schema, database constraints, and API contracts for that slice are finalized.
- Negative authorization and error cases are defined.
- Dependencies and uncertainties are logged.

### 6.4 Definition of Done (DoD)
A slice or feature is done only when:
- Code adheres to modular domain boundaries.
- Server-side authorization and input validation are active.
- Automated tests (unit, API integration, and negative authorization) have been executed and observed passing.
- Audit logging is verified for sensitive operations.
- Documentation and status tracking are updated.

---

## 7. Testing & Verification Standards

1. **Truth-in-Testing Rule:**
   - **Never claim that a test, command, or build passed unless it was actually executed and its successful result was observed directly in tool output.**
   - A planned or scripted test is not a passed test.
2. **Negative Authorization Testing:**
   - Every protected route must have automated negative tests verifying denial (HTTP 401/403) for:
     - Unauthenticated requests.
     - Authenticated users belonging to a different organization (cross-tenant attack).
     - Authenticated users in the same organization lacking required scope (cross-event/cross-department attack).
     - Self-approval attempts on proof-gated tasks.
3. **Concurrency & Idempotency Testing:**
   - Verify that concurrent check-in requests for the same participant do not create duplicate attendance records.
   - Verify that replaying an invitation acceptance or external import payload does not duplicate memberships or registrations.
4. **Degraded Connectivity Testing:**
   - Verify system behavior and error messaging under network timeouts and failed API requests before pilot deployment.

