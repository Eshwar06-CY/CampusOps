# CampusOps — Development Slice 2C: Authentication Feasibility Spike Report

**Date:** 28 October 2026
**Status:** Completed Spike Analysis & Cryptographic Verification; Live Provider Testing Blocked by Environment Prerequisites
**Authoritative Context:** `Consolidated Documentation/CampusOps_Architecture_Decision_Record_v0.2.md` (ADR-004), `CampusOps_Technical_Specification_v1.1.md`, `CampusOps_PRD_v1.1.md`, `CampusOps_Decision_Log_v1.4.md`
**Working Mode:** Feasibility analysis and synthetic verification only. Production application authentication remains 100% fail-closed without an identity provider adapter.

---

## 1. Executive Summary & Status

This report delivers the technical feasibility evaluation (Technical Gate TG-02) for integrating a managed authentication provider into CampusOps, specifically focusing on the primary candidate: **Supabase Auth (GoTrue)**.

### 1.1 Summary Findings
1. **Cryptographic Validation Feasible on Python 3.13 / Windows:**
   - Verified that `PyJWT 2.10.1` and `cryptography 46.0.3` cleanly generate, sign, and verify asymmetric RS256/ES256 JSON Web Tokens (JWTs) against JSON Web Key Sets (JWKS) on Python 3.13.9 under Windows.
   - Verified that Windows Application Control policies (AppLocker/WDAC) do not interfere with standard asymmetric cryptographic operations in the verified environment.
2. **Local Live Provider Testing Blocked by Host Prerequisites:**
   - The local Docker Desktop daemon is inactive (`open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`).
   - The Supabase CLI is not installed globally or in the npm cache.
   - In accordance with repository constraints ("Do not install Docker, reconfigure Windows services, overwrite another local project, expose services publicly, or create paid resources"), live local container instantiation was not performed.
3. **Current Application Reality:**
   - The normal CampusOps backend application has **no configured identity provider adapter** and **fails closed with HTTP 401 Unauthorized** on all protected endpoints.
   - The automated backend test suite (68 tests) validates application and authorization logic by injecting synthetic `AuthPrincipal` objects via FastAPI dependency injection overrides (`app.dependency_overrides[get_current_principal]`).
   - Production cryptographic signature validation, remote JWKS fetching, session revocation, token refresh, and MFA challenge enforcement are **not yet implemented in production application code**.
4. **Candidate Recommendation:**
   - **"Suitable candidate, with outstanding hosted-verification gates."**
   - Supabase Auth meets the core functional requirements (asymmetric JWT issuance, JWKS discovery, TOTP MFA assurance levels, email confirmation), but requires a custom claims hook or explicit verification query for `email_verified` claims, and must be tested against a running instance before final selection.
   - **Technical Gate TG-02 remains UNPASSED** (Status: `Spike Specification Ready / External Provider Blocked`).

---

## 2. Local Environment Inspection & Prerequisites

The host system was inspected without installing system software or reconfiguring Windows services:

| Check | Tool / Command | Observed Result | Status / Impact |
| :--- | :--- | :--- | :--- |
| **Operating System** | System Info | Windows 11 / Windows PowerShell | Host environment verified. |
| **Node.js** | `node --version` | `v26.1.0` | Present and operational. |
| **npm** | `npm --version` | `11.13.0` | Present and operational. |
| **Docker CLI** | `docker --version` | `Docker version 29.8.0, build 88096ef` | CLI binaries present on host. |
| **Docker Daemon** | `docker info` | `failed to connect to docker API at npipe:////./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified` | **INACTIVE.** Docker Desktop service is stopped. Local container orchestration cannot run. |
| **Podman CLI** | `Get-Command podman` | Not found | Alternative container runtime unavailable. |
| **Supabase CLI** | `Get-Command supabase` | Not found | Supabase CLI not installed in PATH. |
| **Supabase CLI (npx)**| `npx --no-install supabase` | `missing packages: supabase@2.122.0` | Not pre-cached in npm cache. |
| **Standard Port 5432** | `Get-NetTCPConnection` | `0.0.0.0:5432` / `[::]:5432` Listen (PID 9244, `postgres.exe`) | **OCCUPIED.** Host already runs a local PostgreSQL service. |
| **Supabase Ports** | `54321` (API), `54322` (DB), `54323` (Studio), `54324` (Mail) | No active connections | Available for loopback binding when container runtime is active. |

### Exact Blocker for Local Live Execution
Because the Docker Desktop daemon is not running and starting Windows background services or installing software is prohibited, an isolated local Supabase container stack could not be launched. Therefore, live provider tests (actual HTTP registration, transactional email capture via Inbucket, live password reset, live TOTP challenge) could not be executed locally and are deferred to a disposable cloud project or containerized CI environment.

---

## 3. Cryptographic & Architecture Spike Execution

To evaluate asymmetric JWT validation, JWKS caching, and claims mapping without polluting `backend/requirements.txt`, an isolated spike script was executed in a disposable directory outside CampusOps (`$env:TEMP\campusops_auth_spike\test_auth_spike.py`) using system Python (`D:\anaconda3\python.exe`) with `PyJWT 2.10.1` and `cryptography 46.0.3`.

### 3.1 11-Point Feasibility Evaluation Matrix

| Test / Flow Item | Test Methodology | Result | Evidence / Observed Behavior |
| :--- | :--- | :--- | :--- |
| **1. Sign-up, confirmation & sign-in** | Protocol Analysis & Architectural Review | **Analyzed (Live Blocked)** | GoTrue handles user registration and emits confirmation emails. Tokens with `role: "authenticated"` are issued only after confirmation when email verification is enabled. |
| **2. Retrieval & validation of real tokens** | Protocol Analysis & Architectural Review | **Analyzed (Live Blocked)** | Requires live GoTrue instance. Standard Supabase tokens use RS256 or ES256 asymmetric signatures issued from `https://<project-ref>.supabase.co/auth/v1`. |
| **3. Signature, issuer, audience, exp, sub** | Synthetic Cryptographic Test (`PyJWT`) | **PASSED (Synthetic)** | Successfully validated RS256 token signed by private key against public JWK. Enforced matching `iss`, `aud`, unexpired `exp`, and valid UUID `sub`. |
| **4. Rejection of tampered / invalid tokens** | Synthetic Cryptographic Test (`PyJWT`) | **PASSED (Synthetic)** | Tampered payload: rejected with `InvalidSignatureError`.<br>Wrong signing key: rejected with `InvalidSignatureError`.<br>Expired token: rejected with `ExpiredSignatureError`.<br>Wrong issuer: rejected with `InvalidIssuerError`.<br>Wrong audience: rejected with `InvalidAudienceError`.<br>`alg="none"`: rejected with `InvalidAlgorithmError`. |
| **5. JWKS caching & unknown-key handling** | Synthetic Cryptographic Test (`PyJWT`) | **PASSED (Synthetic)** | Loaded multi-key `PyJWKSet`. Tested unknown `kid` detection. Unknown `kid` correctly bypassed cached keys, triggering cache invalidation / refresh mechanism. |
| **6. Subject mapping to `UserProfile`** | Synthetic Integration (`test_api_auth_boundary.py`) | **PASSED (Synthetic)** | Verified in `test_api_auth_boundary.py`. `sub` claim maps 1:1 to `user_profiles.auth_subject_id`. Duplicate registrations with identical `sub` resolve existing profile without crash. |
| **7. Prevention of account takeover** | Regression Suite (`test_api_auth_boundary.py`) | **PASSED (Synthetic)** | Hardened `get_current_user` rejects unverified principals attempting to link existing accounts (`403 Forbidden`). Rejects conflicting subject IDs (`403 Forbidden`). |
| **8. Invitation acceptance lifecycle** | Integration Suite (`test_api_invitations.py`) | **PASSED (Synthetic)** | Single-use token acceptance verifies email match (`intended_email == principal.email`). Inactive/unverified users rejected. Stale prior roles revoked on membership reactivation. |
| **9. Password recovery & session revocation** | Protocol Analysis & Architectural Review | **Analyzed** | Asymmetric JWTs are stateless. Revocation cannot be verified locally without: (a) short access token expiry (15m) + refresh token rotation, or (b) querying GoTrue's session endpoint/webhook. Standard pattern: enforce short access token TTL. |
| **10. TOTP MFA enrollment & assurance** | Synthetic Cryptographic Test (`PyJWT`) | **PASSED (Synthetic)** | Tested token containing `aal: "aal2"` and `amr: [{"method": "totp", ...}]`. FastAPI dependency can cleanly enforce `aal == "aal2"` for elevated operations. |
| **11. Identity vs CampusOps Authorization** | Architectural Verification | **PASSED** | Clean boundary established. Supabase Auth owns identity authentication and credentials. CampusOps relational database owns all workspace memberships, roles (`PRIMARY_ADMIN`, `EVENT_LEAD`, etc.), permissions, and scopes. |

---

## 4. Normal Application Reality & Posture Baseline

To preserve an honest, transparent implementation audit, the following boundaries are explicitly confirmed:

1. **Normal Application Code (`backend/app/`):**
   - Contains **no hardcoded credentials, mock provider bypasses, or insecure fallbacks**.
   - [`get_current_principal`](file:///D:/Antigravity_Projects/CampusOps/backend/app/auth/principal.py#L32-L48) raises `HTTP 401 Unauthorized` (`"Authentication credentials were not provided or identity provider is unconfigured"`) on all protected calls when no adapter is configured.
   - Caller-supplied identity headers (`X-User-ID`, `X-User-Email`) are explicitly ignored and untrusted.
2. **Backend Automated Test Suite (`backend/tests/`):**
   - The 68 passing backend tests execute against a pure-Python SQLite database.
   - Tests authenticate by applying FastAPI dependency overrides (`app.dependency_overrides[get_current_principal]`) supplying known `AuthPrincipal` test fixtures.
   - This isolates business domain logic, role permissions, and tenant isolation from external network dependencies.
3. **Platform Administrator Operational Bootstrap (`backend/scripts/bootstrap_platform_admin.py`):**
   - Operates as a server-side CLI script only; zero HTTP endpoints exist for appointing platform administrators.
   - Targets the configured database (`get_session_factory`).
   - Requires an existing user with `account_status == "active"` and `email_verified_at is not None`.
   - Fails safely and aborts execution if an active platform administrator already exists.
   - Records audit reasons and timestamps.

---

## 5. Candidate Evaluation: Supabase Auth (GoTrue)

### 5.1 Strengths & Architectural Fit
- **Asymmetric Signature Verification (RS256/ES256):** Supabase Auth issues JWTs signed by asymmetric keys exposed via a standard JWKS endpoint (`/.well-known/jwks.json`). FastAPI can verify tokens locally using `PyJWT[crypto]` with zero per-request network latency to the IdP.
- **Standards-Compliant Claims:** Standard claims (`sub`, `iss`, `aud`, `exp`, `iat`) align directly with CampusOps [`AuthPrincipal`](file:///D:/Antigravity_Projects/CampusOps/backend/app/auth/principal.py#L18-L24).
- **MFA Assurance Levels (`aal`):** GoTrue natively supports TOTP enrollment and challenge, reflecting MFA elevation in `aal: "aal2"` claims.
- **Tenant Authorization Independence:** CampusOps does not need Supabase Row Level Security (RLS) or Supabase user metadata for permissions. The application maintains 100% tenant isolation in its own relational schema.

### 5.2 Identified Limitations & Required Remediations
1. **`email_verified` Claim Convention:**
   - *Issue:* In default GoTrue JWT configurations, the top-level claims payload includes `role: "authenticated"` and `email`, but may not include a standard boolean `email_verified` claim unless configured.
   - *Required Remediation:* If selecting Supabase Auth, CampusOps must configure the Supabase **Custom Access Token Hook** (a SQL function in PostgreSQL) to explicitly inject `"email_verified": true` into the JWT claims payload, OR configure GoTrue to prevent issuing tokens to unconfirmed users and map `role == "authenticated"` to verified status.
2. **Stateless Access Token Revocation:**
   - *Issue:* If a user account or session is revoked in Supabase, an already-issued stateless JWT remains cryptographically valid until its `exp` time.
   - *Required Remediation:* Configure short access token expiration (e.g., 10 to 15 minutes) and rely on client-side refresh token exchange. For critical actions (e.g. transfer of workspace primary administrator), enforce re-authentication.
3. **Dependency Footprint:**
   - *Recommendation:* Do **not** install the heavy `supabase-py` monolithic SDK. The FastAPI backend only needs lightweight `PyJWT[crypto]` (`~1.5 MB`) to verify JWTs and fetch JWKS.

---

## 6. Provider Recommendation & Technical Gate Status

### Evidence-Based Recommendation
**"Suitable candidate, with outstanding hosted-verification gates."**

Supabase Auth is technically and architecturally compatible with CampusOps's modular FastAPI backend and relational schema. The cryptographic and claims processing pipeline is verified. However, final adoption cannot be approved until live verification against a running GoTrue instance (either local Docker or disposable hosted project) proves email confirmation flow, custom claims hook injection, and refresh token rotation.

### Technical Gate Status
- **Gate:** **TG-02 (Authentication Spike)**
- **Current Status:** **Spike Specification Ready / External Provider Blocked**
- **Condition for Passing TG-02:** Provisioning of disposable test project credentials or activation of a local containerized test environment to run live integration tests against real Supabase-issued tokens and email capture.
