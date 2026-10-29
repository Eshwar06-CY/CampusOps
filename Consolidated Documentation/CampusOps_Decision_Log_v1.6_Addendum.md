# CampusOps — Product Decision Log v1.6 Addendum

**Date:** 29 October 2026  
**Status:** Scoped Implementation Addendum for Slice 4 (Task Management & Operational Blockers)  
**Preceding Decisions:** FA-001–FA-009, FPC-01–FPC-05 in `CampusOps_Decision_Log_v1.4.md` and D-SLICE3-01–D-SLICE3-06 in `CampusOps_Decision_Log_v1.5_Addendum.md` remain authoritative and unchanged.  
**Authoritative Context:** `CampusOps_PRD_v1.1.md` (CO-FR-005, CO-FR-011, FA-004), `CampusOps_Technical_Specification_v1.1.md` Section 3.3, `CampusOps_Data_Model_and_Relationship_Map_v0.1.md` Section 7.2, and `docs/implementation/SLICE_4A_ASSIGNMENT_POLICY_AND_MIGRATION_REVIEW.md`.

---

## 1. Scoped Slice 4 Design Decisions

The following initial-release architectural and domain defaults are formally adopted for Development Slice 4:

### D-SLICE4-01: Single Accountable Task Assignee
- **Cardinality Constraint:** Each operational task may have at most **one active assignee** at any time.
- **Reassignment History Retention:** Reassigning a task immediately ends the active status of the former assignee (`assignment_status = 'unassigned'`, recording `unassigned_at` timestamp and `unassigned_by_user_id` actor) and preserves that record permanently in `task_assignees` before inserting and activating the replacement assignee.
- **Database Engine Enforcement:** The partial unique index `uq_task_assignee_active` on `(task_id)` WHERE `assignment_status = 'active'`, delivered via additive Alembic migration `a6b7c8d9e0f1`, remains authoritative and enforces strict mutual exclusion against concurrent assignment attempts at the database level.
- **Relational Integrity Model:** `TaskAssignee` remains a relational join table maintaining full historical attribution (`assigned_at`, `assigned_by_user_id`, `unassigned_at`, `unassigned_by_user_id`). Multiple user IDs must never be packed into a string or array field.
- **Out of Scope for Initial Release:** Multiple simultaneous active assignees (co-assignees or group ownership) are explicitly **out of scope** for the initial release. Any future transition to multiple active assignees requires a separately approved product decision from the founder and an additive Alembic migration.

#### Architectural & PRD Grounding
1. **Identifiable Accountable Owner:** PRD v1.1 CO-FR-005 ("Active tasks require owner and specific deadline"), CO-FR-011 ("Authorized reassignment updates current owner, retains previous assignment/history and notifies relevant people"), and FA-004 ("Active tasks require a specific deadline and owner") mandate clear individual accountability without ambiguity regarding who is responsible for task completion and proof submission.
2. **Cardinality Reconciliation:** Prompt 15 resolved the distinction between Constraint A (one active assignee per task on `task_id`), Constraint B (multiple active assignees), and Constraint C (one active assignment per membership on `task_id, membership_id`). Model A is locked as the authoritative initial-release policy.

