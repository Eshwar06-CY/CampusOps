# CampusOps — Product Decision Log v1.4

**Date:** 28 October 2026  
**Status:** Founder-approved policies FA-001–FA-009 and FPC-01–FPC-05 retained; technical closure review recorded. Application implementation remains unauthorized.

## 1. Current authoritative baseline

- `CampusOps_PRD_v1.1.md`
- `CampusOps_Technical_Specification_v1.1.md`
- `CampusOps_Delivery_Plan_v1.1.md`
- `CampusOps_Founder_Approval_Checklist_v0.3.md`
- `CampusOps_Final_Pre_Implementation_Closure_Plan_v1.1.md`
- `CampusOps_Implementation_Readiness_Review_v1.1.md`
- `CampusOps_Final_Technical_Closure_Review_v1.0.md`

Older requirements/API/architecture drafts remain useful design history but do not override the current baseline.

## 2. Decisions retained

FA-001–FA-009 and FPC-01–FPC-05 remain founder-approved as recorded in v1.3 and the approval checklist. This update does not change those policies or authorize implementation.

## 3. Technical findings recorded

1. Supabase Auth remains the preferred candidate pending implementation-level feasibility/security checks. Official documentation describes JWT verification and TOTP MFA, but those flows have not been tested in the CampusOps environment.
2. Supabase lists Mumbai (`ap-south-1`) as an available region. Mumbai is a recommended candidate for an India-focused pilot, subject to actual data-residency requirements and review of provider terms.
3. Supabase's built-in email service is suitable for limited development/testing only; use a local test mailbox during development and select/configure custom SMTP before real invitation and recovery emails.
4. A free project may be suitable for disposable synthetic-data development but is not accepted as the live-event deployment plan: current pricing documentation notes resource limits, no automatic backups on Free and pausing after one week of inactivity. Confirm current price and included backup features before any pilot.
5. Private evidence storage, real email, production hosting, Google Forms connector and full offline behavior may be deferred only if no unfinished feature is represented as working and the affected workflow remains safely disabled or has a documented fallback.
6. The first physical schema/API contract should be finalized per implementation slice, not for every future capability at once.

## 4. Current decision status

| Area | Status |
|---|---|
| Product scope and exclusions | Confirmed |
| FA-001–FA-009 | Founder-approved |
| FPC-01–FPC-05 | Founder-approved |
| Supabase Auth | Preferred candidate; technical checks pending |
| PostgreSQL/provider/region | PostgreSQL proposed; provider and region need confirmation before hosted test/pilot |
| Email provider | Deferred for local dev; choose before real invitations/recovery emails |
| Private file storage | Provider and rules pending before file evidence feature is enabled |
| Google Forms | Deferred candidate; native registrations first |
| Offline check-in | Full offline deferred; online-first and manual fallback approved |
| Physical schema and exact API contracts | Finalize by slice before implementing that slice |
| Current repo/toolchain inspection | Pending and must precede file changes/installations when implementation is authorized |
| Application implementation | Not authorized |
| Real-data pilot | No-go until pilot gates are satisfied |

## 5. Go/no-go record

**Current result: NO-GO for implementation until the founder explicitly authorizes it.** Documentation is sufficiently mature to enter a focused implementation-readiness/feasibility check. The current review did not inspect the user's Windows environment, execute code, test a provider integration, or freeze a physical schema/API contract. No test is claimed to have passed.

A future authorization does not automatically approve a real-data pilot. Production readiness requires a separate evidence-based gate.

## 6. Version history

| Version | Change |
|---|---|
| 1.3 | Records approval of FPC-01–FPC-05 and current consolidated baseline. |
| 1.4 | Records final technical closure findings, current provider-doc references and staged next steps; implementation remains unauthorized. |

## 7. Official technical references reviewed

- Supabase JWT verification: https://supabase.com/docs/guides/auth/jwts
- Supabase MFA: https://supabase.com/docs/guides/auth/auth-mfa
- Supabase regions: https://supabase.com/docs/guides/platform/regions
- Supabase pricing: https://supabase.com/pricing
- Supabase Auth SMTP: https://supabase.com/docs/guides/auth/auth-smtp
