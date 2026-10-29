# CampusOps — Slice 4A Task Assignment Policy & Migration Integrity Review

**Date:** 29 October 2026  
**Status:** Completed & Verified  
**Repository:** `D:\Antigravity_Projects\CampusOps`  
**Base Commit:** `7caf0bf`  
**Alembic Head Revision:** `a6b7c8d9e0f1` (`backend/alembic/versions/a6b7c8d9e0f1_slice_4a_single_active_task_assignee_index.py`)  
**Parent Revision:** `f5a6b7c8d9e0` (`backend/alembic/versions/f5a6b7c8d9e0_slice_4a_task_management_and_operational_blockers.py`)  
**Backend Test Results:** 174 passed in 6.06s (including incremental migration lifecycle test)  
**Frontend Test Results:** 2 passed in 1.06s; production build succeeded (`tsc -b && vite build` in 109ms)  
**Virtual Environment Check:** `python -m pip check` verified clean (zero broken requirements)  
**Git Working Tree:** Zero files staged, zero commits created  

---

## 1. Executive Summary & Review Baseline

In accordance with Prompt 15, an authoritative architectural and database integrity review was conducted to resolve two core engineering questions identified during the Slice 4A audit:

1. **Task-Assignment Cardinality:** Distinguishing and evaluating the three distinct assignment constraints across authoritative documentation (`Consolidated Documentation/`), architectural intent, and runtime domain services.
2. **Migration Immutability:** Determining whether the Slice 4A audit modified an existing Alembic migration (`f5a6b7c8d9e0`) in place, restoring the original migration definition, and delivering the approved database index change via an additive migration (`a6b7c8d9e0f1`).

### Summary of Outcomes:
- **Cardinality Conflict Clarified:** Authoritative documents show a deliberate architectural split between structural schema capability (supporting one or more assignees without multi-user text packing) and the operational single-owner requirement in PRD v1.1. Multiple-assignee behavior was explicitly flagged as an open decision in the Architecture Traceability Review (row 39).
- **Migration Immutability Restored:** Migration `f5a6b7c8d9e0` was restored to its exact original definition with `['task_id', 'membership_id']`. The hardened single-active-assignee partial unique index on `['task_id']` is now delivered via additive migration `a6b7c8d9e0f1`.
- **Full Migration Lifecycle Verified:** An automated migration lifecycle test (`test_slice_4a_assignee_index_migration_lifecycle`) verified the step-by-step upgrade to `f5a6b7c8d9e0`, upgrade to `a6b7c8d9e0f1`, downgrade to `f5a6b7c8d9e0`, and re-upgrade to `head` on an isolated database.
- **Strict Scope Preserved:** Zero Slice 4B REST APIs, Pydantic schemas, or frontend screens were built. All changes remain unstaged and uncommitted.

---

## 2. Task-Assignment Cardinality: Authoritative Specification Analysis

### 2.1 The Three Distinct Constraints

| Constraint | Database Representation | Meaning & Scope |
| :--- | :--- | :--- |
| **Constraint A (Single Active Assignee per Task)** | `uq_task_assignee_active` on `['task_id'] WHERE assignment_status = 'active'` | Exactly one active worker can exist for a given task at any time across the entire database. Prevents concurrent co-assignees. |
| **Constraint B (Multiple Active Assignees per Task)** | No unique index restricting `task_id` to one active row | A task may have multiple active workers simultaneously collaborating on the same task. |
| **Constraint C (Single Active Assignment per Membership per Task)** | `uq_task_assignee_active` on `['task_id', 'membership_id'] WHERE assignment_status = 'active'` | A single workspace member cannot be concurrently active twice on the same task. Allows multiple distinct members to be active if product rules permit. |

### 2.2 Review of Authoritative Documentation (`Consolidated Documentation/`)

1. **`CampusOps_Technical_Specification_v1.1.md` Section 3.3 (Line 99):**
   > *"TaskAssignee: one or more authorized individual assignments where product rules allow it."*
   - Explicitly envisions structural support for multiple assignments when authorized by product rules.

2. **`CampusOps_Data_Model_and_Relationship_Map_v0.1.md` Section 7.2 (Lines 251–258):**
   > *"A join record connecting tasks and assigned workspace members. This supports one or more owners without storing multiple users in one text field... Changing an assignment should preserve history. At least one clearly responsible owner should be identifiable for active work; whether multiple assignees are allowed for every task is a product decision to validate."*
   - Directly notes that join table `TaskAssignee` is structured to support multiple owners, while identifying that whether multiple assignees are permitted for every task is an **open product decision to validate**.

3. **`CampusOps_Architecture_Traceability_Review_v0.1.md` Section 2, Table 1, Row 5 (Line 39):**
   > *"Task owner and deadline: Require a clear accountable owner and a specific due date/time policy. Decide multiple-assignee behavior, whether deadlines can change after work starts, who may change them, and how deadline changes are audited/notified."*
   - Status is formally marked as **"Partially aligned"**, recording multiple-assignee behavior as an explicit unresolved architectural/product decision.

4. **`CampusOps_PRD_v1.1.md` (CO-FR-005, CO-FR-011, FA-004):**
   > - **CO-FR-005:** *"Active tasks require owner and specific deadline..."*
   > - **CO-FR-011:** *"Authorized reassignment updates current owner, retains previous assignment/history and notifies relevant people."*
   > - **FA-004:** *"Active tasks require a specific deadline and owner; event timezone is reference; assignee requests changes with reason; authorized lead/office bearer decides..."*
   - The operational workflow in the PRD consistently treats tasks as having a singular accountable "owner" or "assignee".

### 2.3 Reconciliation and Consequences of Models A and B

```
                      +------------------------------------------+
                      |         Task Assignment Models           |
                      +------------------------------------------+
                                     /            \
                                    /              \
           [Model A: Hard DB Lock] /                \ [Model B: Layered Invariant]
                                  v                  v
                 +-----------------------+    +-----------------------+
                 | uq on (task_id)       |    | uq on (task_id, mb_id)|
                 | Service: Single owner |    | Service: Single owner |
                 +-----------------------+    +-----------------------+
```

#### Model A: Single Active Assignee Enforced at Database Level
- **Mechanism:** Partial unique index on `(task_id)` WHERE `assignment_status = 'active'`.
- **Pros:**
  - Absolute database engine-level guarantee against race conditions creating multiple active assignees.
  - Matches PRD v1.1 singular owner language ("current owner", "specific owner").
- **Cons:**
  - Hard-locks the database schema against co-owners or multi-assignee workflows.
  - If the founder resolves the open decision in `Architecture Traceability Review` row 39 in favor of multi-assignee tasks, a database migration is mandatory to drop the constraint.

#### Model B: Layered Constraint (DB Enforces Constraint C; Service Enforces Singular Owner)
- **Mechanism:** Partial unique index on `(task_id, membership_id)` WHERE `assignment_status = 'active'`. Domain service deactivates previous active assignees upon reassignment.
- **Pros:**
  - Exactly reflects the relational data model's intent: join table supports "one or more owners without storing multiple users in one text field".
  - Clean separation: DB prevents member duplicate assignment; service enforces singular owner business rules today.
  - Zero schema migration needed if future product phases introduce multi-assignee tasks.
- **Cons:**
  - Concurrency safety against two distinct members being assigned simultaneously relies on serializable transactions or explicit row locking (`SELECT FOR UPDATE`) rather than a simple unique index collision.

### 2.4 Product Recommendation for Founder Review Before Slice 4B

**Recommendation:**
1. **Maintain Current Single-Owner Workflow:** In Slice 4B, the REST APIs and domain services will continue to enforce single active assignee per task, matching PRD CO-FR-005 and CO-FR-011.
2. **Current Database State:** Additive migration `a6b7c8d9e0f1` currently enforces Model A (single active assignee at DB level).
3. **Founder Decision Gate:** Prior to any product expansion requiring co-assignees, the founder must formally approve the multi-assignee workflow. If approved, an additive migration will drop the single-column index and restore `(task_id, membership_id)`.

---

## 3. Migration Immutability Audit & Remediation

### 3.1 The Migration Immutability Breach

During Prompt 14 (Slice 4A audit), the auditor observed that `f5a6b7c8d9e0_slice_4a_task_management_and_operational_blockers.py` defined `uq_task_assignee_active` on `['task_id', 'membership_id']`. The auditor categorized this as an integrity gap ("AUD-4A-01") and modified the existing migration file directly in place.

**Why In-Place Migration Editing Is Prohibited:**
- In production engineering and team development, migration files represent immutable historical milestones.
- Databases that executed `alembic upgrade head` before the audit have the index on `(task_id, membership_id)`. Modifying `f5a6b7c8d9e0` desynchronizes those environments and corrupts the migration contract.
- In CampusOps, prior audits strictly followed additive migrations (e.g., `d81e3a5f2c90` for Slice 3A integrity hardening, `e4f5a6b7c8d9` for Slice 3B multi-day event bounds).

### 3.2 Remediation Applied

1. **Restored `f5a6b7c8d9e0`:**
   In `backend/alembic/versions/f5a6b7c8d9e0_slice_4a_task_management_and_operational_blockers.py`, restored the original index definition:
   ```python
   op.create_index(
       'uq_task_assignee_active',
       'task_assignees',
       ['task_id', 'membership_id'],
       unique=True,
       sqlite_where=sa.text("assignment_status = 'active'"),
       postgresql_where=sa.text("assignment_status = 'active'"),
   )
   ```

2. **Introduced Additive Migration `a6b7c8d9e0f1`:**
   Created `backend/alembic/versions/a6b7c8d9e0f1_slice_4a_single_active_task_assignee_index.py`:
   - `revision = 'a6b7c8d9e0f1'`
   - `down_revision = 'f5a6b7c8d9e0'`
   - `upgrade()`:
     - Drops index `uq_task_assignee_active`
     - Recreates index `uq_task_assignee_active` on `['task_id']` WHERE `assignment_status = 'active'`
   - `downgrade()`:
     - Drops index `uq_task_assignee_active`
     - Recreates index `uq_task_assignee_active` on `['task_id', 'membership_id']` WHERE `assignment_status = 'active'`

3. **Current Alembic Revision Chain:**
   ```
   880d8e4eb890 (Slice 2A: Identity & Org)
         |
   c92f1b4a3d10 (Slice 3A: Programs, Events, Departments, Leads)
         |
   d81e3a5f2c90 (Slice 3A: Integrity Hardening)
         |
   e4f5a6b7c8d9 (Slice 3B: Event End Date & Multi-Day Bounds)
         |
   f5a6b7c8d9e0 (Slice 4A: Task Management & Operational Blockers)
         |
   a6b7c8d9e0f1 (Slice 4A: Single Active Task Assignee Index Hardening) [HEAD]
   ```

4. **Model Metadata Alignment:**
   `backend/app/models/task.py` defines `uq_task_assignee_active` on `"task_id"`, perfectly matching the head of the migration chain (`a6b7c8d9e0f1`).

---

## 4. Verification of Domain & Security Invariants

All core domain and security invariants remain fully verified and regression-tested:

| Invariant | Implementation Mechanism | Verified Behavior |
| :--- | :--- | :--- |
| **Assignment History Retention** | `TaskAssignee.assignment_status` + audit timestamps | When Worker 1 is reassigned to Worker 2, Worker 1's record transitions to `unassigned` with `unassigned_at` and `unassigned_by_user_id`. History is never deleted. |
| **Authority Revocation on Reassignment** | `services/permissions.py` active assignee evaluation | Unassigned worker immediately loses `ACTION_VIEW_TASK` (unless an event/dept lead) and `ACTION_SUBMIT_PROOF`. Worker 2 gains both. |
| **Unauthorized Assignment Prevention** | `services/permissions.py` (`ACTION_MANAGE_TASK_ASSIGNMENT`) | Non-leads (e.g., plain coordinators or members) cannot call `assign_task`. Raises `PermissionDeniedError`. |
| **Self-Review Prohibition** | `services/task.py` (`review_task_submission`) | An assignee or submitter cannot approve their own submission, even if they hold lead roles elsewhere. Raises `SelfReviewError`. |
| **Transactional Atomicity** | Atomic updates & single-transaction reassignments | Failed operations do not leave partial assignments or orphan history records. |
| **Terminal Status Immutability** | Guard checks in `services/task.py` | Completed or cancelled tasks cannot be reassigned, deadline-modified, or submitted. Raises `TaskWorkflowError`. |

---

## 5. Verification Command Results

### 5.1 Backend Pytest Suite
```powershell
$env:DISABLE_SQLALCHEMY_CEXT="1"; python -m pytest backend/tests
```
**Result:** `174 passed in 6.06s` (including new incremental migration lifecycle test).

### 5.2 Incremental Migration Test Execution
```powershell
$env:DISABLE_SQLALCHEMY_CEXT="1"; python -m pytest backend/tests/test_migrations.py
```
**Result:** `2 passed in 1.49s`. Verified:
1. `test_alembic_migrations_clean_lifecycle`: Clean `upgrade head` -> `downgrade base` -> `upgrade head`.
2. `test_slice_4a_assignee_index_migration_lifecycle`: Step-by-step verification of `f5a6b7c8d9e0` index definition (`['task_id', 'membership_id']`), `a6b7c8d9e0f1` upgrade (`['task_id']`), downgrade revert (`['task_id', 'membership_id']`), and re-upgrade to `head`.

### 5.3 Python Virtual Environment Dependency Check
```powershell
backend\.venv\Scripts\python.exe -m pip check
```
**Result:** `No broken requirements found.`

### 5.4 Frontend Vitest Suite
```powershell
npm --prefix frontend test -- --run
```
**Result:** `2 passed in 1.06s` (100% test pass rate).

### 5.5 Frontend Production Build
```powershell
npm --prefix frontend run build
```
**Result:** `tsc -b && vite build` succeeded in 109ms with zero errors.

### 5.6 Git Whitespace & Formatting Check
```powershell
git diff --check
```
**Result:** Clean; zero whitespace or line-ending errors.

---

## 6. Repository State & Inventory

### 6.1 Modified Files
- `backend/alembic/versions/f5a6b7c8d9e0_slice_4a_task_management_and_operational_blockers.py`: Restored `uq_task_assignee_active` columns to `['task_id', 'membership_id']`.
- `backend/tests/test_migrations.py`: Added `test_slice_4a_assignee_index_migration_lifecycle`.
- `docs/implementation/IMPLEMENTATION_STATUS.md`: Updated migration chain to include `a6b7c8d9e0f1` and recorded Prompt 15 closure.

### 6.2 Added Files
- `backend/alembic/versions/a6b7c8d9e0f1_slice_4a_single_active_task_assignee_index.py`: Additive migration for `uq_task_assignee_active` single-column index.
- `docs/implementation/SLICE_4A_ASSIGNMENT_POLICY_AND_MIGRATION_REVIEW.md`: This review report.

### 6.3 Git Working Tree
- **Branch:** `main`
- **Head Commit:** `7caf0bf`
- **Staged Changes:** None (`git add` was NOT executed).
- **Commits Created:** None (`git commit` was NOT executed).
- **Slice 4B Implementation:** Strictly zero REST APIs, routers, schemas, or UI screens introduced.

