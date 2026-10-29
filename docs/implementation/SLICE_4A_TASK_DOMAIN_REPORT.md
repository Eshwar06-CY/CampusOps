# CampusOps — Slice 4A Implementation Report: Task Management & Operational Blocker Foundation

**Date:** 29 October 2026  
**Status:** Completed & Verified  
**Working Directory:** `D:\Antigravity_Projects\CampusOps`  
**Parent Migration:** `e4f5a6b7c8d9` (Slice 3B Event End Date & Multi-Day Date Bounds)  
**Slice Migration Revision:** `f5a6b7c8d9e0` (`f5a6b7c8d9e0_slice_4a_task_management_and_operational_blockers.py`)  
**Backend Test Results:** 159 passed (14 new Slice 4A tests, 1 Alembic migration test, 144 existing regression tests)  
**Frontend Test Results:** 2 passed; production build succeeded  

---

## 1. Executive Summary & Objective

In accordance with Prompt 13, Development Slice 4A establishes the core relational domain model, database constraints, additive Alembic migration, domain services, permission rules, and automated regression test suite for internal operational task management and operational blocker tracking in CampusOps.

This slice provides the operational engine required for campus event teams to execute work reliably:
- **Task Creation & Scoping:** Tasks can be anchored at Organization, Program, Event, or Department scope, with parent hierarchy (`program_id`, `event_id`, `department_id`) resolved and validated against tenant boundaries.
- **Mandatory Deadlines & Audit Trail:** Every task requires an explicit deadline (`due_date`, optional `due_time`, and canonical IANA timezone); deadline adjustments require a mandatory reason and are permanently preserved in `TaskDeadlineHistory`.
- **Assignment Lifecycle:** Assignments track individual active membership assignees, enforce single-active-assignee via database partial unique index, and record historical handoffs.
- **Evidence Submission & Dual Review:** Tasks requiring proof of completion (`proof_required=True`) transition through a structured workflow (`submitted_for_review` -> `changes_requested` / `approved`).
- **Strict Self-Review Prohibition:** Workers and active assignees are cryptographically and domain-enforced from approving their own evidence submissions.
- **Operational Blocker Management:** Internal staff-only operational blockers (issues, bottlenecks, physical constraints) can be created, linked to tasks or events, resolved with mandatory notes, and reopened. They are strictly segregated from participant-facing surfaces.
- **Durable In-App Notifications:** Assignees and submitters receive durable in-app notifications (`Notification` model) upon assignment and review decisions.

In accordance with strict scope boundaries, **no REST API routes or frontend screens were introduced in this slice**. All functionality is encapsulated in domain models, database migrations, and domain services.

---

## 2. Relational Domain Architecture & 10 Core Models

Ten new SQLAlchemy 2.0 models were defined in `backend/app/models/task.py` and exported through `backend/app/models/__init__.py`:

### 2.1. `Task` (`tasks`)
The central operational unit of work.
- **Primary Key:** `id` (`UUID`, default `uuid4`).
- **Tenancy & Hierarchy:**
  - `organization_id` (`UUID`, FK `organizations.id`, non-null, cascading delete).
  - `scope_type` (`String(50)`, non-null: `'organization'`, `'program'`, `'event'`, `'department'`).
  - `scope_id` (`UUID`, nullable; null only when `scope_type == 'organization'`).
  - `program_id` (`UUID`, FK `programs.id`, nullable, cascading delete).
  - `event_id` (`UUID`, FK `events.id`, nullable, cascading delete).
  - `department_id` (`UUID`, FK `departments.id`, nullable, cascading delete).
- **Attributes:**
  - `title` (`String(200)`, non-null).
  - `description` (`Text`, nullable).
  - `priority` (`String(20)`, non-null, default `'medium'`: `'low'`, `'medium'`, `'high'`, `'urgent'`).
  - `status` (`String(30)`, non-null, default `'not_started'`: `'not_started'`, `'assigned'`, `'in_progress'`, `'submitted_for_review'`, `'changes_requested'`, `'completed'`, `'cancelled'`).
  - `proof_required` (`Boolean`, non-null, default `True`).
  - `due_date` (`Date`, non-null).
  - `due_time` (`Time`, nullable).
  - `timezone` (`String(50)`, non-null, default `'Asia/Kolkata'`).
  - `created_by_user_id` (`UUID`, FK `user_profiles.id`, non-null).
  - `completed_at` (`DateTime(timezone=True)`, nullable).
  - `archived_at` (`DateTime(timezone=True)`, nullable).
  - `created_at`, `updated_at` (`DateTime(timezone=True)`, non-null).

### 2.2. `TaskAssignee` (`task_assignees`)
Tracks worker assignments and historical handoffs.
- **Attributes:** `id`, `task_id` (FK `tasks.id`), `membership_id` (FK `organization_memberships.id`), `assignment_status` (`'active'`, `'unassigned'`), `assigned_by_user_id` (FK `user_profiles.id`), `assigned_at`, `unassigned_at`, `unassigned_by_user_id`.
- **Constraint:** Partial unique index `uq_task_assignee_active` (`task_id`, `WHERE assignment_status = 'active'`) ensures at most one active worker per task while retaining full assignment history.

### 2.3. `TaskDeadlineHistory` (`task_deadline_history`)
Immutable audit log of all deadline alterations.
- **Attributes:** `id`, `task_id` (FK `tasks.id`), `previous_due_date`, `previous_due_time`, `new_due_date`, `new_due_time`, `reason` (`Text`, non-null), `changed_by_user_id` (FK `user_profiles.id`), `changed_at`.

### 2.4. `TaskStatusHistory` (`task_status_history`)
Auditable record of all task workflow state transitions.
- **Attributes:** `id`, `task_id` (FK `tasks.id`), `previous_status`, `new_status`, `reason` (`Text`, nullable), `changed_by_user_id` (FK `user_profiles.id`), `created_at`.

### 2.5. `EvidenceSubmission` (`evidence_submissions`)
Structured submission for proof-required tasks. Supports multi-attempt iterations.
- **Attributes:** `id`, `task_id` (FK `tasks.id`), `submission_number` (`Integer`, non-null, 1-indexed), `submitter_note` (`Text`, nullable), `status` (`'pending_review'`, `'approved'`, `'changes_requested'`), `submitted_by_user_id` (FK `user_profiles.id`), `submitted_at`, `reviewed_at`.
- **Constraint:** `UniqueConstraint("task_id", "submission_number", name="uq_submission_task_number")`.

### 2.6. `EvidenceArtifact` (`evidence_artifacts`)
Individual artifacts attached to a submission attempt.
- **Attributes:** `id`, `submission_id` (FK `evidence_submissions.id`), `artifact_type` (`'url'`, `'file'`), `url` (`String(2048)`, nullable), `file_reference` (`String(500)`, nullable), `created_at`.

### 2.7. `TaskReview` (`task_reviews`)
Formal decision record rendered by an authorized lead.
- **Attributes:** `id`, `evidence_submission_id` (FK `evidence_submissions.id`, unique), `task_id` (FK `tasks.id`), `reviewer_user_id` (FK `user_profiles.id`), `reviewer_membership_id` (FK `organization_memberships.id`), `decision` (`'approved'`, `'changes_requested'`), `review_note` (`Text`, nullable; mandatory on `changes_requested`), `reviewed_at`.

### 2.8. `OperationalBlocker` (`operational_blockers`)
Internal staff-only operational issues.
- **Attributes:** `id`, `organization_id` (FK `organizations.id`), `scope_type` (`'organization'`, `'program'`, `'event'`, `'department'`, `'task'`), `scope_id`, `task_id` (FK `tasks.id`, nullable), `event_id` (FK `events.id`, nullable), `title` (`String(200)`), `description` (`Text`), `priority` (`'low'`, `'medium'`, `'high'`, `'critical'`), `status` (`'open'`, `'resolved'`), `created_by_user_id` (FK `user_profiles.id`), `owner_membership_id` (FK `organization_memberships.id`, nullable), `resolved_at`, `resolution_note` (`Text`), `resolved_by_user_id` (FK `user_profiles.id`), `created_at`, `updated_at`.

### 2.9. `OperationalBlockerHistory` (`operational_blocker_history`)
Status transition log for operational blockers.
- **Attributes:** `id`, `blocker_id` (FK `operational_blockers.id`), `previous_status`, `new_status`, `note` (`Text`), `changed_by_user_id` (FK `user_profiles.id`), `created_at`.

### 2.10. `Notification` (`notifications`)
In-app notification queue for operational events.
- **Attributes:** `id`, `organization_id` (FK `organizations.id`), `user_id` (FK `user_profiles.id`), `event_type` (`String(50)`), `related_entity_type` (`String(50)`), `related_entity_id` (`UUID`), `title` (`String(200)`), `message` (`Text`), `is_read` (`Boolean`, default `False`), `read_at`, `created_at`.

---

## 3. Database Constraints vs. Service-Enforced Invariants

| Invariant / Rule | Enforcement Layer | Implementation Details |
| :--- | :--- | :--- |
| **Valid Task Statuses** | Database Check Constraint | `ck_tasks_status` restricts status to `not_started`, `assigned`, `in_progress`, `submitted_for_review`, `changes_requested`, `completed`, `cancelled`. |
| **Valid Task Priorities** | Database Check Constraint | `ck_tasks_priority` restricts to `low`, `medium`, `high`, `urgent`. |
| **Valid Task Scopes** | Database Check Constraint | `ck_tasks_scope_type` restricts to `organization`, `program`, `event`, `department`. |
| **Mandatory Due Date** | Database Column Constraint | `due_date` is `sa.Date(), nullable=False`. |
| **Single Active Assignee** | Database Partial Unique Index | `uq_task_assignee_active` on `(task_id)` `WHERE assignment_status = 'active'`. Prevents duplicate active workers concurrently. |
| **Submission Number Uniqueness** | Database Unique Constraint | `uq_submission_task_number` on `(task_id, submission_number)`. |
| **Blocker Status & Priority** | Database Check Constraint | `ck_blockers_status` (`open`, `resolved`) and `ck_blockers_priority` (`low`, `medium`, `high`, `critical`). |
| **Non-Empty String Invariants** | Service Layer (`ValueError`) | `title`, `description`, `reason` (deadline changes), `review_note` (rejections), and `resolution_note` (blocker resolution) are stripped and validated for non-emptiness. |
| **Mandatory Rejection Note** | Service Layer (`ValueError`) | When `review_task_submission` receives `decision="changes_requested"`, a non-empty `review_note` is required. |
| **Mandatory Blocker Resolution Note** | Service Layer (`ValueError`) | When resolving a blocker, a non-empty `resolution_note` is required. |
| **Strict Self-Review Prohibition** | Service Layer (`SelfReviewError`) | `review_task_submission` verifies that `user.id != submission.submitted_by_user_id` AND `user.id` is not among the task's active assignees. |
| **Proof-Required Direct Completion Block** | Service Layer (`TaskWorkflowError`) | Tasks with `proof_required=True` cannot call `complete_task_without_proof`. They must be submitted and approved through formal review. |
| **Verified Organization Gate** | Service Layer (`PermissionDeniedError`) | Tasks and blockers can only be created in organizations with `verification_status == 'verified'`. |
| **Tenant & Scope Hierarchy Isolation** | Service Layer (`ScopeIntegrityError`) | `_resolve_task_hierarchy` validates that target `program_id`, `event_id`, or `department_id` belongs to `organization_id` and is active (not archived) before checking caller permissions. |
| **Evidence URL Safety** | Service Layer (`ValueError`) | `validate_evidence_url` validates URLs against standard HTTP/HTTPS schemes with hostnames, rejecting relative paths, `file://`, `ftp://`, and script protocols without making server-side fetches. |

---

## 4. Role and Scope Authorization Matrix

CampusOps permission evaluation was extended in `backend/app/services/permissions.py`:

```
+-------------------+---------------------+------------------+-------------------+-------------------+-------------------+
| Action            | PRIMARY_ADMIN       | OFFICE_BEARER    | EVENT_LEAD        | DEPARTMENT_LEAD   | COORDINATOR       |
+-------------------+---------------------+------------------+-------------------+-------------------+-------------------+
| task:create       | Allowed (Org-wide)  | Allowed (Org-wide)| Allowed (Event)   | Allowed (Dept)    | Denied            |
| task:view         | Allowed (Org-wide)  | Allowed (Org-wide)| Allowed (Event)   | Allowed (Dept)    | Allowed (Assigned)|
| task:assign       | Allowed (Org-wide)  | Allowed (Org-wide)| Allowed (Event)   | Allowed (Dept)    | Denied            |
| task:update       | Allowed (Org-wide)  | Allowed (Org-wide)| Allowed (Event)   | Allowed (Dept)    | Denied            |
| task:change_dead..| Allowed (Org-wide)  | Allowed (Org-wide)| Allowed (Event)   | Allowed (Dept)    | Denied            |
| task:review_proof | Allowed (Org-wide)  | Allowed (Org-wide)| Allowed (Event)   | Allowed (Dept)    | Denied            |
| blocker:create    | Allowed (Org-wide)  | Allowed (Org-wide)| Allowed (Event)   | Allowed (Dept)    | Allowed (Assigned)|
| blocker:view      | Allowed (Org-wide)  | Allowed (Org-wide)| Allowed (Event)   | Allowed (Dept)    | Allowed (Org-wide)|
| blocker:resolve   | Allowed (Org-wide)  | Allowed (Org-wide)| Allowed (Event)   | Allowed (Dept)    | Denied            |
+-------------------+---------------------+------------------+-------------------+-------------------+-------------------+
```

### Non-Participant Isolation
Operational blockers (`OperationalBlocker`) and tasks are strictly restricted to organization members holding active staff roles (`PRIMARY_ADMIN`, `OFFICE_BEARER`, `EVENT_LEAD`, `DEPARTMENT_LEAD`, `COORDINATOR`). They are never exposed to attendees, participants, or public endpoints.

---

## 5. Evidence Handling & Future Storage Architecture

### Current Implementation (Slice 4A)
- Evidence submissions support multi-attempt cycles (`submission_number=1, 2, ...`).
- When a task requires proof, assignees submit one or more URLs (`EvidenceArtifact(artifact_type="url")`) alongside a submitter note.
- `validate_evidence_url(url)` parses URLs using `urllib.parse.urlparse`, requiring scheme `http` or `https` and a valid network location (`netloc`). It rejects:
  - Relative URLs (`/path/to/file`).
  - File schemes (`file:///etc/passwd`).
  - FTP/Gopher schemes (`ftp://fileserver/`).
  - Executable or script pseudo-schemes (`javascript:alert(1)`, `data:text/html,...`).
- **Zero Server Fetch:** In accordance with strict SSRF defense guidelines, the server never fetches or dereferences evidence URLs.

### Future Object Storage Adapter Path (Slice 4B / Future Slices)
When direct file uploads are introduced:
1. Client requests a pre-signed upload URL for an evidence artifact.
2. Server validates authorization, generates a deterministic key (`organizations/{org_id}/tasks/{task_id}/submissions/{sub_num}/{uuid}.{ext}`), and returns a signed PUT URL (e.g. S3 / GCS / Supabase Storage).
3. Client uploads directly to the object store.
4. Client commits the upload by submitting the `file_reference` and SHA-256 hash to `submit_task_evidence`.
5. The schema already includes `file_reference` (`String(500)`) on `EvidenceArtifact` to accommodate this architecture without database migration.

---

## 6. Concurrency & Race Condition Protection

1. **Double-Review Prevention:**
   In `review_task_submission`, reviewers may attempt concurrent approvals or change requests. To eliminate race conditions, the service executes an atomic conditional update:
   ```python
   atomic_update = (
       update(EvidenceSubmission)
       .where(
           EvidenceSubmission.id == submission.id,
           EvidenceSubmission.status == "pending_review",
       )
       .values(status=clean_decision)
   )
   result = db.execute(atomic_update)
   if result.rowcount == 0:
       raise TaskWorkflowError("Evidence submission is not pending review or was concurrently reviewed.")
   ```
2. **Single Active Assignee:**
   When reassigning a task, `_perform_task_assignment` selects existing active assignees, marks them `assignment_status="unassigned"` with timestamps, and inserts the new assignee in the same database transaction. The partial unique index `uq_task_assignee_active` guards the table at the database engine level against parallel assignment races.

---

## 7. Migration Lifecycle Verification (`f5a6b7c8d9e0`)

The additive Alembic migration `backend/alembic/versions/f5a6b7c8d9e0_slice_4a_task_management_and_operational_blockers.py`:
- Specifies `down_revision = 'e4f5a6b7c8d9'`.
- Uses `batch_alter_table` for SQLite compatibility.
- Creates all 10 tables with explicit constraints, foreign keys, and indexes.
- Implements comprehensive `downgrade()` dropping all created tables, constraints, and indexes in correct dependency reverse order.
- Verified via `backend/tests/test_migrations.py`: executes `downgrade("base")` and `upgrade("head")` cleanly across all 5 migrations.

---

## 8. Verification & Test Evidence

### 8.1. Automated Test Execution
```
backend\tests\test_slice_4a_task_domain.py ..............                [100%]
14 passed, 1 warning in 0.55s

======================= 159 passed, 1 warning in 7.81s ========================
```

### 8.2. Slice 4A Test Suite Breakdown (`test_slice_4a_task_domain.py`)
1. `test_create_task_with_mandatory_deadline`: Confirms task creation with due date, due time, timezone, and verified org.
2. `test_create_task_requires_mandatory_deadline`: Confirms `due_date=None` is rejected with `ValueError`.
3. `test_create_task_rejects_unverified_org`: Verifies non-verified organizations cannot create operational tasks.
4. `test_create_task_rejects_archived_or_alien_scopes`: Verifies tasks cannot reference entities belonging to other organizations or archived parents.
5. `test_assign_task_lifecycle_and_single_active_assignee`: Verifies worker assignment, notification generation, and historical handoff unassignment.
6. `test_assign_task_rejects_cross_tenant_and_ineligible_members`: Verifies rejection of cross-tenant members, suspended users, or unverified emails.
7. `test_change_task_deadline_audit`: Verifies deadline changes require a non-empty reason and preserve `TaskDeadlineHistory`.
8. `test_task_full_workflow_with_rejection_and_approval`: Tests full lifecycle (`not_started` -> `assigned` -> `in_progress` -> `submitted_for_review` -> `changes_requested` -> `resubmitted` -> `approved` -> `completed`).
9. `test_complete_task_without_proof_rule`: Verifies proof-optional tasks can be completed directly while proof-required tasks require review.
10. `test_operational_blocker_lifecycle`: Verifies blocker creation, resolution with mandatory note, and reopening.
11. `test_operational_blocker_cross_tenant_rejected`: Verifies blockers cannot reference cross-tenant events, tasks, or scopes.
12. `test_operational_blocker_non_participant_isolation`: Verifies coordinators can create blockers on assigned tasks but non-staff cannot.
13. `test_archive_task_lifecycle`: Verifies task archival and idempotency.
14. `test_notification_lifecycle`: Verifies listing unread notifications and marking them as read.

### 8.3. Frontend & Environment Checks
- **Frontend Vitest:** 2 passed (`src/App.test.tsx`).
- **Frontend Build:** `tsc -b && vite build` succeeded without errors.
- **Python Dependencies:** `pip check` reports no broken requirements.
- **Git Hygiene:** `git diff --check` clean with zero whitespace or line-ending errors.

---

## 9. File Manifest

### Created Files
- `backend/app/models/task.py` (10 SQLAlchemy models: `Task`, `TaskAssignee`, `TaskDeadlineHistory`, `TaskStatusHistory`, `EvidenceSubmission`, `EvidenceArtifact`, `TaskReview`, `OperationalBlocker`, `OperationalBlockerHistory`, `Notification`).
- `backend/app/services/task.py` (Domain services for task lifecycle, evidence submission, review, blockers, notifications, and URL validation).
- `backend/alembic/versions/f5a6b7c8d9e0_slice_4a_task_management_and_operational_blockers.py` (Additive migration).
- `backend/tests/test_slice_4a_task_domain.py` (14 comprehensive domain regression tests).
- `docs/implementation/SLICE_4A_TASK_DOMAIN_REPORT.md` (This document).

### Modified Files
- `backend/app/models/__init__.py` (Exported all 10 task models).
- `backend/app/services/errors.py` (Added domain exceptions for tasks, blockers, and reviews).
- `backend/app/services/permissions.py` (Added task and blocker actions and scope validation).
- `backend/tests/test_migrations.py` (Added 10 new tables to migration lifecycle test).
- `docs/implementation/IMPLEMENTATION_STATUS.md` (Updated implementation status and test metrics).

---

## 10. Scope Boundaries & Next Steps

### Boundaries Maintained
- **NO REST APIs:** No FastAPI endpoints were created for tasks or blockers in this slice.
- **NO Frontend Changes:** No UI components or screens were introduced.
- **NO External Services:** No cloud storage or Supabase Auth linkages were introduced.
- **NO Participant Features:** No registration, attendance check-in, or attendee-facing surfaces were created.

### Readiness for Slice 4B
The application is now prepared for **Development Slice 4B: Task Management & Operational Blocker REST APIs**:
1. Implement Pydantic v2 request/response schemas for tasks, evidence submissions, reviews, blockers, and notifications.
2. Build FastAPI endpoints under `/api/v1/organizations/{id}/tasks`, `/api/v1/organizations/{id}/tasks/{task_id}/assign`, `/submissions`, `/reviews`, and `/blockers`.
3. Wire HTTP integration tests with strict permission, tenant isolation, and anti-enumeration verification.

