# CampusOps — Product Decision Log v1.5 Addendum

**Date:** 28 October 2026
**Status:** Scoped Implementation Addendum for Slice 2C Feasibility & Slice 3A Domain Foundation
**Preceding Decisions:** FA-001–FA-009, FPC-01–FPC-05 in `CampusOps_Decision_Log_v1.4.md` remain authoritative and unchanged.
**Authoritative Context:** `CampusOps_Architecture_Decision_Record_v0.2.md` (ADR-004, ADR-005), `CampusOps_PRD_v1.1.md`, `CampusOps_Technical_Specification_v1.1.md`

---

## 1. Authentication Integration Position (Slice 2C Status)

1. **Preferred Candidate:** Supabase Auth (GoTrue) is designated as the preferred candidate for a future identity-provider adapter.
2. **Provisional Status:** The provider integration decision remains strictly **provisional**. Cryptographic JWT verification, asymmetric JWKS rotation, and claims parsing on Python 3.13 / Windows have been proven feasible synthetically (`docs/implementation/SLICE_2C_AUTH_FEASIBILITY_REPORT.md`), but live provider verification (email confirmation, token issuance, refresh token rotation, live TOTP challenge) remains blocked by host container prerequisites (inactive Docker daemon, missing Supabase CLI).
3. **Technical Gate Status:** **TG-02 remains UNPASSED** (Status: `Spike Specification Ready / External Provider Blocked`).
4. **Fail-Closed Runtime:** The normal application runtime must remain 100% fail-closed (HTTP 401 Unauthorized) when unconfigured. No mock auth bypasses or dummy credentials exist in production code.
5. **Authorization Ownership:** All domain authorization, tenant isolation, workspace membership, scoped roles, and permissions belong exclusively to CampusOps and its relational database (`user_profiles`, `organizations`, `organization_memberships`, `role_assignments`, `platform_admins`, `event_lead_assignments`), never to identity provider metadata or external claims.

---

## 2. Scoped Slice 3 Design Decisions

The following initial-release architectural and domain defaults are formally adopted for Development Slice 3:

### D-SLICE3-01: Program Department Scope Exclusivity
- Departments belonging to a multi-event `Program` are shared across that program's child events.
- Child-event-specific departments within a multi-event program are explicitly **out of scope** for the initial release.
- A standalone `Event` (`program_id IS NULL`) owns its own departments (`standalone_event_id = event.id`).
- Database-level check constraint `ck_departments_exclusive_parent` enforces that a department has exactly one parent: either a `program_id` XOR a `standalone_event_id`.

### D-SLICE3-02: Event Lead Cardinality & Invariants
- An event may have multiple active event leads (`EventLeadAssignment`).
- A workspace member may have at most **one active lead assignment** to a given event at a time, enforced via composite unique constraint on `(event_id, membership_id)` where `revoked_at IS NULL`.
- An event lead must hold an active membership in the same organization as the event.

### D-SLICE3-03: Immutability of Event Hierarchy
- Converting an existing standalone event into a program child event (or detaching a child event into a standalone event) is **unsupported** in the initial release.
- `Event.program_id` is immutable after creation to prevent orphaned departmental scopes or cross-tenant hierarchy corruption.

### D-SLICE3-04: Non-Destructive Archival Semantics
- Archiving a `Program` or `Event` (`archived_at IS NOT NULL`) is strictly non-destructive. Child records, assignments, and historical data remain safely preserved in the database.
- Operational reads and mutations must respect parent archival status: an archived parent Program or Event cannot accept new operational assignments, department creations, or lead appointments. Hard-deletes and cascading destructions are prohibited.

### D-SLICE3-05: Event Duration, Multi-Day Scheduling, and Timezone Policy
- `event_date: Date` represents the local calendar start date of an event.
- `event_end_date: Date` is optional. When absent, the event is treated as a single-day event. When supplied, it must be on or after `event_date`.
- `planned_start_time` and `planned_end_time` are optional timestamps (may be absent if timing is not yet finalized).
- **Single-Day Sequencing:** For a single-day event (`event_end_date IS NULL OR event_end_date == event_date`) with both times supplied, the end time must not precede the start time (`planned_end_time >= planned_start_time`).
- **Multi-Day Sequencing:** A multi-day event (`event_end_date > event_date`) may end at an earlier clock time than it starts (e.g., starts at 18:00 on Day 1, ends at 02:00 on Day 2). Database check constraint `ck_events_time_order` permits `planned_end_time < planned_start_time` only when `event_end_date > event_date`.
- **Timezone Interpretation:** Event times are interpreted and validated using the Event's IANA timezone identifier (persisted in `events.timezone`, default `'Asia/Kolkata'`). Invalid timezone strings are rejected by domain services.
- **Program Date Alignment:** For child events in a Program, the event's start date and end date must fall within the parent Program's `planned_start_date` and `planned_end_date` bounds.

### D-SLICE3-06: Non-Destructive Archival vs. Event Cancellation Policy Closure
- Cancellation remains deferred from the active entity lifecycle in Slice 3B. No `cancelled` state is introduced at this time.
- All non-operational retirement is handled through non-destructive archival (`status = 'archived'`, `archived_at` recorded).
- Formal event cancellation semantics, participant notification triggers, and cancellation audit reasons are recorded for a future release slice before registration and ticketing are activated.
