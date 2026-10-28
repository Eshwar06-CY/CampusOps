# CampusOps — Architecture Decision Record (ADR) v0.1

**Status:** Proposed for review — not approved for implementation  
**Version:** 0.1  
**Date:** 28 October 2026  
**Related documents:**
- `CampusOps_Requirements_Specification_v0.9.md`
- `CampusOps_Role_and_Permission_Matrix_v0.1.md`
- `CampusOps_Data_Model_and_Relationship_Map_v0.1.md`
- `CampusOps_Decision_Log_v0.4.md`

**Working constraint:** Product and architecture documentation only. This record does not authorize coding, dependency installation, deployment, or changes to the project folder.

---

## 1. Purpose

This record proposes a maintainable, security-conscious architecture for CampusOps, an event-operations platform for both standalone events and multi-event programs.

The architecture must support:

- An organization workspace with individual user accounts.
- Verified organization onboarding and invited team members.
- Configurable roles and permissions with organization, program, event, department and task scopes.
- Two setup experiences: standalone event and multi-event program.
- Task ownership, specific deadlines, progress history, evidence submission and approval.
- Native registration plus selected external registration integrations.
- Individual attendance verification for each participant, including people registered as part of a team.
- Post-event reporting and private evidence storage.
- Leadership changes without shared passwords or loss of historical attribution.

Marketing management, promotional campaign tracking, and participant-facing questions/issues are explicitly outside product scope. Internal team tasks, task blockers and review notes remain in scope where required by the workflow.

## 2. Architectural principles

1. **Start with a modular monolith.** Keep one backend application with clear internal modules. Do not introduce microservices, Kubernetes, Redis or separate worker infrastructure until validated scale or workload justifies them.
2. **One source of truth for operational records.** Event, task, assignment, registration, check-in and report records should be stored in the CampusOps database. External tools may be sources for imported registrations, but imported data must be mapped and reconciled explicitly.
3. **Authenticate the person; authorize every action.** A valid login proves identity, not permission. The server must check organization and resource scope on every protected operation.
4. **Use relational constraints for critical invariants.** Duplicate check-ins, invalid ownership, cross-organization links and inconsistent event/program relationships should be prevented by suitable database constraints and transactional operations wherever practical.
5. **Keep UI workflows distinct and underlying concepts shared.** Standalone events and multi-event programs have different setup flows, but can reuse core event, task, registration, check-in and reporting concepts.
6. **Keep uploaded evidence private.** Files and links submitted for task proof or post-event records must be accessible only to authorized users. Avoid permanent public URLs for private evidence.
7. **Minimize sensitive information.** Store only data needed for event operations, make access explicit, and define retention and deletion rules before real participant data is collected.
8. **Prove the technology choices before committing.** Pricing, service availability, account limits, region/data-residency needs and provider-specific restrictions must be checked before selecting hosted services.

## 3. Proposed high-level architecture

```text
Browser
  └── React + TypeScript + Vite web application
        └── HTTPS API calls with a short-lived/managed-auth session token
              └── FastAPI modular backend
                    ├── Identity and membership integration
                    ├── Organization and workspace module
                    ├── Roles, permissions and invitations
                    ├── Events, programs and departments
                    ├── Tasks, evidence and review workflow
                    ├── Registration imports and native registrations
                    ├── Individual check-in and attendance
                    ├── Post-event reports
                    ├── Notifications/email adapter
                    └── Audit history
                          ├── PostgreSQL relational database
                          ├── Private object storage for evidence files
                          └── External provider adapters (e.g. Google Forms, email)
```

This is a conceptual boundary diagram, not a deployed topology. Hosting, authentication provider, object-storage vendor, email vendor and deployment region remain unselected.

## 4. ADR-001 — Application architecture

**Status:** Proposed recommendation

### Context

CampusOps has related workflows and a relatively small initial delivery team. The product needs clear boundaries and testability, but no evidence currently justifies distributed services or infrastructure complexity.

### Options considered

- **A. Modular monolith:** one backend deployable, organized into business modules.
- **B. Microservices:** independently deployed services for identity, events, registration, notifications and reporting.
- **C. Frontend-only/serverless fragments:** separate service functions and vendor-specific application logic without a coherent backend boundary.

### Recommendation

Choose **A — a modular monolith** for the initial product. Define module boundaries in code and API contracts so that future separation is possible if a real need emerges.

### Consequences

- Simpler local development, deployment, debugging and end-to-end testing.
- Transactions can cover operations such as attendance recording and task review without distributed transaction design.
- Modules must not become a single tangled codebase; each should own its business rules and data access patterns.
- A future scale requirement can justify selectively extracting a service later.

### Reconsider when

A measurable operational reason—such as independently scaled workloads, separate reliability requirements, or team ownership constraints—makes service separation worthwhile.

## 5. ADR-002 — Frontend and backend stack

**Status:** Proposed recommendation

### Recommendation

- **Frontend:** React + TypeScript + Vite.
- **Backend:** Python + FastAPI + Pydantic.
- **ORM and migrations:** SQLAlchemy plus Alembic, subject to a small technical validation spike.
- **API style:** versioned HTTP JSON API for browser-facing operations; document request/response schemas and error formats.
- **Testing:** pytest for backend behavior; Vitest/React Testing Library for frontend behavior; Playwright for critical end-to-end workflows.

### Rationale

This stack aligns with the founder's existing experience, supports typed frontend components and validated backend contracts, and is appropriate for a modular application. Final versions and dependency compatibility must be confirmed against the actual development environment before installation.

### Consequences and controls

- Treat request validation as a boundary, not a replacement for domain authorization.
- Keep secrets and privileged database credentials on the server.
- Avoid calling the database directly from UI components.
- Centralize API error semantics and validation messages.
- Run migration and type/lint checks in CI once the repository exists.

## 6. ADR-003 — Relational database and data integrity

**Status:** Proposed recommendation

### Recommendation

Use **PostgreSQL** as the primary operational database, with explicit migrations and constraints.

### Reasons

CampusOps has relational data and cross-entity invariants: users and organization memberships; organization/program/event scopes; shared departments; task assignments; evidence submissions and reviews; registrations; registration participants; and individual check-in records. Transactions and relational constraints fit these needs.

### Required controls

- Use explicit foreign keys, uniqueness constraints and appropriate check constraints.
- Validate that all linked records belong to the same organization and compatible program/event scope.
- Use a transaction for check-in recording and task approval transitions.
- Enforce individual check-in idempotency so duplicate requests do not create a second successful check-in.
- Use explicit status history/audit records for important state changes.
- Create indexes for common list/search paths only after reviewing query patterns.
- Do not store uploaded binary files as ordinary database rows unless a specific, documented reason justifies it; store file metadata and access references in PostgreSQL.

### Data-model warning

A simple `(scope_type, scope_id)` pair without enforced references can permit invalid scope references. Use a design with enforceable foreign keys/check constraints or separate scope-specific tables, then validate scope compatibility in the service layer and tests.

## 7. ADR-004 — Authentication and individual accounts

**Status:** Proposed recommendation; provider not selected

### Context

Every office bearer, lead, coordinator and team member has an individual account. The organization is a workspace, not a shared login. Invitations may target a new or existing CampusOps user.

### Options considered

- Build and operate authentication/password recovery within CampusOps.
- Use a managed identity provider and integrate its verified identities with CampusOps membership records.

### Recommendation

Prefer **managed authentication** for the initial release, subject to cost, provider terms, availability and integration testing. Supabase Auth is one candidate because it supports managed sign-in flows and JWTs, but it is not selected by this document. Other providers can be evaluated against the same criteria.

### Requirements regardless of provider

- Do not store plaintext passwords. Prefer not to operate password storage ourselves in the first release.
- Verify email ownership before activating sensitive account/workspace actions.
- Support password recovery and session revocation.
- Bind invitation acceptance to the intended email and a single-use, expiring token.
- Existing users must sign in to their existing account rather than create duplicates.
- A user's organization membership is separate from their global account. Removing a membership removes access to that organization without deleting their account or historical actions.
- Require re-authentication and strong authorization for sensitive actions such as changing ownership or removing the last administrator.
- Evaluate mandatory multi-factor authentication for workspace administrators before production launch.

### Provider selection gate

Compare price and limits, email verification/recovery support, session revocation, JWT validation, account deletion/export, deployment-region requirements, operational lock-in and developer ergonomics. Verify current terms and free-tier limits before selection.

## 8. ADR-005 — Authorization and organization isolation

**Status:** Proposed recommendation

### Recommendation

Use **server-side role-based access control with explicit resource scope**, backed by database-level controls where practical. Role labels in the UI must never be the sole security boundary.

### Scope model

- Organization: workspace administration and roster-level operations.
- Program: parent program, shared departments and program-level views.
- Event: event configuration, tasks, registration and event reports.
- Department: work associated with the scoped department.
- Task: assignment-specific actions where the product needs finer control.

The exact set of supported scopes and permission grants must follow the role-and-permission matrix. A shared program department does not automatically expose every participant record for every child event.

### Required controls

- Validate the authenticated user and active organization membership on each protected request.
- Validate the permission and scope for the requested object, including nested resources.
- Reject cross-organization foreign-key combinations.
- Test authorization through direct API requests, not only UI behavior.
- Prevent users from changing their own role grants or invitation grants unless independently authorized to do so.
- Audit role changes, task reviews, attendance changes, workspace ownership changes and membership removal.
- Treat database row-level security as defense-in-depth if the chosen architecture supports it; do not assume it is enabled or correctly configured by default.

### Open implementation choice

If PostgreSQL row-level security is used, define non-owner application roles and explicit policies, test them, and ensure privileged credentials never reach the browser. Application-level authorization and tests remain mandatory.

## 9. ADR-006 — Evidence file storage

**Status:** Proposed recommendation; vendor not selected

### Recommendation

Use **private object storage** for uploaded evidence and supporting report files. Store metadata in PostgreSQL, including the organization/event scope, uploader, file size, media type, checksum if required, creation timestamp and retention state.

### Access model

1. The client asks the backend to begin an authorized upload.
2. The backend validates permission, file size and allowed file categories.
3. Storage access is private by default; use a short-lived signed upload/download URL or stream through the backend as appropriate.
4. The backend stores metadata and associates it with the task evidence submission or report.
5. Reviewer access is checked before a download or preview link is issued.

### Security requirements

- Allowlist expected extensions and verify actual file type/content where feasible; do not trust the browser-provided content type alone.
- Enforce maximum file sizes and safe generated storage keys.
- Reject unauthorized uploads and prevent path traversal/public-bucket exposure.
- Consider malware scanning or quarantine before making files available to reviewers, depending on supported file types and launch risk.
- Avoid leaking participant personal information in public URLs or logs.
- Establish deletion/retention rules and backup behavior before pilot data is stored.

### Options to compare

Provider-managed storage integrated with the chosen backend platform; or an independent S3-compatible object-storage service. Select only after validating access controls, signed URL support, cost, region and backup/export options.

## 10. ADR-007 — Native registration and external integrations

**Status:** Proposed architecture; specific connector sequence open

### Product requirement

CampusOps must support both:

1. Native registrations stored in CampusOps.
2. External registration sources, with Google Forms as the first candidate due to the current workflow described by the founder.

### Recommendation

Create a **registration-source adapter boundary**. Native registrations are first-class CampusOps records. Each external source has a connector that imports or synchronizes records into a normalized registration/participant model and records the external source ID. Do not make other parts of CampusOps depend directly on Google Forms response shapes.

### Google Forms validation gate

Google's published Forms API supports form and response retrieval, but access requires authorization and the documented scopes. Before committing to a full integration, verify access for a user-owned form, consent/scopes, API availability, quota behavior and how new responses are detected. The integration must not assume it can read any form simply because its URL is provided.

### Conflict and synchronization rules to define

- Identify an imported response by source and external response ID; repeated imports must not create duplicates.
- Preserve source timestamps and sync status.
- Show the last successful synchronization and actionable errors.
- Define whether imported fields are read-only in CampusOps or can be edited, and how conflicts are resolved.
- Use least-privilege OAuth scopes and store/revoke tokens securely.
- Support a clear manual CSV import/export fallback only if validated as acceptable; do not represent that fallback as live synchronization.

### Participant/check-in integrity

A team registration may group multiple individuals, but **each participant has an independent participant record and check-in outcome**. Check-in must reference the event and participant, and be idempotent under retries. A team-level registration must never automatically mark all members as present.

### Unresolved

The first external integration can be Google Forms, CSV import, or both, depending on technical feasibility and user value. Verify current Google API access/requirements before selecting the release scope.

## 11. ADR-008 — Email and notifications

**Status:** Proposed recommendation; provider not selected

### Recommendation

Use an email-provider adapter for transactional messages, including invitations, accepted/revoked invitation notices, task evidence review outcomes and password/account recovery messages (identity-provider messages may be sent by the chosen identity provider).

### Requirements

- Keep email delivery separate from the core task transaction where possible; persist the intended notification/event and handle retryable delivery failures.
- Do not send sensitive participant information or evidence attachments unnecessarily.
- Treat email as a notification channel, not as the authorization mechanism. The action still requires a valid authenticated session and server-side permission checks.
- Avoid duplicate notifications on retries using an idempotency key or equivalent approach where possible.
- Record delivery state needed for operations without logging secrets or full sensitive content.

Do not add a queueing service until observed delivery volume or reliability requirements justify one. A small database-backed notification/outbox pattern may be sufficient initially.

## 12. ADR-009 — Event-day connectivity and offline behavior

**Status:** Open decision; must be tested before pilot

### Risk

Poor venue connectivity can disrupt registration verification and check-in. True offline support introduces additional issues: devices may hold participant data locally, simultaneous devices may check in the same person, and synchronization may conflict after connectivity returns.

### Recommendation for validation

- Build explicit loading, timeout, retry and connectivity error states into the requirements.
- Test the registration desk under representative Wi-Fi/mobile-network conditions before the pilot.
- Do not promise offline check-in until a design is selected and tested.
- Compare online-only check-in, a limited preloaded offline roster, and a documented manual fallback.
- If offline mode is selected, specify device protection, data minimization, encryption at rest, expiration/purge, conflict resolution and reconciliation before implementation.

## 13. ADR-010 — Hosting, deployment and environments

**Status:** Deferred

Do not choose a permanent hosting vendor yet. First identify the intended pilot conditions, budget, expected data location, outbound email/storage requirements, and provider account constraints.

When implementation is authorized, use separate development and production environments, environment-managed secrets, database migrations, TLS, automated tests, backups and a tested restoration process. Do not use real participant data in development. Never commit API keys, service-role keys, database passwords, OAuth refresh tokens or invitation secrets to source control.

A low-cost managed deployment is a reasonable initial direction, but current prices, regional availability and limits must be checked at the time of selection.

## 14. Cross-cutting security and reliability requirements

Before a real pilot, the architecture and implementation must demonstrate:

- Authentication and role/scope authorization tests, including cross-organization access attempts.
- Transactional and idempotent task review/check-in operations.
- Private file access and file-upload validation.
- Secure invitation token generation, storage, expiry, revocation and single-use acceptance.
- Audit history for important administrative and operational actions.
- Safe secret management and redacted logs.
- Database backups and a tested restoration procedure.
- Error reporting and actionable failure states for external integrations.
- Defined retention and deletion rules for organization and participant data.
- A documented manual fallback for event-day failures until any offline workflow is implemented.

Do not describe CampusOps as production-ready until these controls have been implemented and verified.

## 15. Principal architectural risks

| Risk | Consequence | Proposed mitigation / decision gate |
|---|---|---|
| Overly broad scope | Long delivery cycle and hard-to-use interface | Use a modular monolith and staged release plan; maintain full vision but validate core workflows first. |
| Incorrect tenant isolation | One club could access another club's data | Scope every operation; enforce database relationships; automated negative authorization tests. |
| Permissions become too complex | Unauthorized approvals or confusing role setup | Start with a small permission catalog and explicit scope; test standalone and multi-event cases. |
| Google Forms access or sync is limited | Registration data is stale or unavailable | Technical spike with the actual permission model; connector status, idempotency and validated fallback. |
| Duplicate or conflicting registration records | Wrong check-in/attendance counts | External source IDs, unique constraints, explicit conflict rules and reconciliation report. |
| Evidence file exposure | Leaked internal documents or participant data | Private object storage, scoped authorization, short-lived access, validation and audit. |
| Unreliable venue internet | Registration queue or interrupted check-in | Connectivity tests, clear failure states, manual fallback, then explicit offline decision. |
| Identity-provider lock-in or pricing changes | Unexpected migration cost | Isolate identity provider behind an adapter where practical; verify export and migration paths. |
| Leadership transfer leaves no admin | Workspace becomes inaccessible | Multiple authorized administrators or controlled recovery policy; test transfer before production. |

## 16. Decision register summary

| Decision | Current proposal | Status |
|---|---|---|
| Application architecture | Modular monolith | Proposed |
| Frontend | React + TypeScript + Vite | Proposed |
| Backend | FastAPI + Pydantic | Proposed |
| Primary database | PostgreSQL | Proposed |
| ORM/migrations | SQLAlchemy + Alembic | Proposed; validate in technical spike |
| Authentication | Managed provider; Supabase Auth is one candidate | Provider open |
| Authorization | Server-side RBAC with explicit resource scopes; database defense-in-depth | Required direction; implementation details open |
| Evidence storage | Private object storage | Vendor open |
| Registration | Native records + adapter for external sources | Required direction; first connector scope open |
| Email | Transactional email adapter | Vendor open |
| Offline check-in | No promise until validated | Open; pilot gate |
| Hosting/region | Defer until budget and data needs are known | Open |

## 17. Architecture approval gates

Do not begin implementation until the following are satisfied:

1. The requirements specification and role/permission matrix agree on who can perform each sensitive action.
2. The logical data model has a reviewed mapping to actual foreign keys, uniqueness rules and tenant boundaries.
3. The authentication provider and account recovery/administrator-transfer policies are selected.
4. The initial registration source and its authorization/synchronization path are proven in a small technical validation exercise.
5. Evidence storage, private access and retention rules are decided.
6. The initial event-day connectivity assumption and manual fallback are documented.
7. Hosting cost, environment separation, backups and restoration ownership are understood.

The existence of this ADR is not approval to install packages or create the application. Each proposed option needs review, and any approved decision should be reflected in the decision log before implementation begins.

## 18. References

Official references reviewed to inform this proposal:

- Google Forms API — https://developers.google.com/workspace/forms/api/reference/rest
- Google Forms API guide: retrieve forms and responses — https://developers.google.com/workspace/forms/api/guides/retrieve-forms-responses
- Supabase Row Level Security guidance — https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase Auth overview — https://supabase.github.io/auth/
- FastAPI security reference — https://fastapi.tiangolo.com/reference/security/
- OWASP File Upload Cheat Sheet — https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

These references support the technical considerations, not an endorsement or final selection of any vendor. Current availability, API restrictions, pricing and contractual terms must be rechecked when a choice is made.
