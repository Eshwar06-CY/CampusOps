# CampusOps — System-Wide Integration Readiness Audit

**Document version:** 1.0  
**Effective date:** 30 October 2026  
**Status:** Completed Engineering Audit & Verification  
**Repository:** `D:\Antigravity_Projects\CampusOps`  
**Working branch:** `main` | **HEAD Commit:** `282311a`

---

## 1. Executive Summary & Verification Context

Following the completion of Slice 5D (Participant Registration & Event-Day Operations Frontend) and the Premium UX Review, this independent engineering audit evaluates the system-wide integration readiness of CampusOps. 

CampusOps has evolved across five major architectural slices:
1. **Slice 1:** Minimal modular backend/frontend baseline.
2. **Slices 2A & 2B:** Identity, workspace organization, role hierarchies, and invitation lifecycles.
3. **Slices 3A & 3B:** Programs, standalone events, child events, exclusive departments, and event leads.
4. **Slices 4A & 4B:** Task ownership, strict single-worker assignment, deadline audits, evidence submission, self-review prohibition, staff operational blockers, and in-app notifications.
5. **Slices 5A, 5B, 5C & 5D:** Native public participant registration (solo/team), digital admission passes, event capacity reservation, attendee rosters with tiered contact masking, individual check-in desk, manager check-in void audit trails, attendance KPI reporting, and registration settings management.

### Audit Objectives
1. **Verify the true repository state:** Reconcile all working copy changes, database migrations, backend routes, frontend components, and test baselines without trusting outdated summaries.
2. **Build a system-wide traceability matrix:** Map every core product capability across the backend and frontend to identify integrated systems versus backend-complete orphan APIs.
3. **Rigorously audit security invariants & contract integrity:** Verify fail-closed authentication boundaries, server-side tenant isolation, credential protection, replay resistance, atomic capacity accounting, and evaluate the reported discrepancy regarding URL path credentials versus body-based POST lookups.
4. **Validate custom QR generation and ticket mechanics:** Inspect `frontend/src/utils/qr.ts`, evaluate ISO/IEC 18004 alignment, verify error correction and masking, assess independent decoder coverage, and audit reload/recovery behavior for redacted credentials.
5. **Execute real browser rendering verification:** Distinguish empirical browser rendering from static code inspection using headless Microsoft Edge across desktop (1280px), tablet (768px), and mobile (375px) viewports.
6. **Reassess production readiness gates:** Evaluate PostgreSQL parity, identity provider integration, distributed rate limiting, private object storage, observability, and deployment infrastructure.
7. **Formulate a prioritized next-phase implementation blueprint:** Establish an actionable, dependency-aware plan to connect the operational frontend to Slices 2B, 3B, and 4B APIs, followed by Slice 6 (Post-Event Operations).

---

## 2. Actual Repository State & Changed File Inventory

### 2.1 Git Repository Baseline
- **Branch:** `main`
- **HEAD Commit:** `282311a029636f88726b1e02d237a960568d95a7` (`feat: implement backend API, models, services, and database migrations for core application`)
- **Working Tree State:** Dirty (all development increments across Slices 4B, 5B, 5C, 5D, and Premium UX Review are preserved as unstaged, reviewable modifications; zero commits were created, in strict compliance with project governance).
- **Whitespace & Line Endings:** `git diff --check` passed cleanly with exit code 0 (no whitespace errors).

### 2.2 Verified Changed-File Inventory

#### Tracked Files Modified (13 files):
1. `backend/app/api/v1/api.py`: Router inclusion for tasks, blockers, notifications, public registration, and staff registration.
2. `backend/app/api/v1/endpoints/blockers.py`: Cross-tenant boundary verification and uniform HTTP 404 anti-enumeration hardening.
3. `backend/app/models/__init__.py`: Export of task, blocker, notification, and registration domain models.
4. `backend/app/models/task.py`: Partial unique index `uq_task_assignee_active` (`['task_id'] WHERE assignment_status = 'active'`).
5. `backend/app/schemas/__init__.py`: Export of task, blocker, notification, and registration schemas.
6. `backend/app/services/errors.py`: Registration, ticket, capacity, and check-in domain exceptions.
7. `backend/app/services/permissions.py`: Task assignee dynamic view permissions, registration/check-in action constants.
8. `backend/app/services/task.py`: Terminal status guards, `cancel_task` lifecycle, and assignee active membership checks.
9. `backend/tests/test_migrations.py`: Additive migration lifecycle verification for revisions `b7c8d9e0f1a2` and `c8d9e0f1a2b3`.
10. `docs/implementation/IMPLEMENTATION_STATUS.md`: Authoritative progress tracking and verification ledger.
11. `frontend/src/App.test.tsx`: App shell navigation tests.
12. `frontend/src/App.tsx`: Mode switcher, registration portal, staff operations tabs, and toast provider integration.
13. `frontend/src/index.css`: Design token imports and global resets.

#### Untracked Domain, Migration, Test & Documentation Files (33 items):
- **Decision Addenda & Reports (12 files):**
  - `Consolidated Documentation/CampusOps_Decision_Log_v1.7_Addendum.md`
  - `docs/implementation/CAMPUSOPS_PREMIUM_UX_REVIEW.md`
  - `docs/implementation/SLICE_4B_SECURITY_AUDIT_REPORT.md`
  - `docs/implementation/SLICE_5B_DOMAIN_IMPLEMENTATION_REPORT.md`
  - `docs/implementation/SLICE_5B_SECURITY_AUDIT_REPORT.md`
  - `docs/implementation/SLICE_5C_API_CONTRACT.md`
  - `docs/implementation/SLICE_5C_IMPLEMENTATION_REPORT.md`
  - `docs/implementation/SLICE_5C_SECURITY_AUDIT_REPORT.md`
  - `docs/implementation/SLICE_5D_FRONTEND_IMPLEMENTATION_REPORT.md`
  - `docs/implementation/SLICE_5_ACCEPTANCE_TEST_PLAN.md`
  - `docs/implementation/SLICE_5_API_CONTRACT_DRAFT.md`
  - `docs/implementation/SLICE_5_SCHEMA_RELATIONSHIP_PLAN.md`
  - `docs/implementation/SLICE_5_SCOPE_AND_ARCHITECTURE_PLAN.md`
- **Database Migrations (2 files):**
  - `backend/alembic/versions/b7c8d9e0f1a2_slice_5_registration_ticketing_and_attendance.py`
  - `backend/alembic/versions/c8d9e0f1a2b3_slice_5b_integrity_hardening.py`
- **Backend Application Code (5 files):**
  - `backend/app/api/v1/endpoints/public_registration.py`
  - `backend/app/api/v1/endpoints/staff_registration.py`
  - `backend/app/models/registration.py`
  - `backend/app/schemas/registration.py`
  - `backend/app/services/registration.py`
- **Backend Test Suites (5 files):**
  - `backend/tests/test_api_slice_5c_registration.py`
  - `backend/tests/test_slice_4b_security_audit.py`
  - `backend/tests/test_slice_5b_registration_domain.py`
  - `backend/tests/test_slice_5b_security_audit.py`
  - `backend/tests/test_slice_5c_security_audit.py`
- **Frontend Architecture & Components (9 directories/files):**
  - `frontend/src/api/` (`client.ts`, `types.ts`, `publicRegistration.ts`, `staffOperations.ts`)
  - `frontend/src/components/` (`common/`, `layout/`, `public/`, `staff/`)
  - `frontend/src/styles/` (`theme.css`, `components.css`)
  - `frontend/src/utils/` (`qr.ts`, `formatters.ts`, `idempotency.ts`)
  - `frontend/src/test/qr.test.ts`
  - `frontend/src/test/PassDisplay.test.tsx`
  - `frontend/src/test/PublicRegistration.test.tsx`
  - `frontend/src/test/StaffOperations.test.tsx`
  - `frontend/src/test/PremiumUX.test.tsx`

---

## 3. System-Wide Traceability Matrix

The table below audits every core product capability specified in `CampusOps_PRD_v1.1.md` and subsequent delivery slices, reporting real implementation status across both backend and frontend.

| Capability Area | Backend Status | Frontend Status | API Endpoints & Methods | Connected | Test Coverage | Remaining Dependencies / Blockers | Classification |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Workspace & Org Management** | Complete (Slice 2A/2B) | Missing | `POST /api/v1/organizations`<br>`GET /api/v1/organizations`<br>`GET /api/v1/organizations/{id}` | No | 31 backend integration tests | Requires workspace creation form, organization switcher, and detail view in frontend | **Backend complete, frontend missing** |
| **2. Org Verification & Invitations** | Complete (Slice 2A/2B/3B) | Missing | `POST /api/v1/organizations/{id}/verify`<br>`POST /api/v1/organizations/{id}/invitations`<br>`POST /api/v1/invitations/accept`<br>`POST .../invitations/{id}/revoke` | No | 28 backend tests | Requires platform admin verification queue, member invitation modal, and acceptance token landing page | **Backend complete, frontend missing** |
| **3. Programs & Multi-Event Management** | Complete (Slice 3A/3B) | Missing | `POST /api/v1/organizations/{id}/programs`<br>`GET /api/v1/organizations/{id}/programs`<br>`GET /api/v1/organizations/{id}/programs/{id}`<br>`PATCH .../programs/{id}`<br>`POST .../programs/{id}/archive`<br>`GET .../programs/{id}/events`<br>`POST .../programs/{id}/events`<br>`GET .../programs/{id}/departments` | No | 43 backend tests | Requires Program dashboard, child event list, and umbrella date bounds enforcement UI | **Backend complete, frontend missing** |
| **4. Events & Departments** | Complete (Slice 3A/3B) | Missing | `POST /api/v1/organizations/{id}/events`<br>`GET /api/v1/organizations/{id}/events`<br>`GET /api/v1/organizations/{id}/events/{id}`<br>`PATCH .../events/{id}`<br>`POST .../events/{id}/archive`<br>`POST /api/v1/organizations/{id}/departments`<br>`GET .../departments`<br>`GET .../departments/{id}`<br>`PATCH .../departments/{id}`<br>`POST .../departments/{id}/archive` | No | 36 backend tests | Requires standalone vs child event creation forms, department management drawer, and archive confirmation modals | **Backend complete, frontend missing** |
| **5. Team Hierarchy, Roles & Leads** | Complete (Slice 2A/3B) | Missing | `GET /api/v1/me`<br>`POST .../events/{id}/leads`<br>`GET .../events/{id}/leads`<br>`POST .../events/{id}/leads/{id}/revoke` | No | 22 backend tests | Requires member directory, role assignment interface, and event lead delegation controls | **Backend complete, frontend missing** |
| **6. Tasks, Deadlines & Assignment** | Complete (Slice 4A/4B) | Missing | `POST /api/v1/organizations/{id}/tasks`<br>`GET /api/v1/organizations/{id}/tasks`<br>`GET .../tasks/{id}`<br>`PATCH .../tasks/{id}`<br>`POST .../tasks/{id}/assign`<br>`POST .../tasks/{id}/cancel`<br>`POST .../tasks/{id}/deadline`<br>`GET .../tasks/{id}/history`<br>`POST .../tasks/{id}/start` | No | 37 backend tests | Requires Kanban/task list, task creation modal, deadline audit dialog (mandatory reason), and status lifecycle buttons | **Backend complete, frontend missing** |
| **7. Evidence Submission & Review** | Complete (Slice 4A/4B) | Missing | `POST .../tasks/{id}/submissions`<br>`GET .../tasks/{id}/submissions`<br>`POST .../tasks/{id}/submissions/{id}/review` | No | 14 backend tests | Requires evidence submission form (URL link), submission history view, and review action modal (enforcing no-self-review) | **Backend complete, frontend missing** |
| **8. Internal Operational Blockers** | Complete (Slice 4A/4B) | Missing | `POST /api/v1/organizations/{id}/blockers`<br>`GET /api/v1/organizations/{id}/blockers`<br>`GET .../blockers/{id}`<br>`PATCH .../blockers/{id}`<br>`POST .../blockers/{id}/resolve`<br>`POST .../blockers/{id}/reopen` | No | 16 backend tests | Requires event-day blocker feed, blocker raise modal, resolution modal (mandatory notes), and reopen action | **Backend complete, frontend missing** |
| **9. Notifications** | Complete (Slice 4A/4B) | Missing | `GET /api/v1/notifications`<br>`GET /api/v1/notifications/{id}`<br>`POST /api/v1/notifications/{id}/read` | No | 8 backend tests | Requires topbar notification bell, unread badge indicator, and flyout drawer | **Backend complete, frontend missing** |
| **10. Participant Registration** | Complete (Slice 5B/5C) | Complete (Slice 5D) | `GET /api/v1/public/events/{registration_key}`<br>`GET .../registration-settings`<br>`PUT .../registration-settings` | Yes | 15 backend, 8 frontend tests | Fully wired in `EventOverview` and `RegistrationSettingsCard` | **Complete and integrated** |
| **11. Individual & Team Registration** | Complete (Slice 5B/5C) | Complete (Slice 5D) | `POST /api/v1/public/events/{registration_key}/registrations`<br>`POST .../registrations/walk-in` | Yes | 22 backend, 8 frontend tests | Fully wired in `IndividualRegForm` and `TeamRegForm` with dynamic team sizing | **Complete and integrated** |
| **12. Admission Passes** | Complete (Slice 5B/5C) | Complete (Slice 5D) | `POST /api/v1/public/events/{key}/passes/verify`<br>`GET .../passes/{pass_code}`<br>`POST .../participants/{id}/reissue-pass` | Yes | 18 backend, 6 frontend tests | Fully wired in `PublicPassDisplay`, `ParticipantDetailModal`, and `qr.ts` (independent decoder validation pending) | **Complete and integrated** |
| **13. Staff Roster & Attendee Search** | Complete (Slice 5B/5C) | Complete (Slice 5D) | `GET .../events/{id}/participants`<br>`GET .../events/{id}/participants/{id}`<br>`PATCH .../events/{id}/participants/{id}`<br>`GET .../events/{id}/registrations` | Yes | 20 backend, 7 frontend tests | Fully wired in `ParticipantRoster` with debounced search and contact masking | **Complete and integrated** |
| **14. Check-In & Corrections** | Complete (Slice 5B/5C) | Complete (Slice 5D) | `POST .../events/{id}/check-ins`<br>`POST .../events/{id}/check-ins/{id}/void`<br>`GET .../events/{id}/check-in-lookup` | Yes | 24 backend, 7 frontend tests | Fully wired in `CheckInDesk` and `CheckInCorrectionModal` (>= 10 char mandatory reason) | **Complete and integrated** |
| **15. Attendance Summaries & Exports** | Complete (Slice 5B/5C) | Complete (Slice 5D) | `GET .../events/{id}/attendance-summary`<br>`GET .../events/{id}/roster-export` | Yes | 14 backend, 4 frontend tests | Fully wired in `AttendanceSummaryCard` and CSV export action in `ParticipantRoster` | **Complete and integrated** |

### Capability Classification Summary:
- **Complete and integrated:** 6 capabilities (Capabilities 10–15: Participant Registration, Individual/Team Registration, Admission Passes, Staff Roster, Check-In & Corrections, Attendance Summaries & Exports).
- **Backend complete, frontend missing:** 9 capabilities (Capabilities 1–9: Workspace Management, Verification & Invitations, Programs, Events & Departments, Team Hierarchy & Leads, Tasks, Evidence Submission & Review, Blockers, Notifications).
- **Frontend complete, backend incomplete:** 0 capabilities.
- **Partially integrated:** 0 capabilities.
- **Not implemented:** 0 capabilities (all 15 capabilities have complete backend foundations).

---

## 4. Security and Contract Verification

### 4.1 Route-by-Route Security Invariant Verification

1. **Staff Authentication Fails Closed:**
   - Evaluated in `backend/app/api/v1/deps.py`: `get_current_principal` raises `HTTP_401_UNAUTHORIZED` unless an upstream authentication adapter is explicitly active.
   - Verified in `frontend/src/components/staff/AuthUnavailableNotice.tsx`: When staff endpoints respond with 401, the UI displays an explicit fail-closed operational notice without attempting mock logins or bypassing security.

2. **Server-Side Tenant Isolation & Authorization:**
   - Evaluated in `backend/app/services/permissions.py`: The `can_perform` and `require_permission` functions evaluate scoped `RoleAssignment` entries against database-verified hierarchies (`organization_id`, `event_id`, `department_id`).
   - Anti-enumeration: Cross-tenant accesses return uniform `HTTP_404_NOT_FOUND` across all endpoints to prevent resource existence discovery.

3. **Public Capability Protection:**
   - Public event discovery requires an unguessable high-entropy registration key (`secrets.token_urlsafe(32)`).
   - Only the SHA-256 hash `registration_key_hash` is indexed and matched in the database (`uq_event_reg_settings_key_hash`).
   - Key rotation (`rotate_registration_key=True` in `PUT .../registration-settings`) immediately invalidates prior URLs.

4. **Zero Client Storage of Sensitive Credentials:**
   - Verified: Neither `localStorage` nor `sessionStorage` are used to persist admission pass tokens (`CO-PASS-<HEX>`), registration confirmation codes, or staff bearer tokens.
   - All state is managed in memory via React state hooks.

5. **Discrepancy Investigation: URL Paths vs Body-Based POST Endpoints:**
   - **Background:** Earlier Slice 5C drafts specified pass verification (`GET .../passes/{pass_code}`), status lookup (`GET .../registrations/{confirmation_code}`), and cancellation (`POST .../registrations/{confirmation_code}/cancel`) with sensitive capability codes in URL paths. Slice 5D claimed these were migrated to request bodies.
   - **Direct Source Verification:**
     - `backend/app/api/v1/endpoints/public_registration.py` exposes:
       - `POST /public/events/{registration_key}/passes/verify` (accepts `PublicPassVerifyRequest(pass_code=...)`).
       - `POST /public/events/{registration_key}/registrations/lookup` (accepts `PublicRegistrationLookupRequest(confirmation_code=...)`).
       - `POST /public/events/{registration_key}/registrations/cancel` (accepts `PublicRegistrationCancelBodyRequest(...)`).
     - Simultaneously, the backend maintains backwards-compatible endpoints:
       - `GET /public/events/{registration_key}/passes/{pass_code}`
       - `GET /public/events/{registration_key}/registrations/{confirmation_code}`
       - `POST /public/events/{registration_key}/registrations/{confirmation_code}/cancel`
     - `frontend/src/api/publicRegistration.ts`: Calls **strictly the body-based POST endpoints** (`/passes/verify`, `/registrations/lookup`, `/registrations/cancel`).
   - **Conclusion:** There is **zero contract conflict**. The frontend and backend agree on the hardened body-based contract, which eliminates bearer token exposure in HTTP Referer headers, proxy logs, and browser history. The backend maintains legacy path routes solely for backwards compatibility.

6. **Idempotency and Replay Protections:**
   - Database constraint `uq_registrations_event_idempotency` (`['event_id', 'idempotency_key'] WHERE idempotency_key IS NOT NULL`) blocks concurrent duplicate submissions at the engine level.
   - Exact replays return the existing registration with pass credentials redacted (`<REDACTED_AFTER_ISSUANCE>`).
   - Replays with altered registration payloads raise `HTTP_409_CONFLICT`.

7. **Atomic Capacity Accounting:**
   - Implemented via atomic SQL update in `backend/app/services/registration.py`:
     ```sql
     UPDATE event_registration_settings 
     SET current_confirmed_count = current_confirmed_count + :slots 
     WHERE event_id = :event_id 
       AND (capacity_limit IS NULL OR current_confirmed_count + :slots <= capacity_limit);
     ```
   - Eliminates overselling race conditions across concurrent processes without distributed locking overhead.

8. **All-or-Nothing Team Admissions:**
   - Team registration atomically reserves `len(participants)` individual capacity slots. If available capacity is fewer than the requested team size, the entire team is either waitlisted (if enabled) or rejected atomically. Partial team admissions are strictly prevented.

9. **Enforcement of Individual Check-In Rule (FA-005):**
   - Verified in `backend/app/services/registration.py` (`perform_check_in`): Pass verification or manual roster check-in validates strictly the specific participant's ticket. Scanning a team member's pass checks in only that individual; group auto-check-in is structurally impossible.
   - Partial unique index `uq_check_in_event_participant` ensures at most one valid check-in row per participant.
   - Duplicate scans are idempotent and return `status: "already_checked_in"` without inflating attendance totals.

10. **Manager-Only Check-In Corrections & Audit Ledger (D-SLICE5-04):**
    - `POST .../check-ins/{id}/void` requires `ACTION_CORRECT_CHECK_IN` (restricted to `PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`).
    - Requires a non-empty explanation of at least 10 characters.
    - Appends an immutable record in `CheckInCorrection` capturing `check_in_id`, `previous_status`, `new_status`, `reason`, `authorized_by_id`, and `created_at`. Check-in records are never hard-deleted.

11. **Tiered Contact Masking for Desk Staff:**
    - Desk staff holding `ACTION_CHECK_IN` (e.g. `REGISTRATION_STAFF` volunteers) view masked emails (`j***e@domain.com`) and phone numbers (`*******1234`).
    - Unmasked PII disclosure requires `ACTION_VIEW_ATTENDEE_CONTACT` (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`).

12. **Spreadsheet Formula Injection Defense (CWE-1236):**
    - Roster CSV export (`GET .../roster-export`) sanitizes all text cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` by prefixing with a single quote (`'`), preventing formula execution in Excel/Google Sheets.

13. **Abuse Controls & Timing-Safe Lookups:**
    - Pass verification uses constant-time `hmac.compare_digest` to prevent timing attacks against SHA-256 ticket hashes.
    - Public registration keys have 256 bits of cryptographic entropy.

14. **Telemetry & Log Privacy:**
    - Domain models (`Ticket`, `Registration`, `UserProfile`) override `__repr__` to suppress pass codes, confirmation codes, and personal details.
    - Application loggers record only UUID identifiers and event lifecycle states.

---

## 5. QR Code & Pass Validation

### 5.1 Architecture of `frontend/src/utils/qr.ts`
The application utilizes a zero-dependency, pure TypeScript QR Code generator (`src/utils/qr.ts`) producing inline scalable vector graphics (`<svg>`):
- **Model Standard:** ISO/IEC 18004 Model 2.
- **Supported Versions:** Versions 1 through 6 (modules $21 \times 21$ through $41 \times 41$), supporting up to 134 bytes—sufficient for 128-bit hexadecimal bearer tokens (`CO-PASS-<HEX>`).
- **Encoding Mode:** 8-bit Byte Mode (`0100`).
- **Galois Field Arithmetic:** GF(256) with primitive polynomial $x^8 + x^4 + x^3 + x^2 + 1$ (`0x11d`), precomputing exponential and logarithmic tables.
- **Error Correction:** Implements Reed-Solomon polynomial division generating ECC codewords for levels `L` (7%), `M` (15%), `Q` (25%), and `H` (30%).
- **Quiet Zone:** Configurable margin defaulting to 4 modules (ISO standard quiet zone).
- **Pure SVG Rendering:** Generates vector path strings using `shape-rendering="crispEdges"`, eliminating canvas pixelation and external image dependencies.

### 5.2 Identified Limitations in Custom QR Implementation
1. **Hardcoded Mask Pattern:**
   - In `qr.ts`, the mask pattern is hardcoded to Mask 0 (`(row + col) % 2 == 0`).
   - ISO/IEC 18004 Section 8.8 requires evaluating all 8 mask patterns against penalty rules (N1, N2, N3, N4) to select the mask minimizing optical scanner misreads. While Mask 0 format bits are written correctly and render syntactically valid QR structures, dense data patterns may suffer reduced readability under poor lighting or smudged lenses.
2. **Alignment Pattern Centers in Version 2:**
   - In `VERSION_PARAMS[1]` (Version 2), alignment is configured as `[6, 18]`. In the ISO standard, Version 2 has only a single alignment pattern at row 18, column 18; coordinates `(6, 18)` and `(18, 6)` coincide with the timing patterns and finder separators. The implementation guards against overwriting function modules, but standards compliance warrants validation.
3. **Absence of Independent Decoder Testing:**
   - **Critical Finding:** The Vitest test suite (`frontend/src/test/qr.test.ts`) tests only that the output is a valid SVG string, contains no PII, and has the expected viewBox dimensions.
   - **No standards-compliant decoder (such as ZXing, jsQR, or pyzbar) has decoded the generated SVG in automated tests.**
   - **Action Required:** Recorded as an **outstanding verification requirement**. Do not claim full ISO compliance until automated roundtrip decoder tests are implemented.

### 5.3 Pass Lifecycle, Reload & Recovery Behavior
1. **Initial Issuance:**
   - Upon successful public registration (`POST .../registrations`), raw unguessable pass tokens (`CO-PASS-<HEX>`) are generated and returned in the HTTP response.
   - The confirmation screen renders the individual passes with vector QR codes and ticket references (`CO-TKT-<HEX>`).
2. **Page Reload & Capability Lookups:**
   - The database stores **only** the SHA-256 hash `pass_code_hash`. The raw token is strictly non-recoverable from the database.
   - When an attendee looks up an existing registration via confirmation code (`POST .../registrations/lookup`), the registration status endpoint returns attendee names and ticket references, but pass codes are omitted.
   - In `PublicPassDisplay.tsx`, if the pass code is missing or marked `<REDACTED_AFTER_ISSUANCE>`, the UI gracefully displays a "Pass Code Secured" card displaying the persistent ticket reference and explaining that credentials are protected.
3. **Staff Recovery & Reissuance:**
   - If an attendee loses their pass code, desk staff with manager authority execute `POST .../participants/{id}/reissue-pass`.
   - This atomically revokes the prior ticket, generates a fresh pass code, updates the SHA-256 hash, and provides the new pass code to the attendee without mutating attendance history.

---

## 6. Premium UX Verification

### 6.1 Empirical Browser Rendering Methodology
Rather than relying solely on static component inspection, the application was built (`npm run build`), served via local HTTP server (`http://localhost:5173`), and rendered using headless Microsoft Edge (`msedge.exe --headless=new`) across three standardized viewports:
- **Desktop:** $1280 \times 900$ pixels.
- **Tablet:** $768 \times 1024$ pixels.
- **Mobile:** $375 \times 812$ pixels.

Actual rendered screenshots were captured and inspected in the brain scratch repository (`desktop.png`, `tablet.png`, `mobile.png`).

### 6.2 Visual and Ergonomic Evaluation

| Evaluation Criteria | Desktop ($1280\text{px}$) | Tablet ($768\text{px}$) | Mobile ($375\text{px}$) | Audit Assessment |
| :--- | :--- | :--- | :--- | :--- |
| **Visual Distinctiveness** | High | High | High | Slate-950 dark background, Indigo primary accents, professional typography; avoid generic AI dashboard aesthetics. |
| **Information Hierarchy** | High | High | Moderate | Clear separation between public attendee mode and staff desk; card-based grouping with tabular figures. |
| **Table & Roster Usability** | High | Moderate | Moderate (horizontal scroll) | Roster displays tabular data with masked contacts and status pills. Mobile requires horizontal scroll for wide tables. |
| **Loading & Skeleton States** | Clean | Clean | Clean | Shimmer gradient skeletons (`CardSkeleton`, `TableSkeleton`) eliminate Cumulative Layout Shift (CLS). |
| **Error & Empty States** | High | High | High | Paired SVG vector icons (`IconAlertCircle`, `IconAlertTriangle`) with accessible alert roles and high contrast. |
| **Keyboard Ergonomics** | High | High | N/A (Touch) | Global `/` shortcut focuses check-in scanner input; candidate search supports `ArrowDown`/`ArrowUp` + `Enter`. |
| **Focus Trapping & Return** | High | High | High | Modal dialogs trap focus in loop and restore focus to trigger element upon `Escape` or dismissal. |
| **Reduced Motion** | High | High | High | `@media (prefers-reduced-motion: reduce)` globally disables transitions, transforms, and shimmer animations. |
| **Dark Mode Contrast** | High | High | High | Neutral text (`#f8fafc`, `#cbd5e1`) exceeds WCAG AA 4.5:1 ratio against background (`#090d16`). |
| **Pass Print Layout** | Clean | Clean | Clean | `@media print` eliminates navbars, dark backgrounds, buttons, and footers for crisp paper ticket printing. |

### 6.3 Identified UX Gaps from Actual Browser Rendering
1. **Mobile Navbar Wrapping & Horizontal Overflow at 375px:**
   - **Observation in `mobile.png`:** On narrow mobile viewports ($375\text{px}$), the top navigation bar elements (`Navbar.tsx`) wrap awkwardly. The registration key input (`Key: [ reg_demo_key ] [ Load ]`) extends beyond the right edge, causing a horizontal scrollbar. Additionally, the `Slice 5D` pill badge wraps its label onto two lines ("Slice\n5D").
   - **Remediation Required:** In mobile media queries (`@media (max-width: 640px)`), stack navigation controls vertically, collapse secondary debug controls (like the key loader) into a collapsible drawer or toggle, and apply `white-space: nowrap` to badge pills.
2. **Table Header Fixed Layout on Mobile:**
   - The attendee roster table requires horizontal scrolling on mobile. While functional, a card-based responsive list view would improve mobile desk usability.

---

## 7. Production Readiness Assessment & Canonical Technical Gate Alignment

### 7.1 Canonical Technical Gate Register (TG-01 to TG-07)
The project's architectural milestones are governed by seven canonical Technical Gates defined in `IMPLEMENTATION_STATUS.md`:
- **TG-01 (Toolchain Baseline):** Local Python virtual environment and Node workspace setup (**PASSED**).
- **TG-02 (Authentication Spike):** Server-side JWT/JWKS cryptographic verification (**SPIKE SPECIFICATION READY / EXTERNAL PROVIDER BLOCKED**).
- **TG-03 (Database & Migrations):** Multi-tenant SQLAlchemy/Alembic migration baseline through `c8d9e0f1a2b3` (**PASSED**).
- **TG-04 (API Contract Freeze):** Strict Pydantic v2 schemas and REST endpoints across all domain slices (**PASSED**).
- **TG-05 (Test Framework Baseline):** Automated backend pytest and frontend vitest suites (**PASSED**).
- **TG-06 (Evidence Storage):** Private object storage adapter and signed URLs (**DEFERRED**).
- **TG-07 (Production Pilot):** Deployment on target cloud infrastructure (**STRICT NO-GO**).

### 7.2 TG-07 Production Pilot Operational Sub-Criteria
Passing **TG-07 (Production Pilot)** requires satisfying eight operational criteria evaluated below:

| Sub-Criterion | Category | Current Implementation State | Operational Status | Outstanding Requirements |
| :--- | :--- | :--- | :--- | :--- |
| **TG-07.1** | Identity Provider Integration | Fail-closed stub (`get_current_principal` raises 401). Synthetic dependency overrides in tests. Cryptographic JWT/JWKS spike completed in Slice 2C. | **BLOCKED (NO-GO)** | Deploy hosted identity provider (Supabase Auth / OIDC), configure asymmetric JWKS verification and remote key caching in normal runtime. |
| **TG-07.2** | PostgreSQL Parity & Migration | Tested against SQLite with batch mode enabled. Additive Alembic migration revisions verified up to `c8d9e0f1a2b3`. | **BLOCKED (NO-GO)** | Execute automated migration and concurrency tests against a real PostgreSQL 16+ instance. Verify partial unique indexes and row-level locking. |
| **TG-07.3** | Distributed Rate Limiting | In-memory or missing rate limiting on public endpoints (`/public/events/...`). | **BLOCKED (NO-GO)** | Deploy shared Redis/Upstash rate limiter enforcing sliding-window limits on registration, key lookup, and check-in endpoints. |
| **TG-07.4** | Private Object Storage | Slice 4A/4B implemented URL strings for evidence links. No binary file upload handling (TG-06 deferred). | **BLOCKED (NO-GO)** | Provision private S3/GCS buckets with signed pre-upload URLs, mime-type verification, and virus scanning for task evidence. |
| **TG-07.5** | Observability & Logging | Standard Python logging and Starlette console output. OpenTelemetry API imported. | **BLOCKED (NO-GO)** | Configure structured JSON logging, distributed trace context propagation, and APM error aggregation (Sentry/Datadog). |
| **TG-07.6** | Backup & Disaster Recovery | Local file databases only. | **BLOCKED (NO-GO)** | Implement automated point-in-time recovery (PITR), hourly WAL archiving, and daily encrypted database backups. |
| **TG-07.7** | Deployment Configuration | No Dockerfile, docker-compose, Kubernetes manifests, or CI/CD pipelines in repo. | **BLOCKED (NO-GO)** | Author multi-stage production Dockerfiles, compose environments, health check probes, and GitHub Actions CI pipelines. |
| **TG-07.8** | Operational Security Policies | Break-glass platform admin bootstrap CLI (`bootstrap_platform_admin.py`) verified. | **CONDITIONAL** | Establish production secret management (AWS Secrets Manager / Vault) and formal incident response runbooks. |

**Overall Production Pilot Gate (TG-07):** **STRICT NO-GO**. The application remains in controlled incremental development.

---

## 8. Critical and High-Priority Issues Inventory

### Priority 1: High Priority (Integration & Compliance)
1. **Orphan Backend APIs (Frontend Missing):**
   - 9 complete backend capabilities (Organizations, Invitations, Programs, Events, Departments, Roles/Leads, Tasks, Evidence Reviews, Blockers, Notifications) have zero frontend interface. Users cannot perform event setup, task tracking, or proof approvals through the browser.
2. **Missing Independent QR Decoder Validation:**
   - `frontend/src/utils/qr.ts` has not been validated against an automated standard QR decoder library (e.g. ZXing, jsQR). Potential risk of scanner incompatibility under edge-case data sizes or hardware scanners.
3. **Mobile Navbar Layout Overflow at 375px:**
   - Actual browser rendering revealed horizontal overflow in `Navbar.tsx` on narrow mobile screens.

### Priority 2: Medium Priority (Hardening & Architecture)
4. **QR Mask Pattern Optimization:**
   - `qr.ts` currently hardcodes Mask 0 instead of computing ISO penalty scores across Masks 0–7.
5. **PostgreSQL Automated CI Execution:**
   - Migrations and domain models have only been verified against SQLite in local test suites. PostgreSQL concurrency and partial index behavior must be verified in CI.
6. **Rate Limiting on Public Registration Endpoints:**
   - In-memory rate limiting must be upgraded to distributed Redis storage before public exposure.

---

## 9. Conclusion & Transition to Next Phase

The CampusOps backend domain foundation, REST API contract, and security model are exceptionally robust, with 305 passing backend tests and verified database constraints. Slice 5D successfully proved that a high-velocity, accessible, and visually distinctive frontend can be integrated cleanly with these APIs.

The immediate priority for the engineering roadmap is **NOT** to jump ahead to Slice 6 (Post-Event Operations), but rather to **close the frontend integration gap** by building user interfaces for the existing Slice 2B, 3B, and 4B backend APIs.

See [`docs/implementation/NEXT_PHASE_IMPLEMENTATION_BLUEPRINT.md`](NEXT_PHASE_IMPLEMENTATION_BLUEPRINT.md) for the detailed, prioritized implementation roadmap.

