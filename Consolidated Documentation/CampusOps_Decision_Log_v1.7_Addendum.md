# CampusOps — Product Decision Log v1.7 Addendum

**Date:** 29 October 2026  
**Status:** Scoped Implementation Addendum for Slice 5 (Participant Registration, Ticketing & Attendance Check-In Architecture)  
**Preceding Decisions:** FA-001–FA-009, FPC-01–FPC-05 in `CampusOps_Decision_Log_v1.4.md`, D-SLICE3-01–D-SLICE3-06 in `CampusOps_Decision_Log_v1.5_Addendum.md`, and D-SLICE4-01 in `CampusOps_Decision_Log_v1.6_Addendum.md` remain authoritative and unchanged.  
**Authoritative Context:** `CampusOps_PRD_v1.1.md` (CO-FR-008, CO-FR-009, CO-SEC-003, FA-005, FA-007, AT-004), `CampusOps_Technical_Specification_v1.1.md` Section 3.4, `CampusOps_Data_Model_and_Relationship_Map_v0.1.md` Section 8, `CampusOps_Role_and_Permission_Matrix_v0.1.md`, `CampusOps_API_Contract_Draft_v0.2.md` Section 7, and `docs/implementation/SLICE_5_SCOPE_AND_ARCHITECTURE_PLAN.md`.

---

## 1. Scoped Slice 5 Design Decisions

The following initial-release architectural and domain defaults are formally adopted for Development Slice 5:

### D-SLICE5-01: Individual Human Participant Capacity Metric
- **Capacity Definition:** Event capacity (`capacity_limit` in `event_registration_settings`) represents the physical human headcount capacity of the event venue or operational limit.
- **Consumption Accounting:** Solo registrations consume exactly one (1) capacity slot. Team registrations consume exactly *N* capacity slots, where *N* is the count of confirmed team participants submitted (`len(participants)`).
- **Concurrency & Atomic Reservation:** Capacity reservations must be guarded at the database level using atomic transaction validation (`current_confirmed_count + slots <= capacity_limit`). If a team of size *N* cannot be fully accommodated without exceeding `capacity_limit`, the entire registration must fail with HTTP 409 Conflict; partial team admissions are strictly prohibited.
- **Waitlist Semantics:** When waitlists are enabled and capacity is reached, waitlist order is FIFO by `created_at`. Waitlist promotion must verify that the full team size fits within available slots before confirming.

#### Architectural & PRD Grounding
1. **Safety & Fire Codes:** Physical campus venue limits (auditoriums, labs, workshops) are defined by human bodies, not registration groups. Counting teams as a single unit would lead to catastrophic venue overcrowding.
2. **Deterministic Availability:** PRD v1.1 CO-FR-008 and FA-005 require enforceable registration limits that prevent overselling capacity.

---

### D-SLICE5-02: Non-Payment Digital Admission Pass Baseline
- **Pass Semantics:** In the initial release, a "ticket" (`tickets` table) is strictly a digital admission pass / boarding credential verifying a participant's confirmed registration and eligibility to enter the event venue.
- **Payment Gateway Exclusion:** Payment processing, payment gateway integrations (Razorpay, Stripe), fee collection, ticketing tiers with pricing, invoices, and refunds are explicitly **out of scope** for Slice 5.
- **Pass Credential Security:** Each ticket pass possesses a cryptographically random, unguessable token (`CO-PASS-<UUID4>`).
- **Zero PII in QR Codes:** QR codes rendered for passes encode only the opaque ticket token or secure verification URL. Personally Identifiable Information (PII) such as participant name, email, phone number, or roll number must never be baked into the QR payload.
- **Single Active Pass Invariant:** A participant may hold at most one active (`ISSUED`) pass per event at any time, enforced by the partial unique index `uq_ticket_participant_active`.

#### Architectural & PRD Grounding
1. **Core Operational Focus:** CampusOps core mission focuses on student operations, logistics, and verified attendance. Free student events, club orientations, hackathons, and departmental fests do not require monetary gatekeeping for operational validation.
2. **Privacy & Tamper Resistance:** PRD v1.1 CO-SEC-003 and FA-007 mandate privacy-first attendee data protection and unguessable tokens to prevent ticket forgery and screen scraping.

---

### D-SLICE5-03: Event-Scoped Registration Model (No Monolithic Program Merging)
- **Scope of Registration:** Registration settings, participant rosters, capacity limits, tickets, and attendance check-in records are strictly scoped to the individual `Event` entity (standalone events or child events within a program).
- **Program-Level All-Access Pass Deferred:** For multi-event programs (festivals, orientations), attendees register for each child event (workshops, keynotes, competitions) independently. Monolithic program-wide bundled passes or cross-event master rosters are deferred to a subsequent enhancement.
- **Cross-Event Attendance Isolation:** Checking in to Event A in a festival grants zero admission to Event B. Each child event maintains its own independent check-in roster and attendance log.

#### Architectural & PRD Grounding
1. **Capacity Independence:** In a festival, the main auditorium may seat 500 participants, while a coding lab workshop accommodates only 40. Scoping registrations and check-ins directly to the `event_id` provides exact room capacity management without complex quota sub-allocation.
2. **Schema Uniformity:** Reuses existing multi-tenant scoping invariants (`organization_id`, `event_id`) across all tables without requiring conditional program-level join semantics.

---

### D-SLICE5-04: Manager-Only Check-In Correction & Void Authority
- **Check-In Privilege:** Ordinary desk staff assigned the `REGISTRATION_STAFF` functional role (`ACTION_CHECK_IN` permission) are authorized to perform pass scans and manual check-ins.
- **Void & Correction Privilege:** Desk staff do **NOT** have permission to delete, cancel, or void an existing check-in. Voids and corrections require elevated manager authority (`ACTION_CORRECT_CHECK_IN`), held exclusively by `PRIMARY_ADMIN`, `OFFICE_BEARER`, or `EVENT_LEAD`.
- **Immutable Correction Audit Log:** Check-in corrections do not hard-delete attendance history. When a check-in is voided, `check_ins.status` transitions to `REVOKED` and an immutable record is inserted into `check_in_corrections` containing `check_in_id`, `corrected_by_user_id`, `reason` (mandatory minimum 10 characters), and `corrected_at`.

#### Architectural & PRD Grounding
1. **Audit Integrity & Anti-Fraud:** Prevents desk volunteers from colluding to erase attendance records or tampering with headcount audits.
2. **Compliance & Disciplinary Audits:** PRD v1.1 CO-FR-009, CO-SEC-003, and AT-004 require verifiable, auditable check-in logs for academic credit and certificate issuance.

