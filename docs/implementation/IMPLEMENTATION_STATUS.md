# CampusOps — Implementation Status & Governance Record

**Last updated:** 30 October 2026<br>
**Status:** Phase 1.1 Organization Management Closure (Prompt 27) completed and verified. Delivered: (1) Secure URL fragment invitation routing (`#token=...`), ephemeral component memory extraction, immediate URL scrubbing via `history.replaceState` before any network call, legacy query parameter rejection (`?token=...`) with security alert notice and manual-entry fallback, and zero token persistence in web storage; (2) Organization-wide member directory API (`GET /api/v1/organizations/{organization_id}/members`) with tenant isolation, `ACTION_VIEW_ORG_PROFILE` gating, tiered contact privacy masking (`email_masked: bool`), and pagination; (3) Organization-wide invitation directory API (`GET /api/v1/organizations/{organization_id}/invitations`) gated by role management authority (`ACTION_MANAGE_ROLES` / `ACTION_INVITE_MEMBER`), dynamic expiration evaluation, and strict credential exclusion; (4) Frontend directory integration in `MemberDirectoryTable.tsx`, `WorkspaceOverview.tsx`, and `InvitationAcceptView.tsx` with live API-backed roster, status filtering, privacy badges, and pagination; (5) Reconciled canonical technical gate register (TG-01 to TG-07) across all documentation. Total test suite expanded to **310 passing backend tests** (5 new integration tests added) and **59 passing frontend tests** (6 new automated tests added); production build clean (145ms). Application development active; production pilot remains **NO-GO**.<br>
**Working directory:** `D:\Antigravity_Projects\CampusOps`

---

## 1. Executive Summary

CampusOps development is progressing across strictly bounded, verified increment slices in accordance with `Consolidated Documentation/` and `AGENTS.md`.

- **Development Slice 1 (Completed):** Established minimal scaffolds for backend (FastAPI `GET /health` with Python 3.13.9 virtual environment) and frontend (React 19 + TypeScript + Vite + Vitest).
- **Development Slice 2A (Completed & Hardened):** Implemented and security-hardened the Identity and Organization Domain Foundation:
  - **Relational Domain Models (SQLAlchemy 2.0):** Defined `UserProfile` (UUID PK, unique `auth_subject_id`, unique `email_normalized`, strictly no password storage), `Organization` (enforcing `pending_verification` default status and audit metadata), `OrganizationMembership` (unique user-org constraint `uq_org_membership_user`), `RoleAssignment` (hierarchical and scoped: Organization, Department, Event), `PlatformAdmin` (explicit system authority), and `Invitation` (SHA-256 token hashing, 7-day expiration, single-use acceptance state).
  - **Schema Migrations (Alembic):** Created and verified initial migration revision `880d8e4eb890_slice_2a_identity_and_organization.py` with batch mode enabled for SQLite foreign key and constraint alterations. Clean upgrade (`head`), downgrade (`base`), and re-upgrade roundtrips verified.
  - **Authorization & Domain Services:** Built centralized deny-by-default permission evaluator (`can_perform`, `require_permission`), organization lifecycle service (creator role assignment, platform-admin-only verification/rejection with mandatory audit reasons), secure invitation lifecycle service (atomic acceptance, email match verification, tenant isolation, and replay prevention), and platform operator bootstrap mechanism (`appoint_platform_admin`).
  - **Testing Coverage:** 37 automated backend Pytest tests covering migrations, model constraints, tenant isolation, scope non-leakage, organization verification gates, and invitation lifecycles.
- **Development Slice 2B (Completed, Audited & Hardened):** Implemented the Identity & Organization REST API Foundation on top of Slice 2A models and services:
  - **Strict Pydantic Request/Response Contracts:** Implemented `extra="forbid"` models preventing payload pollution or privilege escalation attempts; explicit response models strictly excluding sensitive internal fields (`raw_token`, `token_hash`, passwords).
  - **Fail-Closed Authentication Boundary:** Built `get_current_principal` dependency that fails closed with HTTP 401 Unauthorized unless an upstream identity provider adapter is configured. Untrusted caller headers (`X-User-ID`, etc.) and body IDs are ignored. `get_current_user` resolves `UserProfile`, links `auth_subject_id`, and enforces that accounts are active and emails are verified (403 Forbidden).
  - **Organization Endpoints:**
    - `POST /api/v1/organizations`: Creates workspace in `pending_verification` status; creator is granted `PRIMARY_ADMIN`.
    - `GET /api/v1/organizations`: Returns only organizations where the caller holds active membership (strict tenant isolation).
    - `GET /api/v1/organizations/{id}`: Returns organization details for authorized members or platform administrators; enforces role-based field disclosure (censors `verification_reviewer_id` for non-platform admins, censors `verification_note` for non-admin members); returns uniform HTTP 404 for non-existent or foreign organizations to prevent enumeration.
    - `POST /api/v1/organizations/{id}/verify`: Platform-admin-only endpoint to verify or reject organizations; rejections require a mandatory review reason.
  - **Current User Profile & Membership Discovery:**
    - `GET /api/v1/me`: Returns caller's profile, platform admin status, and active memberships/roles; excludes removed memberships and never leaks cross-tenant information.
  - **Invitation & Acceptance Endpoints:**
    - `POST /api/v1/organizations/{id}/invitations`: Restricts scopes to organization-level (department/event scopes deferred to Slice 3 return 400 Bad Request); requires verified organization status; fails closed with HTTP 503 if transactional email provider is unconfigured (FPC-06); response schema never exposes tokens.
    - `POST /api/v1/invitations/accept`: Accepts raw token in JSON body; enforces single-use atomic status transition, non-expiration, email match, and organization verification; returns HTTP 409 if already a member.
    - `POST /api/v1/organizations/{id}/invitations/{id}/revoke`: Verifies organization tenancy and revokes pending invitations; requires role management authority.
  - **Security Audit & Hardening Review (Prompt 07):** Identified and resolved 6 critical defects/vulnerabilities and operational requirements:
    1. *Pre-Account Takeover / Unverified Email Spoofing:* Gated secondary email profile lookups strictly behind `principal.email_verified == True` and prevented conflicting subject ID linking.
    2. *Provider Email Change Verification & Conflict Prevention:* Rejected unverified email changes from upstream auth providers with HTTP 403, rejected collisions with other accounts with HTTP 409, and cleanly updated `email_normalized` when verified and unconflicted.
    3. *Legacy Role Accumulation:* Automatically revoked unrevoked prior tenure roles when reactivating a removed membership upon new invitation acceptance.
    4. *Orphan Invitations on Email Delivery Failure:* Ensured unexpected exceptions during email delivery trigger clean deletion of the committed invitation row and return HTTP 503.
    5. *Role-Based Information Disclosure Controls:* Built tiered organization detail filtering—Platform Admins inspect full reviewer audit metadata; Primary Admins inspect verification notes/reasons without revealing reviewer identity; ordinary members see workspace details with audit fields censored.
    6. *Operational Platform Administrator Bootstrap:* Created server-side CLI tool (`backend/scripts/bootstrap_platform_admin.py`) for initial break-glass/first-admin setup with zero HTTP privilege-escalation surface.
  - **Testing Coverage:** 31 HTTP integration and regression tests added across 4 test suites. Total backend test suite now stands at **68 passing tests**.
- **Development Slice 2C (Authentication Feasibility & Prerequisite Audit Completed):**
  - **Prerequisite Inspection:** Verified that host Docker Desktop daemon is inactive and Supabase CLI is not installed; host port 5432 is occupied by an existing PostgreSQL service (`PID 9244`). Avoided system modification, service re-configuration, or public cloud provisioning.
  - **Cryptographic Validation Spike:** Verified asymmetric RS256/ES256 signature verification against JWKS, key rotation, tamper rejection, expired token rejection, wrong issuer/aud rejection, algorithm confusion rejection, and TOTP MFA `aal2` claim extraction using `PyJWT 2.10.1` and `cryptography 46.0.3` on Python 3.13.9 in an isolated disposable directory outside CampusOps.
  - **Application Baseline Reality Check:** Clarified that the normal application currently has NO configured identity provider adapter and fails closed (HTTP 401); tests use synthetic dependency overrides; production cryptographic validation and remote JWKS caching are NOT yet in the normal application codebase.
  - **Deliverable:** Created `docs/implementation/SLICE_2C_AUTH_FEASIBILITY_REPORT.md`. Candidate recommendation: *"Suitable candidate, with outstanding hosted-verification gates."* TG-02 remains unpassed pending live verification.
- **Slice 3 Design Plan (Programs, Events, Departments & Event Leads Completed):**
  - **Deliverable:** Created `docs/implementation/SLICE_3_SCHEMA_API_ACCEPTANCE_PLAN.md`.
  - **Scope & Architecture:** Formulated complete relational schema, check constraints, exclusive departmental scoping (`program_id` XOR `standalone_event_id`), tenant boundary verification engine, Alembic migration order (`c92f1b4a3d10`), Pydantic v2 API contracts, dual setup journeys (Standalone Event Workflow A vs Multi-Event Program Workflow B), scoped invitations unblocking, and comprehensive acceptance test matrix.
  - **Governance:** Identified 4 explicit unresolved product-policy questions for founder review without inventing assumptions. Zero application code or migrations were implemented in this design step.
- **Development Slice 3A (Program, Event, Department & Event-Lead Domain Foundation Completed):**
  - **Relational Domain Models (`backend/app/models/event.py`):**
    - `Program`: Multi-event umbrella belonging to `Organization`; enforces unique name per org (`uq_programs_org_name`) and non-destructive archival (`D-SLICE3-04`).
    - `Event`: Standalone (`program_id IS NULL`) or child event under a Program (`program_id IS NOT NULL`). Enforces tenant alignment with parent program.
    - `Department`: Functional team. Enforces database check constraint `ck_departments_exclusive_parent` ensuring a department belongs either to a Program XOR a standalone Event (`D-SLICE3-01`).
    - `EventLeadAssignment`: Relational join table mapping active members to events. Enforces `uq_event_lead_active` partial unique index to prevent duplicate active leads while preserving historical revocations (`D-SLICE3-02`).
  - **Alembic Migration (`c92f1b4a3d10`):**
    - Created additive migration with `down_revision = '880d8e4eb890'`.
    - Dependency order: `programs` -> `events` -> `departments` -> `event_lead_assignments`.
    - Batch mode (`render_as_batch=True`) enabled for SQLite. Roundtrip upgrade, downgrade to base, and re-upgrade verified cleanly.
  - **Domain Services & Scope Validation (`backend/app/services/event.py`):**
    - Lifecycle services: `create_program`, `archive_program`, `create_event`, `archive_event`, `create_department`, `archive_department`, `assign_event_lead`, `revoke_event_lead`.
    - Upgraded `validate_target_resource_scope` in `backend/app/services/permissions.py` to validate against real database entities, enforcing tenant boundaries, non-leakage, and non-archived parent hierarchies.
    - Authoritative event-lead synchronization: `assign_event_lead` and `revoke_event_lead` transactionally synchronize `RoleAssignment(role_name="EVENT_LEAD", scope_type="event")`.
    - Prepared validation helpers for future Slice 3B APIs: `validate_program_scope_assignment`, `validate_event_scope_assignment`, `validate_department_scope_assignment`, `validate_event_lead_eligibility`.
  - **Initial-Release Design Decisions:** Formally adopted decisions D-SLICE3-01 through D-SLICE3-04 and documented in `Consolidated Documentation/CampusOps_Decision_Log_v1.5_Addendum.md`.
  - **Testing Coverage:** 13 new automated tests in `backend/tests/test_slice_3a_domain.py`. Total backend test suite reached 81 passing tests.
- **Slice 3A Database Integrity & Lifecycle Audit (Prompt 10 Completed):**
  - **Relational Integrity Audit & Remediation:** Identified that migration `c92f1b4a3d10` foreign keys checked entity existence by primary key (`id`) only, permitting direct-database cross-tenant associations. Created additive Alembic migration `d81e3a5f2c90_slice_3a_integrity_hardening.py` with composite unique constraints and composite foreign keys enforcing that child events, departments, and event leads strictly belong to the same `organization_id` as their parent programs, events, and memberships.
  - **Database Check Constraints:** Added check constraints for event start/end ordering (`ck_events_time_order`), program date ordering (`ck_programs_date_order`), and status/archival timestamp consistency (`*_status_archived` on programs, events, and departments). Added `timezone` column (`String(50)`, default `'Asia/Kolkata'`, non-null) to `Event`.
  - **Domain Service Hardening:** Updated `create_program` and `create_event` with temporal sequencing validation; hardened `assign_event_lead` and `validate_event_lead_eligibility` to verify active account status and email verification; wrapped assignment and revocation operations in explicit database transaction rollback blocks.
  - **Comprehensive Audit Suite:** Added 10 tests in `backend/tests/test_slice_3a_integrity_audit.py` verifying cross-tenant database rejects, temporal constraints, archival invariant checks, and transactional rollback on fault injection. Total backend test suite now stands at **91 passing tests**.
  - **Deliverable:** Created `docs/implementation/SLICE_3A_INTEGRITY_AUDIT_REPORT.md` documenting all findings, constraint mappings, and architectural observations.
- **Development Slice 3B (Program, Event, Department & Event-Lead APIs & Scoped Invitations Completed):**
  - **Product Policy Closure (D-SLICE3-05 & D-SLICE3-06):** Adopted formal decisions in `Consolidated Documentation/CampusOps_Decision_Log_v1.5_Addendum.md`:
    - `D-SLICE3-05`: Multi-day event scheduling policy. Added `event_end_date` (sa.Date()). Enforces `planned_end_time >= planned_start_time` for single-day events; allows overnight sessions when `event_end_date > event_date`. Enforces child event date bounds within parent Program dates. Validates timezones against 599 standard canonical IANA timezones offline via `backend/app/services/timezones.py`.
    - `D-SLICE3-06`: Non-destructive archival confirmed via `archived_at` timestamp. Event lifecycle state machine transitions (`draft` -> `published` -> `in_progress` -> `completed` / `cancelled`) and registration invalidations deferred to Slice 4.
  - **Additive Alembic Migration (`e4f5a6b7c8d9`):** Created `backend/alembic/versions/e4f5a6b7c8d9_slice_3b_event_end_date_and_multi_day_time_order.py` with `down_revision = 'd81e3a5f2c90'`. Added `event_end_date` column, check constraint `ck_events_date_order`, and updated `ck_events_time_order` for multi-day events. Clean roundtrip verified.
  - **Pydantic v2 Request/Response Schemas (`extra="forbid"`):** Implemented strict schemas across `backend/app/schemas/` (`program.py`, `event.py`, `department.py`, `invitation.py`), forbidding unknown fields, payload pollution, and client ID injection.
  - **REST API Endpoints:**
    - Programs: `POST /organizations/{id}/programs`, `GET /organizations/{id}/programs`, `GET /organizations/{id}/programs/{program_id}`, `PATCH /organizations/{id}/programs/{program_id}`, `POST /organizations/{id}/programs/{program_id}/archive`, `GET /organizations/{id}/programs/{program_id}/departments`, `GET /organizations/{id}/programs/{program_id}/events`.
    - Events: `POST /organizations/{id}/events` (standalone), `POST /organizations/{id}/programs/{program_id}/events` (child), `GET /organizations/{id}/events`, `GET /organizations/{id}/events/{event_id}`, `PATCH /organizations/{id}/events/{event_id}`, `POST /organizations/{id}/events/{event_id}/archive`, `GET /organizations/{id}/events/{event_id}/departments`.
    - Departments: `POST /organizations/{id}/departments` (enforces `program_id` XOR `standalone_event_id`), `GET /organizations/{id}/departments/{department_id}`, `PATCH /organizations/{id}/departments/{department_id}`, `POST /organizations/{id}/departments/{department_id}/archive`.
    - Event Leads: `GET /organizations/{id}/events/{event_id}/leads`, `POST /organizations/{id}/events/{event_id}/leads`, `POST /organizations/{id}/events/{event_id}/leads/{assignment_id}/revoke`.
    - Scoped Invitations: `POST /organizations/{id}/invitations` (unblocks `department` and `event` scopes with real database validation), `POST /invitations/accept` (atomically creates `RoleAssignment` + `EventLeadAssignment` for `EVENT_LEAD` invitations with rollback protection).
  - **Anti-Enumeration and Tenant Isolation:** Uniform HTTP 404 returned for cross-tenant access to prevent entity or organization existence discovery.
  - **Testing Coverage:** 43 new tests added (7 direct DB tests, 36 HTTP integration tests across 5 test suites). Total backend test suite now stands at **134 passing tests**.
  - **Deliverables:** Created `docs/implementation/SLICE_3B_API_CONTRACT.md` and `docs/implementation/SLICE_3B_IMPLEMENTATION_REPORT.md`.
- **Slice 3B API Security, Authorization & Transaction Audit (Prompt 12 Completed):**
  - **Route-by-Route Authorization Review:** Systematically audited all 25 REST API endpoints against tenant isolation, minimum role enforcement, fail-closed unauthenticated behavior (HTTP 401), non-member enumeration protection (uniform HTTP 404), and intra-tenant role scoping.
  - **Vulnerability Remediation & Hardening:**
    1. *Information Disclosure Elimination:* Sanitized foreign organization UUID leakage in `create_event` when rejecting cross-tenant parent programs.
    2. *Scheduling Integrity Enforcement:* Added explicit validation in `create_event` and `update_event` rejecting `event_end_date` when `event_date` is `None` (mapped to HTTP 400).
    3. *Cross-Event Scope Matching:* Enforced strict `event_id` verification in `revoke_event_lead` and mapped mismatched URL paths to HTTP 404.
    4. *Two-Phase Commit Limitation Closure:* Documented the fail-closed distributed limitation where email provider timeouts delete the DB invitation row to prevent orphan tokens.
  - **Atomic Transaction Rollback Verification:** Tested that simulated commit crashes during `assign_event_lead`, `revoke_event_lead`, `accept_invitation` (EVENT_LEAD sync), and membership reactivation atomically roll back all related entities and leave base records uncorrupted.
  - **Role & Scope Isolation:** Proved via HTTP integration tests that Event Leads cannot mutate sibling events under the same parent program, and Platform Administrators without organization membership cannot mutate workspace resources.
  - **Testing Coverage:** 11 new security audit tests in `backend/tests/test_slice_3b_security_audit.py`. Total backend test suite now stands at **145 passing tests**.
  - **Deliverable:** Created `docs/implementation/SLICE_3B_SECURITY_AUDIT_REPORT.md`.
- **Development Slice 4A (Task Management and Operational Blocker Foundation Completed):**
  - **Relational Domain Models (`backend/app/models/task.py`):** Defined 10 SQLAlchemy 2.0 models: `Task`, `TaskAssignee`, `TaskDeadlineHistory`, `TaskStatusHistory`, `EvidenceSubmission`, `EvidenceArtifact`, `TaskReview`, `OperationalBlocker`, `OperationalBlockerHistory`, and `Notification`.
  - **Additive Alembic Migration (`f5a6b7c8d9e0`):** Created `f5a6b7c8d9e0_slice_4a_task_management_and_operational_blockers.py` with `down_revision = 'e4f5a6b7c8d9'`. Configured batch alterations for SQLite, partial unique index `uq_task_assignee_active` for single active assignees, submission number unique constraint `uq_submission_task_number`, and check constraints for statuses and priorities. Clean downgrade and upgrade roundtrip verified.
  - **Domain Services & Invariants (`backend/app/services/task.py`):**
    - Task lifecycle: creation with mandatory deadline (`due_date`, optional `due_time`, IANA `timezone`), verified organization gating, and scope resolution across organization, program, event, and department.
    - Assignment lifecycle: assigns active organization members, records history, and auto-unassigns prior active assignee with timestamp and actor tracking.
    - Deadline management: requires non-empty reason and records full audit log in `TaskDeadlineHistory`.
    - Evidence submission & review workflow: multi-attempt submissions, safe URL validation (valid HTTP/HTTPS, no server fetch), strict self-review prohibition (submitter or active assignee cannot review own work), mandatory rejection reason, and atomic conditional updates preventing race conditions.
    - Staff-only operational blockers: creation, resolution with mandatory notes, reopening, and non-participant isolation.
    - In-app notifications: durable records for task assignment and review feedback.
  - **Testing Coverage:** 14 new automated tests in `backend/tests/test_slice_4a_task_domain.py`. Total backend test suite reached 159 passing tests.
  - **Strict Scope Boundaries:** Zero REST APIs or frontend screens were introduced in this slice.
  - **Deliverable:** Created `docs/implementation/SLICE_4A_TASK_DOMAIN_REPORT.md`.
- **Slice 4A Security, Integrity & Workflow Audit (Prompt 14 Completed):**
  - **Database Partial Unique Index Hardening:** Audited `uq_task_assignee_active` and identified that indexing `['task_id', 'membership_id']` permitted different members to simultaneously hold active worker status. Hardened index in `models/task.py` and migration `f5a6b7c8d9e0` to index `['task_id'] WHERE assignment_status = 'active'`, enforcing strictly at most one active worker per task across all users at the database engine level.
  - **Transitive Parent Scope Archival Validation:** Hardened `_resolve_task_hierarchy` to assert non-archived status of umbrella parent programs and parent events before creating tasks or blockers.
  - **Task State Machine & Terminal Status Guards:** Guarded `complete_task_without_proof`, `assign_task`, and `change_task_deadline` against mutating closed tasks in `completed` or `cancelled` status.
  - **Formal Task Cancellation Lifecycle:** Implemented `cancel_task` in `backend/app/services/task.py` requiring an authorized manager and non-empty cancellation reason, recording the transition in `TaskStatusHistory`.
  - **Blocker Precondition Enforcement:** Enforced that `reopen_operational_blocker` strictly requires `status in ('resolved', 'wont_fix')` and `resolve_operational_blocker` rejects already resolved/closed blockers.
  - **Active Assignee Task View Access:** Updated `can_perform` in `backend/app/services/permissions.py` to grant active task assignees direct `ACTION_VIEW_TASK` and `ACTION_SUBMIT_PROOF` on their assigned tasks (including organization-scoped tasks), which is automatically revoked once unassigned.
  - **URL Safety Boundary:** Added 2048-character length limit in `validate_evidence_url` while affirming zero server-side fetch execution.
  - **Testing Coverage:** 14 new comprehensive audit regression tests in `backend/tests/test_slice_4a_security_audit.py`. Total backend test suite now stands at **173 passing tests**.
  - **Deliverable:** Created `docs/implementation/SLICE_4A_SECURITY_AUDIT_REPORT.md`.
- **Development Slice 4B (Task Management & Operational Blocker REST APIs Completed):**
  - Implemented 17 REST API endpoints across tasks, deadline changes, proof reviews, staff-only operational blockers, and in-app notifications.
  - Adopted decision `D-SLICE4-01` in `Consolidated Documentation/CampusOps_Decision_Log_v1.6_Addendum.md` cementing single active task assignment.
  - Added 22 HTTP integration tests across `test_api_tasks.py` and `test_api_blockers_notifications.py`. Total backend test suite reached 196 passing tests.
  - Deliverables: `docs/implementation/SLICE_4B_API_CONTRACT.md` and `docs/implementation/SLICE_4B_IMPLEMENTATION_REPORT.md`.
- **Slice 4B Security, Authorization & Transaction Audit (Prompt 17 Completed):**
  - **Route-by-Route Matrix Review:** Audited all 17 REST API endpoints against the Role and Permission Matrix.
  - **Cross-Tenant Anti-Enumeration & Boundary Hardening:** Identified and resolved blocker route gap where `PATCH`, `resolve`, and `reopen` lacked tenant ID verification; added `_ensure_blocker_in_org` ensuring uniform HTTP 404 responses for alien blockers.
  - **Worker Authority Lifecycle:** Hardened `start_task`, `submit_task_evidence`, and deadline notifications to assert active membership status, invalidating removed members immediately.
  - **Self-Review Prohibition & Replay Protection:** Verified submitter and active worker self-review rejection (HTTP 400) even with elevated roles; verified conditional update double-review rejection.
  - **Testing Coverage:** 14 new comprehensive security audit regression tests in `backend/tests/test_slice_4b_security_audit.py`. Total backend test suite now stands at **210 passing tests**.
  - **Deliverable:** Created `docs/implementation/SLICE_4B_SECURITY_AUDIT_REPORT.md`.
- **Development Slice 5A (Participant Registration, Ticketing & Attendance Architecture Completed):**
  - **Comprehensive Architectural Blueprint:** Formulated domain architecture, boundary constraints, privacy tiers, and capacity mechanics across 4 primary engineering specifications in `docs/implementation/`:
    1. `SLICE_5_SCOPE_AND_ARCHITECTURE_PLAN.md`: Clarified non-payment admission passes, individual check-in rule (scanning a team pass marks ONLY the specific individual as present), event-scoped registration model, capacity accounting, tiered privacy disclosure, and offline sync readiness.
    2. `SLICE_5_SCHEMA_RELATIONSHIP_PLAN.md`: Defined 7 normalized relational tables (`event_registration_settings`, `registrations`, `participants`, `registration_participants`, `tickets`, `check_ins`, `check_in_corrections`), composite foreign keys enforcing multi-tenancy, check constraints, partial unique indexes (`uq_participants_event_email`, `uq_ticket_participant_active`, `uq_check_in_event_participant`), and Alembic migration sequence (`b7c8d9e0f1a2` revising `a6b7c8d9e0f1`).
    3. `SLICE_5_API_CONTRACT_DRAFT.md`: Defined 18 REST endpoints across public namespace (`/api/v1/public/events/{key}/...` with unguessable registration keys, rate limiting, and honeypot bot defense) and staff namespace (`/api/v1/organizations/{org_id}/events/{event_id}/...`), covering settings, solo/team registration, pass verification, QR and manual check-ins, check-in voids with mandatory audit reason, summaries, and CSV export.
    4. `SLICE_5_ACCEPTANCE_TEST_PLAN.md`: Specified 48 exhaustive acceptance test cases across 8 functional and security categories (solo/team happy paths, negative boundaries, sibling event isolation, concurrency races, privacy masking, check-in void audit integrity, and Alembic roundtrips).
  - **Formal Decision Closure:** Adopted decisions D-SLICE5-01 through D-SLICE5-04 in `Consolidated Documentation/CampusOps_Decision_Log_v1.7_Addendum.md`:
    - `D-SLICE5-01`: Capacity measured in individual human bodies (`len(participants)`), with atomic concurrency reservations.
    - `D-SLICE5-02`: Ticketing defined as digital non-payment admission passes; zero PII embedded in QR codes.
    - `D-SLICE5-03`: Registrations and check-ins strictly scoped to individual events (standalone or child events); program-wide pass bundling deferred.
    - `D-SLICE5-04`: Check-in voids and corrections restricted to managers (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`) with mandatory immutable audit log in `check_in_corrections`.
  - **Design-Only Discipline Preserved:** Zero application code, database migrations, REST endpoints, frontend screens, or payment integrations implemented. Total backend test suite maintained at **210 passing tests**.
- **Development Slice 5B (Participant Registration, Ticketing & Check-In Domain Foundation Completed):**
  - **Baseline Inventory Resolution:** Independently verified collected test baseline before changes. While Prompt 19 noted the Slice 5A inventory summed to 202, dynamic pytest collection confirmed exactly 210 passing tests across 24 test files; arithmetic analysis revealed an 8-test file had been inadvertently omitted from manual arithmetic addition, confirming a true baseline of 210 tests.
  - **Relational Domain Models (`backend/app/models/registration.py`):** Implemented 7 normalized SQLAlchemy 2.0 models:
    1. `EventRegistrationSettings`: Event-level registration controls, capacity limit (`capacity_limit`), current confirmed count (`current_confirmed_count`), waitlist limit, window datetimes, and team size boundaries (`min_team_size`, `max_team_size`).
    2. `Registration`: Transactional booking entity capturing `registration_type` (`solo` / `team`), `status` (`confirmed`, `waitlisted`, `cancelled`), `idempotency_key`, and contact details.
    3. `Participant`: Normalized attendee records with name, email, phone, and optional academic affiliation. Index `ix_participants_event_email` is non-unique to allow shared contact emails across distinct participants (FA-007) while preventing duplicate members inside teams.
    4. `RegistrationParticipant`: Association join table mapping participants to their parent registration, with `is_primary_contact` and `role_in_team`.
    5. `Ticket`: Digital non-payment admission pass (`status`: `active`, `cancelled`, `revoked`, `expired`). Raw pass code is strictly non-persisted; stores SHA-256 hash `pass_code_hash`. Partial unique index `uq_ticket_participant_active` enforces strictly one active ticket per participant.
    6. `CheckIn`: Attendance check-in record (`status`: `valid`, `voided`). Partial unique index `uq_check_in_event_participant` enforces at most one valid check-in per participant.
    7. `CheckInCorrection`: Immutable audit ledger for check-in status corrections and voids per decision `D-SLICE5-04`.
  - **Additive Alembic Migration (`b7c8d9e0f1a2`):** Created `b7c8d9e0f1a2_slice_5_registration_ticketing_and_attendance.py` with `down_revision = 'a6b7c8d9e0f1'`. Includes SQLite batch operations, composite foreign keys `(organization_id, event_id)` for tenant isolation, partial unique indexes, check constraints for enums and positive capacities, and complete downgrade/upgrade roundtrips verified in `test_migrations.py`.
  - **Domain Services & Invariants (`backend/app/services/registration.py`):**
    - Atomic Capacity Reservation: Capacity accounted strictly in individual human bodies (`len(participants)` per `D-SLICE5-01`). Evaluated via conditional atomic SQL update: `WHERE current_confirmed_count + :slots <= capacity_limit`, eliminating overselling race conditions.
    - Solo & Team Registration: Validates registration window dates, team size limits, unique team names, and non-duplicate emails within a submission; supports idempotent re-submission via `idempotency_key`.
    - Ticket Credential Security: Generates cryptographically secure pass codes (`CO-PASS-<HEX>`), stores strictly SHA-256 hashes, verifies passes with constant-time `hmac.compare_digest`, and issues replacement passes with atomic revocation.
    - Attendance Check-In & Idempotency: Supports pass-code and manual roster check-ins; duplicate scans on already checked-in attendees safely return the existing check-in without mutating state; scanning team passes checks in only the individual participant.
    - Manager-Only Check-In Correction (`D-SLICE5-04`): Voids and corrections restricted to manager authority (`ACTION_CORRECT_CHECK_IN`), requiring a mandatory explanation of at least 10 characters and recording an immutable entry in `CheckInCorrection`.
    - Privacy Boundaries: Data-masking helpers (`mask_email`, `mask_phone`) and tiered roster retrieval protecting participant PII from non-administrative staff.
  - **Permission Rules & Domain Errors:** Added 6 action constants (`ACTION_MANAGE_REGISTRATION_SETTINGS`, `ACTION_VIEW_REGISTRATIONS`, `ACTION_CHECK_IN`, `ACTION_CORRECT_CHECK_IN`, `ACTION_VIEW_ATTENDEE_CONTACT`, `ACTION_EXPORT_PARTICIPANTS`) in `backend/app/services/permissions.py` and 15 domain exceptions in `backend/app/services/errors.py`.
  - **Testing Coverage:** 19 automated domain tests added in `backend/tests/test_slice_5b_registration_domain.py`, plus migration lifecycle verification in `test_migrations.py`. Total backend test suite reached **230 passing tests**.
  - **Strict Scope Boundaries:** Zero REST APIs or frontend screens were introduced in this slice.
  - **Deliverable:** Created `docs/implementation/SLICE_5B_DOMAIN_IMPLEMENTATION_REPORT.md`.
- **Slice 5B Security, Authorization & Integrity Audit (Prompt 20 Completed & Hardened):**
  - **Alembic Additive Hardening Migration (`c8d9e0f1a2b3`):** Upgraded `ix_registrations_idempotency` to partial unique index `uq_registrations_event_idempotency` (`['event_id', 'idempotency_key'] WHERE idempotency_key IS NOT NULL`) and added partial unique index `uq_event_reg_settings_key_hash` (`['registration_key_hash'] WHERE registration_key_hash IS NOT NULL`). Replaced indexes cleanly without editing migration history; upgrade/downgrade verified via `test_migrations.py`.
  - **Credential Security & Rotation:** Proved 128-bit entropy in ticket pass codes (`CO-PASS-<HEX>`), non-persistence of raw tokens (SHA-256 only), constant-time comparison (`hmac.compare_digest`), absence of credentials in `__repr__`, and zero PII in passes. Implemented public key generator `generate_registration_key()` and added key rotation (`rotate_registration_key: bool = False`) in `update_registration_settings`.
  - **Relational Cross-Tenant & Cross-Event Isolation:** Verified via direct SQL tests that composite foreign keys strictly block cross-tenant registrations, participants, and settings, and prevent cross-event ticket, registration-participant, and check-in associations at the database engine level.
  - **Participant Identity & Shared Email Policy (FA-007):** Verified distinct `Participant` records, tickets, and check-in lifecycles for distinct individuals sharing an email address. Enforced team-member duplicate rejection in service and DB join tables.
  - **Capacity Concurrency & Rollback:** Tested atomic conditional updates, strict all-or-nothing team reservations, transactional rollback on fault injection, exact cancellation releases (confirmed releases once, waitlisted never releases), and safe capacity reduction below current attendance.
  - **Check-In & Void Audit Ledger (D-SLICE5-04):** Verified duplicate scan idempotency, database-enforced single valid check-in (`uq_check_in_event_participant`), rejection of cancelled/revoked attendees, manager-only void permissions, minimum 10-character reason constraint, and append-only audit trail in `check_in_corrections`.
  - **Diagnostic Reconciliation Query:** Implemented `reconcile_event_registration_counts(db, event_id, auto_fix=False)` for operational auditability and drift auto-correction.
  - **Testing Coverage:** 20 new comprehensive security audit regression tests in `backend/tests/test_slice_5b_security_audit.py` + 1 migration lifecycle test in `backend/tests/test_migrations.py`. Total backend test suite reached **251 passing tests**.
  - **Deliverable:** Created `docs/implementation/SLICE_5B_SECURITY_AUDIT_REPORT.md`.
- **Development Slice 5C (Participant Registration, Ticketing & Attendance REST APIs Completed):**
  - **Public Participant Endpoints (`/api/v1/public/...`):**
    - `GET /public/events/{registration_key}`: Event discovery, status (`open`, `closed`, `not_yet_open`, `ended`), registration format, team sizing rules, and real-time capacity availability.
    - `POST /public/events/{registration_key}/registrations`: Self-service individual and team registrations with Pydantic v2 `extra="forbid"`, issuing digital passes with zero PII, and handling idempotent replays safely (`<REDACTED_AFTER_ISSUANCE>`) with 409 Conflict on payload divergence.
    - `GET /public/events/{registration_key}/passes/{pass_code}`: Attendee pass display and QR payload verification (opaque high-entropy token, zero participant PII).
    - `GET /public/events/{registration_key}/registrations/{confirmation_code}`: Unguessable capability registration lookup with privacy masking (no attendee emails or phone numbers exposed).
    - `POST /public/events/{registration_key}/registrations/{confirmation_code}/cancel`: Public self-service cancellation with contact email identity verification, releasing capacity and invalidating passes.
  - **Staff Operational Endpoints (`/api/v1/organizations/{org_id}/events/{event_id}/...`):**
    - `GET` & `PUT .../registration-settings`: Manage registration status, capacity limits, format, scheduling windows, and key rotation.
    - `GET .../registrations`: Lists registration headers with status and type filters.
    - `POST .../registrations/walk-in`: Desk-assisted walk-in registration tagged `registration_channel = 'walk_in'`.
    - `POST .../registrations/{id}/cancel`: Manager cancellation releasing confirmed capacity.
    - `GET .../participants` & `GET .../participants/{id}`: Tiered attendee roster access. Desk volunteers (`REGISTRATION_STAFF`) receive masked contact details (`mask_email`, `mask_phone`). Unmasked contact info requires `ACTION_VIEW_ATTENDEE_CONTACT`.
    - `PATCH .../participants/{id}`: Corrects attendee details (name, college, student ID).
    - `POST .../participants/{id}/reissue-pass`: Atomically revokes prior passes and issues fresh admission pass credentials.
    - `POST .../check-ins`: QR or manual check-in enforcing individual check-in rule (FA-005) and duplicate scan idempotency (`status: "already_checked_in"` without inflating attendance counts).
    - `GET .../check-in-lookup`: Candidate search across attendee roster via ticket token, reference, name, or student ID.
    - `POST .../check-ins/{id}/void`: Manager-only void/correction (`ACTION_CORRECT_CHECK_IN`) requiring >= 10 character explanation, restoring pass and decrementing attendance.
    - `GET .../attendance-summary`: Real-time attendance metrics, attendance percentage, and team attendance breakdown (fully, partially, absent).
    - `GET .../roster-export`: Streamed CSV download of attendee roster strictly gated by `ACTION_EXPORT_PARTICIPANTS`.
  - **Testing Coverage:** 32 comprehensive integration tests added in `backend/tests/test_api_slice_5c_registration.py`. Total backend test suite now stands at **283 passing tests**.
  - **Deliverables:** Created `docs/implementation/SLICE_5C_API_CONTRACT.md` and `docs/implementation/SLICE_5C_IMPLEMENTATION_REPORT.md`.
- **Slice 5C Public API Security, Privacy & Transaction Audit (Prompt 22 Completed & Hardened):**
  - **URL Credential Exposure Hardening:** Added body-based POST endpoints (`/passes/verify`, `/registrations/lookup`, `/registrations/cancel`) protecting bearer tokens from URL leakage in reverse proxy logs, browser histories, and referer headers.
  - **CSV Formula Injection Sanitization (CWE-1236):** Hardened `/roster-export` by sanitizing all text cells against formula execution triggers (`=`, `+`, `-`, `@`, `\t`, `\r`).
  - **Registration Header Contact Masking:** Hardened `GET .../registrations` to mask contact details for callers lacking `ACTION_VIEW_ATTENDEE_CONTACT`.
  - **Testing Coverage:** 22 new security audit tests in `backend/tests/test_slice_5c_security_audit.py`. Total backend test suite reached **305 passing tests**.
  - **Deliverable:** Created `docs/implementation/SLICE_5C_SECURITY_AUDIT_REPORT.md`.
- **Development Slice 5D (Participant Registration & Event-Day Operations Frontend Completed):**
  - **Public Participant Portal:** Implemented `EventOverview` with capacity indicators, `IndividualRegForm` (solo registration), `TeamRegForm` (dynamic team member sizing within min/max bounds and duplicate email rejection), `RegistrationConfirmation` with individual passes, and `RegistrationLookupModal` for capability lookup and self-service cancellation via POST request bodies.
  - **Digital Admission Pass Display & SVG QR Generator:** Built zero-dependency pure TypeScript QR Code generator (`src/utils/qr.ts`) rendering scalable vector QR passes with zero PII in QR payloads. Safe recovery notice displayed if raw one-time tokens are redacted on browser reloads.
  - **Staff Event Operations Hub:** Built `CheckInDesk` (pass code scan and 250ms debounced candidate search with duplicate scan idempotency), `ParticipantRoster` (searchable table with masked contact details and CSV download trigger), `AttendanceSummaryCard` (real-time headcounts, capacity ratios, and team arrival breakdowns), `RegistrationSettingsCard` (capacity limits and key rotation), `CheckInCorrectionModal` (manager-only check-in void requiring >= 10 char mandatory reason), and `ParticipantDetailModal` (atomic pass reissuance).
  - **Fail-Closed Authentication Notice (`AuthUnavailableNotice`):** Formatted clear notice upon HTTP 401 when upstream identity provider remains unconfigured, maintaining strict deny-by-default boundary with zero mock login or client-side bypasses.
  - **Design System & Accessibility:** Established design tokens in `theme.css` and component styles in `components.css` with dark mode support, semantic HTML/ARIA attributes, visible focus indicators, and mobile-responsive layouts.
  - **Testing Coverage:** 23 passing tests across 5 Vitest test suites (`qr.test.ts`, `PublicRegistration.test.tsx`, `PassDisplay.test.tsx`, `StaffOperations.test.tsx`, `App.test.tsx`). Frontend production build verified clean (`tsc -b && vite build` in 219ms).
  - **Deliverable:** Created `docs/implementation/SLICE_5D_FRONTEND_IMPLEMENTATION_REPORT.md`.
- **Premium Product Experience & UX Quality Review (Completed):**
  - **Design System Tokens & Theme:** Upgraded `theme.css` with Slate/Zinc neutrals, Operational Indigo brand palette, WCAG AA semantic feedback colors, layered elevation shadows, `--co-focus-ring` focus indicators, and `@media (prefers-reduced-motion: reduce)` override.
  - **Component Styling & Print Stylesheet:** Added tabular figures (`tabular-nums`), segmented navigation switch, and dedicated `@media print` rules stripping navigation chrome, buttons, and dark ink waste for crisp ticket printing.
  - **Accessible Vector Icon Suite:** Built 20+ accessible vector SVGs in `Icons.tsx` replacing platform emojis.
  - **Global Non-Blocking Feedback:** Implemented `ToastProvider` and `useToast()` hook with auto-dismissal for check-ins, copies, pass reissues, and errors.
  - **Layout Stability:** Built shimmer skeletons (`Skeleton.tsx`) eliminating Cumulative Layout Shift (CLS).
  - **Desk Velocity Ergonomics:** Added global `/` shortcut for hardware barcode scanners and `ArrowDown`/`ArrowUp` + `Enter` navigation for search candidates in `CheckInDesk.tsx`.
  - **Dialog Management:** Built focus trapping, focus restoration to previous trigger elements, and `Escape` key close handling in `Dialog.tsx`.
  - **Testing Coverage:** 7 new comprehensive UX tests added in `frontend/src/test/PremiumUX.test.tsx`, raising frontend test suite to **30 passing tests** across 6 test suites. Frontend production build verified clean in 260ms.
  - **Deliverable:** Created `docs/implementation/CAMPUSOPS_PREMIUM_UX_REVIEW.md`.
- **System-Wide Integration Readiness Audit (Prompt 24 Completed):**
  - **Traceability Matrix:** Audited all 15 core capabilities across 63 REST API endpoints. Found Capabilities 10–15 complete and integrated, while Capabilities 1–9 have complete backend foundations but lack frontend interfaces.
  - **Security Invariants Verified:** Proved fail-closed authentication (HTTP 401), tenant isolation (anti-enumeration HTTP 404), atomic capacity reservation, all-or-nothing team admission, individual check-in enforcement, manager-only void audit trails ($\ge 10$ char mandatory reason), tiered contact masking, and spreadsheet formula injection sanitization.
  - **Contract Reconciliation:** Proved frontend and backend agree on body-based POST endpoints (`/passes/verify`, `/registrations/lookup`, `/registrations/cancel`), resolving the legacy URL path discrepancy while maintaining backwards compatibility.
  - **QR Code Inspection:** Audited `frontend/src/utils/qr.ts`; recorded the absence of automated standard decoder testing as an outstanding verification requirement.
  - **Empirical Browser Verification:** Executed headless Edge rendering across desktop (1280px), tablet (768px), and mobile (375px); identified minor mobile navbar wrapping and horizontal overflow at 375px.
  - **Production Gate Assessment:** Reassessed the 8 production gates; affirmed that production pilot remains **STRICT NO-GO**.
  - **Deliverables:** Created `docs/implementation/SYSTEM_INTEGRATION_READINESS_AUDIT.md` and `docs/implementation/NEXT_PHASE_IMPLEMENTATION_BLUEPRINT.md`.
- **Repository Hygiene:** All tracked and newly created files pass strict Git whitespace, line-ending, and dependency compatibility checks. Local test databases are excluded from Git via `.gitignore`.
- **Historical Documentation Integrity:** Authoritative product documents in `Consolidated Documentation/` and historical archives (`Requirement Specification Documents/`, `Decision Logs Documents/`, `Other Documents/`) remain untouched.

---

## 2. Verified Environment & Toolchain

The following runtime and compiler versions were directly verified through CLI execution:

| Tool | Executed Command | Verified Version | Notes |
| :--- | :--- | :--- | :--- |
| **Operating System** | System check | Windows 11 / Windows PowerShell | Host platform verified. |
| **Node.js** | `node --version` | `v26.1.0` | Located at `D:\nodejs\node.exe`. |
| **npm** | `npm --version` | `11.13.0` | Package manager verified. |
| **Python (System)** | `python --version` | `Python 3.13.9` | Primary interpreter at `D:\anaconda3\python.exe`. |
| **Python (Selected)**| `py -3.13 --version`| `Python 3.13.9` | Selected verified interpreter for `backend/.venv`. |
| **Python (Installed)**| `py -3.14 --version`| `Python 3.14.6` | Detected at `AppData\Local\Python\pythoncore-3.14-64\python.exe`. Python 3.13 preferred per pre-flight rule. |
| **Git** | `git --version` | `2.54.0.windows.1` | Baseline commit `7caf0bf`, clean branch `main`. |

---

## 3. Dependency Choices & Pinned Manifests

### 3.1 Backend Dependencies (`backend/requirements.txt`)
Isolated in `backend/.venv` (Python 3.13.9):
- `fastapi==0.162.0`
- `pydantic==2.14.1` (Pydantic v2 strictly enforced; Pydantic v1 prohibited)
- `pydantic_core==2.50.1`
- `uvicorn==0.54.0`
- `pytest==9.2.0`
- `httpx==0.28.1`
- `starlette==1.10.0`
- `anyio==4.15.1`
- `SQLAlchemy==2.1.6` (SQLAlchemy 2.0 DeclarativeBase, pure-Python fallback via `DISABLE_SQLALCHEMY_CEXT="1"`)
- `alembic==1.20.1`
- `Mako==1.4.3`
- `MarkupSafe==3.0.4`

### 3.2 Frontend Dependencies (`frontend/package.json`)
Installed in `frontend/` using npm 11.13.0 and locked in `frontend/package-lock.json`:
- **Core:** `react@^19.3.1`, `react-dom@^19.3.1`
- **Build & Tooling:** `vite@^8.3.5`, `typescript@~7.0.2`, `@vitejs/plugin-react@^6.1.2`, `oxlint@^1.89.0`
- **Testing:** `vitest@^5.0.5`, `jsdom@^30.1.3`, `@testing-library/react@^16.3.3`, `@testing-library/jest-dom@^7.0.1`

---

## 4. Test & Build Execution Evidence

In strict accordance with the truth-in-testing rule (AGENTS.md Section 7), every result below was directly executed and observed:

### 4.1 Backend Test Execution
- **Command:** `backend\.venv\Scripts\python.exe -m pytest backend/tests` (from repo root)
- **Result:**
  ```text
  platform win32 -- Python 3.13.9, pytest-9.2.0, pluggy-1.7.0
  rootdir: D:\Antigravity_Projects\CampusOps\backend
  configfile: pytest.ini
  plugins: anyio-4.15.1
  collected 305 items

  backend\tests\test_api_auth_boundary.py .........                        [  3%]
  backend\tests\test_api_blockers_notifications.py .....                   [  4%]
  backend\tests\test_api_departments.py .......                            [  7%]
  backend\tests\test_api_event_leads.py ......                             [  9%]
  backend\tests\test_api_events.py ..........                              [ 12%]
  backend\tests\test_api_invitations.py .........                          [ 15%]
  backend\tests\test_api_me.py ....                                        [ 16%]
  backend\tests\test_api_organizations.py .........                        [ 19%]
  backend\tests\test_api_programs.py ........                              [ 22%]
  backend\tests\test_api_scoped_invitations.py .....                       [ 23%]
  backend\tests\test_api_slice_5c_registration.py ........................ [ 31%]
  ........                                                                 [ 34%]
  backend\tests\test_api_tasks.py .................                        [ 39%]
  backend\tests\test_domain_models.py ......                               [ 41%]
  backend\tests\test_health.py .                                           [ 41%]
  backend\tests\test_invitation.py .............                           [ 45%]
  backend\tests\test_migrations.py .....                                   [ 47%]
  backend\tests\test_organization.py ........                              [ 50%]
  backend\tests\test_permissions.py ........                               [ 52%]
  backend\tests\test_slice_3a_domain.py .............                      [ 56%]
  backend\tests\test_slice_3a_integrity_audit.py ..........                [ 60%]
  backend\tests\test_slice_3b_event_dates_db.py .......                    [ 62%]
  backend\tests\test_slice_3b_security_audit.py ...........                [ 65%]
  backend\tests\test_slice_4a_security_audit.py ..............             [ 70%]
  backend\tests\test_slice_4a_task_domain.py ..............                [ 75%]
  backend\tests\test_slice_4b_security_audit.py ..............             [ 79%]
  backend\tests\test_slice_5b_registration_domain.py ...................   [ 85%]
  backend\tests\test_slice_5b_security_audit.py ....................       [ 92%]
  backend\tests\test_slice_5c_security_audit.py ......................     [100%]

  ======================= 305 passed, 2 warnings in 25.12s =======================
  ```

### 4.2 Frontend Test Execution
- **Command:** `npm test` (running `vitest run` inside `frontend/`)
- **Result:**
  ```text
  RUN  v5.0.5 D:/Antigravity_Projects/CampusOps/frontend

  ✓ src/test/qr.test.ts (3 tests) 21ms
  ✓ src/test/PassDisplay.test.tsx (3 tests) 779ms
  ✓ src/App.test.tsx (2 tests) 1390ms
  ✓ src/test/PremiumUX.test.tsx (7 tests) 1526ms
  ✓ src/test/StaffOperations.test.tsx (7 tests) 2149ms
  ✓ src/test/PublicRegistration.test.tsx (8 tests) 2236ms

  Test Files  6 passed (6)
       Tests  30 passed (30)
    Duration  6.75s
  ```

### 4.3 Frontend Production Build
- **Command:** `npm run build` (running `tsc -b && vite build` inside `frontend/`)
- **Result:**
  ```text
  vite v8.3.5 building client environment for production...
  transforming...
  ✓ 48 modules transformed.
  rendering chunks...
  computing gzip size...
  dist/index.html                   0.45 kB │ gzip:  0.29 kB
  dist/assets/index-Dd279yQh.css   15.86 kB │ gzip:  3.77 kB
  dist/assets/index-B12YQllx.js   315.18 kB │ gzip: 90.74 kB
  ✓ built in 260ms
  ```

---

## 5. Maintenance Review & Technical Findings

### 5.1 Host Environment C-Extension Policy (Windows AppLocker / WDAC)
- **Finding:** Windows Application Control policy on the host blocks loading native compiled C-extension DLLs (such as SQLAlchemy's `_collections_cy.pyd`).
- **Remediation:** Configured `DISABLE_SQLALCHEMY_CEXT="1"` across `app/config.py`, `app/database.py`, `alembic/env.py`, and `tests/conftest.py`. This instructs SQLAlchemy 2.0 to use its pure-Python implementations cleanly without compromising functionality or stability.

### 5.2 SQLite Pragmas, Timezones & Batch Mode Migrations
- **Foreign Keys:** SQLite does not enforce foreign keys by default. Attached a connection listener on `Engine` (`PRAGMA foreign_keys=ON;`), ensuring relational integrity and foreign key constraints are strictly enforced in dev and test environments.
- **Datetime Normalization:** Implemented `ensure_utc` normalization in `app/services/invitation.py` to handle SQLite's offset-naive datetime serialization, preventing timezone comparison errors against UTC timestamps.
- **Batch Alter Tables:** Configured `render_as_batch=True` in Alembic migrations to support SQLite table reconstructions during schema evolutions.

### 5.3 Slice 2A Security Hardening & Invariant Verification Review
During the Prompt 05 review, the implementation was audited and hardened against the authoritative specifications:
1. **User Identity & Account Status Checks:** `can_perform` and `is_active_platform_admin` explicitly verify `user.account_status == "active"` and `user.email_verified_at is not None`.
2. **Single Primary Administrator Invariant:** Enforced via `has_active_primary_admin(db, organization_id)`. `create_invitation` strictly rejects assigning `PRIMARY_ADMIN`.
3. **Role & Scope Structural Invariants:** Validated role names and allowed scopes (`organization`, `department`, `event`).
4. **Target Resource Scope Verification:** Added `validate_target_resource_scope` in `permissions.py`.
5. **Membership Reactivation on Re-Invitation:** In `accept_invitation`, reactivates previously removed memberships safely avoiding unique constraint violations.
6. **Constant-Time Verification & Org Status Gate:** `accept_invitation` uses `secrets.compare_digest` for token comparison and verifies organization `verified` status.
7. **Concurrency Race Condition Simulation:** Verified atomic update query triggers rollback on concurrent acceptance races.
8. **Explicit Platform Admin Bootstrap:** Created `appoint_platform_admin` in `app/services/platform.py` providing audited bootstrap.

### 5.4 Slice 2B Security Audit & Hardening Remediations
During the Slice 2B audit and Prompt 07 security hardening, the following vulnerabilities, edge cases, and operational requirements were identified, remediated, and verified with dedicated regression tests:
1. **Pre-Account Takeover / Unverified Email Spoofing Defense (`app/auth/principal.py`):**
   - *Vulnerability:* If an attacker presented an unverified token claiming the email of an existing verified user, the previous lookup queried by email and did not check `principal.email_verified` if `user.email_verified_at` was already set in the database, allowing unauthorized session access. Additionally, combined OR queries risked raising `MultipleResultsFound`.
   - *Remediation:* Gated secondary email profile lookups strictly behind `principal.email_verified == True`. If an email is claimed by an existing profile, unverified principals are rejected immediately with HTTP 403 Forbidden without modifying or querying other user records. If the profile is bound to a different `auth_subject_id`, an identity conflict is raised (HTTP 403).
   - *Regression Tests:* `test_unverified_principal_cannot_hijack_existing_verified_account` and `test_auth_subject_conflict_rejected` in `test_api_auth_boundary.py`.
2. **Provider Email Change Lifecycle Hardening (`app/auth/principal.py`):**
   - *Vulnerability/Risk:* If an authenticated user changed their email in an upstream IdP, unverified new email claims could be accepted, or conflicting emails matching another existing user could cause database integrity crashes or unauthorized account takeover.
   - *Remediation:* Enforced that new email claims require `principal.email_verified == True` (returning HTTP 403 otherwise). Checked for collisions with other existing user records (returning HTTP 409 Conflict). Only when verified and collision-free is `user.email_normalized` updated and synchronized.
   - *Regression Tests:* `test_email_change_unverified_rejected`, `test_email_change_conflict_rejected`, `test_email_change_verified_succeeds` in `test_api_auth_boundary.py`.
3. **Stale Role Accumulation on Membership Reactivation (`app/services/invitation.py`):**
   - *Vulnerability:* When a previously removed member accepted a new invitation, legacy role assignments on the membership from the prior tenure were not marked revoked, causing them to re-activate alongside the new role.
   - *Remediation:* Explicitly revoked all prior unrevoked role assignments (`old_ra.revoked_at = now`) when reactivating a membership row.
   - *Regression Test:* Verified in `test_reaccept_invitation_for_previously_removed_member_reactivates_membership` in `test_invitation.py`.
4. **Orphan Invitation Prevention on Email Delivery Crash (`app/api/v1/endpoints/invitations.py`):**
   - *Vulnerability:* If the email delivery provider raised a network or connection exception, the committed invitation remained in the database with an undelivered token.
   - *Remediation:* Wrapped `send_invitation_email` in an exception boundary that deletes the persisted invitation and returns HTTP 503 on any provider crash.
   - *Regression Test:* `test_invitation_creation_rolls_back_on_email_delivery_exception` in `test_api_invitations.py`.
5. **Tiered Role-Based Field Disclosure Controls (`app/api/v1/endpoints/organizations.py`):**
   - *Information Disclosure Risk:* Exposing platform reviewer user IDs (`verification_reviewer_id`) or administrative review notes to all organization members leaks internal operational data and personnel identities.
   - *Remediation:* Implemented tiered serialization in `get_org_details`: Platform Admins see full reviewer audit metadata; Primary Admins see review notes and timestamps (to remediate rejections) with reviewer IDs censored; ordinary members see organization details with reviewer IDs and notes censored (`None`).
   - *Regression Test:* `test_organization_detail_information_disclosure_controls` in `test_api_organizations.py`.
6. **Platform Administrator Workspace Inspection Permission (`app/services/permissions.py`):**
   - *Access Control Gap:* Platform administrators inspecting organization workspaces for verification review were denied `ACTION_VIEW_ORG_PROFILE` because they lacked membership in the tenant organization, causing unexpected 404 responses.
   - *Remediation:* Explicitly authorized active platform administrators (`is_active_platform_admin(db, user.id)`) to perform `ACTION_VIEW_ORG_PROFILE` platform-wide without violating tenant boundary isolation for non-platform actions.
7. **Workspace Profile Visibility for Active Members (`app/services/permissions.py`):**
   - *Defect:* `ACTION_VIEW_ORG_PROFILE` was only granted to `PRIMARY_ADMIN` and `OFFICE_BEARER`, blocking non-admin active members (e.g. `COORDINATOR`, `REGISTRATION_STAFF`) from reading their workspace details.
   - *Remediation:* Extended `can_perform` so that any active member with an active role in the organization can view the organization profile, aligning with the API Contract.
   - *Regression Test:* `test_active_non_admin_member_can_view_organization_profile` in `test_api_organizations.py`.
8. **Operational Platform Administrator CLI Bootstrap (`backend/scripts/bootstrap_platform_admin.py`):**
   - *Privilege Escalation Prevention:* Zero HTTP endpoints exist to appoint platform administrators. Created an operational server-side CLI tool (`backend/scripts/bootstrap_platform_admin.py`) for initial break-glass/first-admin setup with strict validation (existing user profile, active status, verified email, and blocks re-running when active platform admins exist).

### 5.5 Git Whitespace & Encoding Hygiene
- **Verification:** Ran repository-wide automated whitespace scans and `git diff --check`.
- **Result:** Zero trailing whitespaces, zero multiple blank lines at EOF, and valid UTF-8 encoding across all backend and frontend source files.

### 5.6 Slice 3A Database Integrity & Lifecycle Audit Findings & Hardening
During the Slice 3A integrity audit (Prompt 10), the following schema invariants, database constraints, and service boundaries were audited, hardened, and verified with dedicated regression tests:
1. **Multi-Tenant Composite Foreign Key Enforcement (`backend/alembic/versions/d81e3a5f2c90_slice_3a_integrity_hardening.py`):**
   - *Integrity Gap:* Initial migration `c92f1b4a3d10` established foreign keys referencing only primary keys (`id`). While application domain services validated tenant boundaries, direct database operations or bypassing service logic could associate child events, departments, or event lead assignments with entities belonging to other organizations.
   - *Remediation:* Created additive migration `d81e3a5f2c90` that established composite unique constraints `(id, organization_id)` on `programs`, `events`, and `organization_memberships`, and composite foreign keys on all child operational entities (`events (program_id, organization_id) -> programs (id, organization_id)`, `departments (program_id, organization_id) -> programs (id, organization_id)`, `departments (standalone_event_id, organization_id) -> events (id, organization_id)`, `event_lead_assignments (event_id, organization_id) -> events (id, organization_id)`, `event_lead_assignments (membership_id, organization_id) -> organization_memberships (id, organization_id)`).
   - *SQLite / SQL Standard Semantics:* Leveraged standard SQL `MATCH SIMPLE` semantics: nullable parent keys (`program_id` on standalone events, `standalone_event_id` on program departments) evaluate as valid when null, but strictly block cross-tenant parent references whenever non-null.
   - *Regression Tests:* `test_db_blocks_cross_tenant_child_event_insert`, `test_db_blocks_cross_tenant_department_inserts`, and `test_db_blocks_cross_tenant_event_lead_assignment_inserts` in `test_slice_3a_integrity_audit.py`.
2. **Relational Sequencing and Archival Check Constraints:**
   - *Integrity Gap:* Start/end timestamps and dates were unconstrained at the database level, permitting inverted ranges. Status values (`archived`) could diverge from timestamp columns (`archived_at`).
   - *Remediation:* Added database check constraints `ck_events_time_order` (`planned_start_time IS NULL OR planned_end_time IS NULL OR planned_end_time >= planned_start_time`), `ck_programs_date_order` (`planned_start_date IS NULL OR planned_end_date IS NULL OR planned_end_date >= planned_start_date`), and status/archival timestamp consistency constraints (`*_status_archived`) across `programs`, `events`, and `departments`.
   - *Timezone Persistence:* Added non-null `timezone` column (`String(50)`, default `'Asia/Kolkata'`) to `Event` to anchor all local date/time interpretations unambiguously.
   - *Regression Tests:* `test_db_enforces_event_time_sequencing`, `test_db_enforces_program_date_sequencing`, `test_db_enforces_status_archived_consistency`, and `test_event_timezone_persisted_and_default` in `test_slice_3a_integrity_audit.py`.
3. **Event-Lead Eligibility Verification & Atomic Rollback Hardening (`backend/app/services/event.py`):**
   - *Integrity Gap:* `assign_event_lead` checked organization membership status but did not assert underlying `UserProfile` account status (`active`) and email verification status (`email_verified_at is not None`). Furthermore, errors occurring during lead assignment could leave partial role assignment records if not explicitly rolled back.
   - *Remediation:* Hardened `assign_event_lead` and `validate_event_lead_eligibility` to reject suspended or unverified users. Wrapped assignment and revocation operations in explicit database transaction rollback blocks (`try: ... db.commit() ... except: db.rollback(); raise`).
- *Regression Tests:* `test_assign_event_lead_rejects_suspended_or_unverified_member` and `test_assign_event_lead_transaction_rollback_on_failure` in `test_slice_3a_integrity_audit.py`.

### 5.7 Slice 3B REST APIs, Multi-Day Event Scheduling & Scoped Invitations
During Development Slice 3B (Prompt 11), the REST API layer and scoped invitation flows were implemented and verified:
1. **Multi-Day Scheduling & Event Duration Policy (D-SLICE3-05 & Migration `e4f5a6b7c8d9`):**
   - Implemented additive migration `e4f5a6b7c8d9` introducing `event_end_date` and check constraint `ck_events_date_order`.
   - Updated `ck_events_time_order` to support overnight multi-day events when `event_end_date > event_date`.
   - Validated child event dates against parent Program `planned_start_date` and `planned_end_date`.
   - Added `backend/app/services/timezones.py` containing 599 canonical IANA timezones, enabling offline validation on Windows.
2. **Pydantic v2 Contract Discipline (`extra="forbid"`):**
   - All request schemas reject extraneous fields, preventing parameter pollution and client-driven ID overrides.
   - Response schemas strictly omit internal tokens, token hashes, and internal server fields.
3. **Exclusive Departmental Parenting & Anti-Enumeration:**
   - Enforced `program_id` XOR `standalone_event_id` in `POST /departments`.
   - Replaced cross-tenant leakages with uniform HTTP 404 responses.
4. **Scoped Invitations & Atomic Event Lead Assignment:**
   - Unblocked `department` and `event` scope types in `POST /organizations/{id}/invitations` with database-backed entity validation.
   - In `POST /invitations/accept`, accepting an `EVENT_LEAD` invitation atomically provisions both `RoleAssignment(role_name="EVENT_LEAD", scope_type="event")` and `EventLeadAssignment` in a single transaction with rollback protection.

### 5.8 Slice 4A Task Management & Operational Blocker Foundation
During Development Slice 4A (Prompt 13), the core internal operational task and blocker foundation was implemented and verified:
1. **Relational Models & Additive Migration (`f5a6b7c8d9e0`):**
   - Implemented additive Alembic migration `f5a6b7c8d9e0` (`down_revision = 'e4f5a6b7c8d9'`).
   - Defined 10 SQLAlchemy 2.0 models with batch SQLite alterations, partial unique index `uq_task_assignee_active` for single active worker enforcement, composite parent foreign keys, and check constraints for status and priority enums.
   - Verified clean downgrade to base and upgrade to head via `test_migrations.py`.
2. **Mandatory Deadlines & Audit Trail:**
   - Tasks enforce non-null `due_date`, optional `due_time`, and canonical IANA `timezone`.
   - Deadline adjustments require an authorized actor, a non-empty `reason`, and record full audit entries in `TaskDeadlineHistory`.
3. **Multi-Attempt Evidence Submission & Review State Machine:**
   - Proof-required tasks (`proof_required=True`) transition through `submitted_for_review` -> `changes_requested` / `approved`.
   - Direct completion of proof-required tasks without review is strictly blocked.
   - Rejections require a mandatory review note.
   - Dual-review race conditions are eliminated via atomic conditional updates (`update().where(status="pending_review")`).
4. **Strict Self-Review Prohibition:**
   - Submitters and active assignees are forbidden from reviewing or approving their own submissions (`SelfReviewError`).
5. **Staff-Only Operational Blockers & Non-Participant Isolation:**
   - Blockers can be recorded at Organization, Program, Event, Department, or Task scope.
   - Gated to staff roles (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`, `DEPARTMENT_LEAD`, `COORDINATOR`); strictly invisible to attendees and external portals.
   - Resolution requires a mandatory note; reopening is auditable via `OperationalBlockerHistory`.

### 5.9 Slice 4A Task Assignment Policy & Migration Integrity Review
During Prompt 15, an authoritative review of task assignment cardinality and Alembic migration integrity was completed:
1. **Assignment Cardinality Analysis:**
   - Compared authoritative specifications across `Consolidated Documentation/`: Tech Spec 3.3 and Data Model 7.2 intentionally design `TaskAssignee` as a join table supporting one or more assignees to avoid multi-user text packing, while Architecture Traceability Review (row 39) explicitly flags multiple-assignee behavior as an open decision.
   - Evaluated the three distinct constraints: Constraint A (single active assignee per task on `task_id`), Constraint B (multiple active assignees), and Constraint C (single active assignment per membership on `(task_id, membership_id)`).
   - Formulated a clear architectural recommendation for founder review before Slice 4B: continue enforcing single active owner in domain services and at DB level, while maintaining explicit documentation of the open founder decision for future co-assignee workflows.
2. **Migration Immutability Restoration:**
   - Identified that the Prompt 14 audit edited migration `f5a6b7c8d9e0` in place, breaching migration immutability.
   - Restored `f5a6b7c8d9e0` to its exact original definition with `['task_id', 'membership_id']`.
   - Delivered the single active assignee constraint via additive migration `a6b7c8d9e0f1_slice_4a_single_active_task_assignee_index.py` (`down_revision = 'f5a6b7c8d9e0'`).
   - Added automated test `test_slice_4a_assignee_index_migration_lifecycle` in `backend/tests/test_migrations.py` validating full upgrade/downgrade roundtrips across `f5a6b7c8d9e0` and `a6b7c8d9e0f1`.

### 5.10 Slice 4B Task Management & Operational Blocker REST APIs
During Development Slice 4B (Prompt 16), the complete REST API layer was implemented and verified:
1. **Decision D-SLICE4-01 Cemented:**
   - Recorded single accountable task assignee policy in `Consolidated Documentation/CampusOps_Decision_Log_v1.6_Addendum.md`.
2. **Pydantic v2 Request/Response Schemas (`extra="forbid"`):**
   - Implemented schemas in `backend/app/schemas/task.py`, `blocker.py`, and `notification.py` forbidding unknown fields and client ID injection.
3. **Task Endpoints (`backend/app/api/v1/endpoints/tasks.py`):**
   - Implemented creation, listing with filters (`status`, `scope_type`, `scope_id`, `assigned_to_me`, pagination), retrieval, permitted metadata updates, assignment/reassignment (with former assignee authority revocation), work start, cancellation with mandatory reason, deadline change with audit history, and full history retrieval.
4. **Submission & Review Workflows:**
   - Implemented evidence submission (`proof_required` enforcement, safe URL parsing, zero server-side fetches) and review decisions (`approved` transitions to `completed`, `changes_requested` with mandatory note transitions to `changes_requested`, self-review strictly prohibited, replay/contradictory review attempts rejected).
5. **Staff-Only Operational Blockers (`backend/app/api/v1/endpoints/blockers.py`):**
   - Implemented internal staff-only routes for blocker creation, listing, retrieval with history, metadata updates, resolution with mandatory note, and reopening with mandatory reason. Public/attendee access is excluded.
6. **In-App Notifications (`backend/app/api/v1/endpoints/notifications.py`):**
   - Implemented routes for listing user notifications (with unread filter), retrieving single notification, and marking as read. Recipient boundary enforced (`user_id == current_user.id`).
7. **Testing Coverage:**
   - 22 new HTTP integration tests across `test_api_tasks.py` and `test_api_blockers_notifications.py`. Total backend test suite reached 196 passing tests.
8. **Deliverables:**
   - Created `docs/implementation/SLICE_4B_API_CONTRACT.md` and `docs/implementation/SLICE_4B_IMPLEMENTATION_REPORT.md`.

### 5.11 Slice 4B REST API Security, Authorization & Transaction Audit Findings
During Prompt 17, the Slice 4B REST APIs were audited and hardened against authorization, tenancy, and transactional criteria:
1. **Blocker Anti-Enumeration & Tenancy Hardening (`app/api/v1/endpoints/blockers.py` & `app/services/task.py`):**
   - Implemented `_ensure_blocker_in_org` across all blocker item routes (`GET`, `PATCH`, `POST /resolve`, `POST /reopen`) and added `organization_id` delegation in service methods, preventing cross-tenant existence enumeration (returning uniform HTTP 404) and URL tenant tampering by dual-members.
2. **Removed Member Active Assignment Invalidation (`app/services/task.py` & `app/models/task.py`):**
   - Hardened `start_task`, `submit_task_evidence`, deadline notifications, and `@property active_assignee` to assert active membership status (`membership_status == 'active'` and `removed_at is None`), blocking revoked members immediately.
3. **Strict Self-Review Prohibition & Concurrency Replay Defense:**
   - Verified that submitters and active assignees are strictly prevented from reviewing their own submissions (HTTP 400), even when holding elevated workspace roles.
   - Verified conditional atomic updates prevent double-review races on already approved or rejected submissions.
4. **Scope-Level Boundary Enforcement & Coordinator Ceiling:**
   - Proved that Event Leads and Department Leads cannot view or mutate sibling scope tasks or blockers (returning HTTP 403, and excluded from listing endpoints).
   - Proved Coordinators are restricted to read-only operations and proof submissions (when assigned), and cannot perform metadata updates, deadline changes, cancellations, reviews, or blocker resolutions.
5. **Testing Coverage:**
   - 14 new comprehensive security audit regression tests in `backend/tests/test_slice_4b_security_audit.py`. Total backend test suite now stands at **210 passing tests**.
6. **Deliverables:**
   - Created `docs/implementation/SLICE_4B_SECURITY_AUDIT_REPORT.md`.

### 5.12 Slice 5A Participant Registration, Ticketing & Attendance Architecture
During Prompt 18, the complete product scope, relational architecture, API contracts, security model, and acceptance-test plan were established for Slice 5:
1. **Relational Schema Design (`docs/implementation/SLICE_5_SCHEMA_RELATIONSHIP_PLAN.md`):**
   - Designed 7 normalized tables: `event_registration_settings`, `registrations`, `participants`, `registration_participants`, `tickets`, `check_ins`, and `check_in_corrections`.
   - Enforced composite foreign keys `(organization_id, event_id)` for multi-tenant boundary integrity.
   - Enforced partial unique indexes: `uq_participants_event_email` (one participant per email per event), `uq_ticket_participant_active` (single active pass per participant), and `uq_check_in_event_participant` (single active check-in per participant).
2. **API Contract Draft (`docs/implementation/SLICE_5_API_CONTRACT_DRAFT.md`):**
   - Public namespace: `/api/v1/public/events/{registration_key}/...` with unguessable keys, rate limiting, and honeypot validation for public registration, status queries, and pass retrieval.
   - Staff namespace: `/api/v1/organizations/{org_id}/events/{event_id}/...` for registration settings, walk-ins, cancellations, roster queries with contact masking, pass verification, QR and manual check-ins, check-in voids with mandatory audit reason, summaries, and CSV export.
3. **Acceptance Test Matrix (`docs/implementation/SLICE_5_ACCEPTANCE_TEST_PLAN.md`):**
   - 48 exhaustive test cases across 8 functional and security categories covering happy paths, negative boundaries, sibling isolation, concurrency races, privacy masking, void audit logs, and Alembic roundtrips.
4. **Formal Decision Log Closure (`Consolidated Documentation/CampusOps_Decision_Log_v1.7_Addendum.md`):**
   - `D-SLICE5-01`: Capacity measured in individual human bodies; atomic reservation logic prevents overselling.
   - `D-SLICE5-02`: Ticketing defined as digital non-payment admission pass; zero PII in QR codes.
   - `D-SLICE5-03`: Registrations strictly scoped to individual events (no monolithic program pass merging).
   - `D-SLICE5-04`: Check-in voids restricted to managers (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`) with mandatory immutable audit history in `check_in_corrections`.
5. **Design-Only Discipline:**
   - Strictly no application code, database migrations, or endpoints implemented in this slice.

### 5.13 Slice 5B Domain Foundation Findings & Implementation Details
During Development Slice 5B (Prompt 19), the core registration, ticketing, and check-in domain foundation was implemented and verified:
1. **Shared Email Policy & Participant Modeling (FA-007):**
   - *Architecture Choice:* In academic and campus environments, students, lab partners, or family members may register using shared department or family email addresses. Imposing a database-level unique constraint `(event_id, email_normalized)` would prevent legitimate multi-participant registrations or team submissions.
   - *Implementation:* The schema employs a non-unique index `ix_participants_event_email`. Distinct participants sharing an email receive distinct `Participant` records, separate UUIDs, unique tickets, and separate check-in records. Duplicate submissions are controlled via `idempotency_key` on `Registration` and intra-team duplicate participant validation.
2. **Raw Token Non-Persistence & Hash-Only Verification:**
   - *Security Defense:* Admission pass codes (`CO-PASS-<HEX>`) are never persisted in raw form in any database table. The `tickets` table persists only `pass_code_hash` (SHA-256).
   - *Issuance & Verification:* Raw pass codes are returned only once at issuance boundary via `IssuedTicketDTO`. Verification hashes candidate input and performs constant-time equality checks using `hmac.compare_digest`.
3. **Atomic Individual Capacity Accounting (D-SLICE5-01):**
   - *Concurrency Safety:* Registration capacity counts individual attendees (`len(participants)`), not registrations. To prevent race conditions and overselling without coarse table locks, slot reservation executes via conditional atomic SQL update: `UPDATE event_registration_settings SET current_confirmed_count = current_confirmed_count + :slots WHERE event_id = :event_id AND current_confirmed_count + :slots <= capacity_limit`.
   - *All-or-Nothing Team Invariant:* Teams are admitted in full or waitlisted; partial team reservations are prohibited.
4. **Individual Attendance Invariant for Team Passes:**
   - *Operational Rule:* Even when participants register together as a team, attendance check-in operates strictly per individual person. Checking in one team member marks only that member as present, while teammates remain unchecked until their passes are scanned.
5. **Manager-Only Check-In Correction Authority (D-SLICE5-04):**
   - *Auditability & Privilege Separation:* Regular registration staff (`REGISTRATION_STAFF` / `COORDINATOR`) holding `ACTION_CHECK_IN` are restricted to admitting attendees; they cannot void check-ins. Voiding or correcting a check-in requires manager authority (`ACTION_CORRECT_CHECK_IN`), a minimum 10-character rationale, and records an append-only entry in `check_in_corrections`.

### 5.14 Slice 5B Registration, Ticketing & Attendance Security Audit Findings & Hardening
During Prompt 20, an independent security and database-integrity audit was conducted across the Slice 5B registration domain:
1. **Alembic Additive Hardening Migration (`c8d9e0f1a2b3`):**
   - *Database Concurrency Defense:* Replaced non-unique `ix_registrations_idempotency` with partial unique index `uq_registrations_event_idempotency` (`['event_id', 'idempotency_key'] WHERE idempotency_key IS NOT NULL`), preventing concurrent duplicate submissions for the same event at the database engine level.
   - *Public Registration Key Uniqueness:* Upgraded `ix_event_reg_settings_key_hash` to partial unique index `uq_event_reg_settings_key_hash` (`['registration_key_hash'] WHERE registration_key_hash IS NOT NULL`), guaranteeing that public capability URLs resolve unambiguously to at most one event.
   - *Lifecycle Roundtrip:* Verified incremental upgrade and downgrade roundtrips in `test_migrations.py`.
2. **Credential Security & Unguessable Key Threat Model:**
   - Proved 128-bit cryptographic entropy in `generate_ticket_credential()` (`CO-PASS-<HEX>`), non-persistence of raw tokens (SHA-256 only stored in `tickets.pass_code_hash`), constant-time verification using `hmac.compare_digest`, absence of credentials in `Ticket.__repr__`, and zero PII in passes.
   - Implemented `generate_registration_key()` and added key rotation capability (`rotate_registration_key: bool = False`) in `update_registration_settings`.
3. **Relational Isolation & Scope Integrity:**
   - Verified via direct SQL tests that composite foreign keys `(event_id, organization_id)` strictly block cross-tenant registrations, participants, and settings, and prevent cross-event ticket, registration-participant, and check-in associations at the database engine level.
4. **Attendance Query Safety & Multi-Ticket Handling:**
   - Hardened manual roster check-in in `check_in_participant` to query active `status == 'issued'` tickets first, falling back to `status == 'used'` only for duplicate scan idempotency. This eliminates potential `MultipleResultsFound` exceptions when replacement passes exist.
   - Hardened `issue_replacement_ticket` to revoke all prior non-cancelled (`issued`, `used`) tickets for the participant with audit timestamp and reason before issuing a replacement.
5. **Transitive Scope Archival Protection:**
   - Enforced that child events under archived parent programs cannot accept registrations or be opened for registration in `_validate_event_and_settings_for_registration` and `update_registration_settings`.
6. **Diagnostic Reconciliation Engine:**
   - Built `reconcile_event_registration_counts(db, event_id, auto_fix=False)` providing exact verification between stored counters and active database rows.

### 5.15 Slice 5C Participant Registration, Ticketing & Attendance REST API Implementation
During Development Slice 5C (Prompt 21), the complete public and staff REST API layer for registration, ticketing, and check-in was implemented and verified:
1. **Public Self-Service Registration Namespace (`/api/v1/public/...`):**
   - Addressed by unguessable registration keys (`reg_<32-hex>`), returning public event parameters, registration format, team limits, and capacity availability.
   - Pydantic v2 `extra="forbid"` models reject unknown parameters or client-supplied IDs.
   - Submissions issue unguessable digital admission passes (`CO-PASS-<HEX>`) with zero PII in passes or QR payloads.
   - Safe idempotency replay returns prior registration details with pass tokens redacted (`<REDACTED_AFTER_ISSUANCE>`).
   - Conflicting payloads with matching idempotency keys return `HTTP 409 Conflict`.
   - Unguessable confirmation code lookup protects attendee contact details. Self-service cancellation verifies contact email identity and restores event capacity.
2. **Staff Operational Namespace (`/api/v1/organizations/{org_id}/events/{event_id}/...`):**
   - Gated by deny-by-default role permissions (`ACTION_VIEW_REGISTRATIONS`, `ACTION_MANAGE_REGISTRATION_SETTINGS`, `ACTION_CHECK_IN`, `ACTION_CORRECT_CHECK_IN`, `ACTION_EXPORT_PARTICIPANTS`).
   - Ordinary registration desk volunteers (`REGISTRATION_STAFF`) receive masked contact info (`mask_email`, `mask_phone`). Unmasked contact info requires `ACTION_VIEW_ATTENDEE_CONTACT`.
   - Check-ins support QR scan and manual roster lookup. Duplicate scans return `status: "already_checked_in"` without inflating attendance counts.
   - Managerial check-in voids (`ACTION_CORRECT_CHECK_IN`) enforce a minimum 10-character explanation, revert ticket/participant status, decrement attendance, and record an immutable audit entry in `check_in_corrections`. Desk volunteers are denied (`HTTP 403 Forbidden`).
   - Roster export streams CSV format strictly gated by `ACTION_EXPORT_PARTICIPANTS`.
3. **Transaction Safety:**
   - Savepoint isolation via `with db.begin_nested():` ensures that failed capacity reservations or validation errors rollback cleanly without corrupting session state or outer fixtures.

### 5.16 Slice 5C Public API Security, Privacy & Transaction Audit Findings & Hardening
During Prompt 22, an independent security, privacy, transaction integrity, and abuse-prevention audit was conducted across the completed Slice 5C REST API layer:
1. **URL Credential Exposure Mitigation:**
   - *Threat Surface:* Raw bearer tokens (`pass_code`) and capability references (`confirmation_code`) in GET/POST URL paths leak into browser history, access logs, referer headers, and proxy telemetry.
   - *Hardening:* Introduced secure POST body endpoints:
     - `POST /public/events/{key}/passes/verify` accepting `{"pass_code": "..."}`.
     - `POST /public/events/{key}/registrations/lookup` accepting `{"confirmation_code": "..."}`.
     - `POST /public/events/{key}/registrations/cancel` accepting `{"confirmation_code": "...", "contact_email": "...", "cancellation_reason": "..."}`.
   - Retained legacy GET/path routes for backward compatibility.
2. **Spreadsheet Formula Injection Sanitization (CWE-1236):**
   - *Threat Surface:* Registrants entering names or text fields beginning with formula execution characters (`=`, `+`, `-`, `@`, `\t`, `\r`) could trigger dynamic formula or DDE command execution when staff open exported CSV files in Excel or Google Sheets.
   - *Hardening:* Implemented `sanitize_csv_cell(...)` in `app/services/registration.py` and applied to all user-controllable columns in `export_event_roster_csv`. Prepends `'` to neutralize formula triggers.
3. **Registration Transaction Privacy:**
   - Enforced tiered contact masking on `GET .../registrations` headers: callers lacking elevated `ACTION_VIEW_ATTENDEE_CONTACT` receive masked `contact_email` and `contact_phone`.
4. **Registration Key Rotation & Transitive Program Archival:**
   - Enhanced `update_registration_settings` to transiently attach the generated `public_registration_key` to the response DTO so managers can immediately distribute it upon rotation.
   - Verified that archiving parent programs transitively invalidates public and staff access for child events.
5. **Dedicated Security Audit Test Suite:**
   - Authored `backend/tests/test_slice_5c_security_audit.py` with 22 dedicated test cases proving all audit guarantees (zero PII in passes, uniform 404s on tampered tokens, idempotency replay with safe credential redaction `<REDACTED_AFTER_ISSUANCE>`, volunteer roster masking, manager-only voiding with >= 10 chars explanation, duplicate scan idempotency with `already_checked_in`, all-or-nothing team capacity rollback, and single active ticket invariants). Total backend test suite reached **305 passing tests**.

### 5.17 Slice 5D Frontend Implementation, Premium UX Review & System Readiness Audit
During Slice 5D (Prompts 23 & 24), the complete public participant and staff event operations frontend was implemented in React 19 + TypeScript + Vite:
1. **Public Self-Service Registration Views:**
   - Event overview displaying dates, times, venue, description, format badges, and live capacity meters.
   - Dual registration forms: Individual registration and Team registration (with dynamic member addition/removal, lead contact fields, and team size boundaries).
   - Real-time client-side field validation, double-submission protection, and honeypot spam protection.
   - Self-service confirmation code lookup modal.
2. **Admission Pass & Zero-PII Digital Tickets:**
   - Individual and team digital pass display with scannable QR code generator, ticket references, and event date/time.
   - Pure-SVG client-side QR generator avoiding external CDN dependencies.
   - Single-use raw pass token reveal with sensitive-credential handling boundaries.
3. **Staff Event Desk & Operations Suite:**
   - Check-in desk with dual operation modes: fast QR/pass-code verification and instant roster candidate search with direct check-in actions.
   - Participant roster table with real-time text search, status filters (`registered`, `checked_in`, `waitlisted`, `cancelled`), and role-based contact masking indicators.
   - Attendance summary analytics card with live metric badges, percentage progress bars, capacity breakdown, and manual refresh controls.
   - Managerial check-in correction modal (`ACTION_CORRECT_CHECK_IN`) requiring a 10-character minimum audit explanation.
   - Participant detail view showing pass hash, check-in history, registration timestamp, and replacement ticket issuance.
4. **Premium UX & System Integration Audit:**
   - System-wide design system tokens, accessible keyboard shortcuts, toast notification provider, high-contrast states, and empirical browser validation across 1280px, 768px, and 375px viewports.

### 5.18 Slice 5D Technical Closure & Verification Remediations (Prompt 25)
During Prompt 25, the four outstanding technical remediation items identified by the System Integration Readiness Audit were closed and verified:
1. **Removal of Legacy Capability-Bearing URL Routes:**
   - In `backend/app/api/v1/endpoints/public_registration.py`, removed legacy routes accepting raw tokens in paths (`GET /passes/{pass_code}`, `GET /registrations/{confirmation_code}`, `POST /registrations/{confirmation_code}/cancel`).
   - Deprecated and eliminated formatting raw pass codes into `pass_url` strings (set to `None`).
   - Standardized on body-based POST endpoints (`POST /passes/verify`, `POST /registrations/lookup`, `POST /registrations/cancel`).
   - Regression test `test_public_capability_legacy_get_endpoints_removed` verifies legacy routes return HTTP 404.
2. **Independent QR Code Decoding Verification (`jsQR 1.4.0`):**
   - Installed `jsqr` in `frontend/package.json` for automated verification.
   - Identified and resolved two critical encoding bugs in `frontend/src/utils/qr.ts`:
     - Top-left format information bits were ordered LSB-first instead of MSB-first per ISO/IEC 18004 Figure 25.
     - Dark module at coordinate $(4 \times \text{version} + 9, 8)$ was overwritten by format bit 7 due to an index bounds error (`i < 8` vs `i < 7`).
   - Implemented rasterized SVG decoding test suite validating 100% decode success across short, medium (`CO-PASS-...`), long, and special-character payloads across ECC levels L, M, Q, and H.
3. **ISO/IEC 18004 Standards-Compliant Dynamic Mask Penalty Evaluation:**
   - Replaced hardcoded Mask 0 with dynamic penalty calculation ($N_1..N_4$) evaluating all 8 standard mask patterns ($0 \le m \le 7$) and selecting the minimal-penalty mask for each payload.
   - Corrected alignment pattern step coordinates for Versions 2–6 (`[18]`, `[22]`, `[26]`, `[30]`, `[34]`) and sequenced timing patterns before alignment patterns.
4. **Mobile Navigation & Responsive Viewport Overflow:**
   - Converted `.co-navbar` into a responsive column layout at $\le 640\text{px}$ in `components.css`.
   - Prevented badge wrapping with `white-space: nowrap; flex-shrink: 0;`.
   - Enhanced `Footer.tsx` and error lookup buttons with responsive flex wrapping, eliminating all horizontal scrolling at 375px.

### 5.19 Phase 1 Workspace, Organization & Team Management Frontend Implementation (Prompt 26)
During Prompt 26, Phase 1 of the Next-Phase Implementation Blueprint was implemented and verified:
1. **Workspace Provisioning & Switching:**
   - Implemented `CreateOrgModal` connected to `POST /api/v1/organizations` with client-side field validation and clear FPC-02/FPC-03 policy guidance.
   - Built `OrganizationSwitcher` connected to `GET /api/v1/organizations` enabling seamless context switching between authorized workspaces and instant creation triggers.
2. **Institutional Verification & Administrative Audit:**
   - Implemented `VerificationBanner` communicating `pending_verification`, `verified`, and `rejected` states with tiered audit feedback (`verification_note`, review timestamp).
   - Created `PlatformVerifyModal` connected to `POST /api/v1/organizations/{id}/verify`, restricted to platform administrators with mandatory rejection rationale.
3. **Role-Scoped Invitations & Token Acceptance:**
   - Built `InviteMemberModal` connected to `POST /api/v1/organizations/{id}/invitations` allowing invitation of valid backend roles (`OFFICE_BEARER`, `COORDINATOR`, `DEPARTMENT_LEAD`, `EVENT_LEAD`, `REGISTRATION_STAFF`). Enforced that invitations remain disabled while workspace verification is pending.
   - Gracefully handled `HTTP 503 Service Unavailable` when transactional email provider is unconfigured (FPC-06 fail-closed policy).
   - Implemented `InvitationAcceptView` submitting raw tokens strictly through JSON POST body (`POST /api/v1/invitations/accept`), mapping 401, 403, 404, 409, and 400 error states.
4. **Member Directory & Revocation Management:**
   - Implemented `MemberDirectoryTable` displaying current user membership, assigned roles, search filters, and session-dispatched invitation revocation (`POST .../invitations/{id}/revoke`).
   - Formally documented missing backend endpoints `GET /organizations/{id}/members` and `GET /organizations/{id}/invitations` for multi-user tenant rosters.
5. **Testing Coverage:**
   - Added 18 new automated frontend tests in `frontend/src/test/WorkspaceTeam.test.tsx` and `App.test.tsx`. Total frontend test suite expanded from 35 to **53 passing tests**.

- **Phase 1.1 Organization Management Closure (Completed & Verified — Prompt 27):** Completed the organization-management capabilities identified during Phase 1:
  1. **Secure Invitation URL Fragment Routing:**
     - Replaced legacy query parameter routing with secure URL fragment `#token=...` / `#invite_token=...`.
     - Extracted token into ephemeral component state and immediately scrubbed the fragment from browser address bar and history via `window.history.replaceState` before any network request.
     - Rejected legacy query parameter URLs (`?token=...`) with an explicit security alert and manual-entry fallback; zero query parameter acceptance.
     - Enforced that invitation tokens are never written to `localStorage`, `sessionStorage`, or cookies.
  2. **Organization-Wide Member Directory API:**
     - Implemented `GET /api/v1/organizations/{organization_id}/members`.
     - Enforced tenant isolation: active membership or platform admin authority required; uniform HTTP 404 for non-members and missing/archived organizations.
     - Enforced contact privacy disclosure rules: managers (`PRIMARY_ADMIN`, `OFFICE_BEARER`), platform admins, and users viewing their own record receive unmasked email; ordinary members viewing other members receive masked email (`mask_email()`). Returned explicit `email_masked: bool` flag.
     - Supported status filtering and offset/limit pagination.
  3. **Organization-Wide Invitation Directory API:**
     - Implemented `GET /api/v1/organizations/{organization_id}/invitations`.
     - Gated by role management authority (`ACTION_MANAGE_ROLES` or `ACTION_INVITE_MEMBER`); unauthorized members receive HTTP 403 Forbidden; non-members receive uniform HTTP 404.
     - Supported status filtering (`pending`, `accepted`, `revoked`, `expired`) with dynamic expiration calculation and offset/limit pagination.
     - Strictly excluded `raw_token` and `token_hash` from responses.
  4. **Frontend Directory Integration:**
     - Updated `frontend/src/api/types.ts` with `OrganizationMemberResponse`.
     - Added `listOrganizationMembers` and `listOrganizationInvitations` to `frontend/src/api/organizations.ts`.
     - Integrated `MemberDirectoryTable.tsx` with live API queries, loading spinners, error alerts with retry, status filters, pagination controls, and privacy `Masked` badges.
     - Integrated `WorkspaceOverview.tsx` and `InvitationAcceptView.tsx`.
  5. **Testing Coverage:**
     - Backend test suite expanded from 305 to **310 passing tests** (5 new integration tests in `test_api_organizations.py` and `test_api_invitations.py`).
     - Frontend test suite expanded from 53 to **59 passing tests** (6 new automated tests in `WorkspaceTeam.test.tsx`).
     - Production build verified (`tsc -b && vite build` clean in 145ms).

---

## 6. Technical Gate Tracking

| Gate | Category | Required Validation | Current Status |
| :--- | :--- | :--- | :--- |
| **TG-01** | Toolchain Baseline | Confirm local Python virtual environment and Node workspace setup on Python 3.13 / Node 26. | **PASSED** (Backend venv & frontend build verified) |
| **TG-02** | Authentication Spike | Evaluate Supabase Auth candidate: server-side JWT verification via JWKS in FastAPI, token expiry, invitation acceptance, and TOTP MFA. | **Spike Specification Ready / External Provider Blocked** (Cryptographic validation verified on Python 3.13; live container/hosted testing blocked by stopped Docker daemon and unconfigured credentials; candidate conditionally recommended; report in `docs/implementation/SLICE_2C_AUTH_FEASIBILITY_REPORT.md`) |
| **TG-03** | Database & Migrations | Initialize schema with SQLAlchemy/Alembic enforcing organization tenancy and unique constraints. | **PASSED (Slice 5B Hardened Migration Baseline)** (Alembic migrations `880d8e4eb890`, `c92f1b4a3d10`, `d81e3a5f2c90`, `e4f5a6b7c8d9`, `f5a6b7c8d9e0`, `a6b7c8d9e0f1`, `b7c8d9e0f1a2`, and `c8d9e0f1a2b3`; batch mode for SQLite, relational integrity, composite foreign keys for multi-tenancy, partial unique indexes for active tickets/check-ins/idempotency/keys, and 17 domain models verified) |
| **TG-04** | API Contract Freeze | Freeze OpenAPI path schemas and Pydantic models for `/me`, `/organizations`, `/invitations`, `/programs`, `/events`, `/departments`, `/tasks`, `/blockers`, `/notifications`, and Slice 5 registration/check-in. | **PASSED (Slice 5C APIs Audited, Hardened & Body-Based Post Standardized)** (Pydantic v2 models with `extra="forbid"`, fail-closed auth, scoped invitations, task management, proof review, blockers, notifications, Slice 5 public and staff registration endpoints, body-based verification endpoints, 310 backend tests verified; formal contract in `docs/implementation/SLICE_5C_API_CONTRACT.md`) |
| **TG-05** | Test Framework Baseline | Establish backend pytest and frontend vitest suites with automated execution. | **PASSED** (310 backend tests across 25 suites, 59 frontend tests across 7 suites passing, clean production build) |
| **TG-06** | Evidence Storage | Validate private object storage adapter and signed upload/download URLs before task file proof is enabled. | **Deferred** (Evidence links validated safely without server fetch; file uploads deferred to future storage adapter slice) |
| **TG-07** | Production Pilot | Deploy on target cloud region, configure custom SMTP, test DB backup/restore, enforce admin MFA, and test manual fallback. Incorporates operational sub-criteria TG-07.1 through TG-07.8 (Identity Provider, PostgreSQL parity, distributed rate limiting, private storage, structured logging/APM, PITR backups, deployment containers, and secret management). | **NO-GO** (Blocked until pilot readiness checklist is satisfied) |

---

## 7. Recommended Next Steps

1. **Next Phase Implementation Blueprint (Phase 2):** Implement Programs, Events & Department Structure Frontend (`docs/implementation/NEXT_PHASE_IMPLEMENTATION_BLUEPRINT.md` Phase 2): Dual setup journeys (Standalone Event Workflow A vs Multi-Event Program Workflow B), date/time pickers, and Event Lead assignments.
2. **Next Phase Implementation Blueprint (Phase 3):** Implement Task & Proof Hub Frontend (Task creation, assignees, deadlines, proof review, and submission forms).
3. **TG-02 Hosted / Container Verification:** Execute live verification against a running Supabase instance (disposable cloud project or containerized CI) once credentials or container infrastructure are provided.
