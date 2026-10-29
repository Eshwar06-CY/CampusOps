import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Department, Event, Program
from app.models.organization import Organization, OrganizationMembership
from app.models.role import PlatformAdmin, RoleAssignment
from app.models.user import UserProfile
from app.services.errors import PermissionDeniedError

# Permission action constants
ACTION_VIEW_ORG_PROFILE = "org:view_profile"
ACTION_EDIT_ORG_PROFILE = "org:edit_profile"
ACTION_VERIFY_ORG = "org:verify"
ACTION_INVITE_MEMBER = "org:invite_member"
ACTION_MANAGE_ROLES = "org:manage_roles"
ACTION_CREATE_EVENT = "org:create_event"
ACTION_VIEW_DEPARTMENT = "department:view"
ACTION_MANAGE_DEPARTMENT = "department:manage"

# Slice 4A: Task and Operational Blocker action constants
ACTION_CREATE_TASK = "task:create"
ACTION_VIEW_TASK = "task:view"
ACTION_ASSIGN_TASK = "task:assign"
ACTION_UPDATE_TASK = "task:update"
ACTION_CHANGE_DEADLINE = "task:change_deadline"
ACTION_SUBMIT_PROOF = "task:submit_proof"
ACTION_REVIEW_PROOF = "task:review_proof"

ACTION_CREATE_BLOCKER = "blocker:create"
ACTION_VIEW_BLOCKER = "blocker:view"
ACTION_RESOLVE_BLOCKER = "blocker:resolve"


def is_active_platform_admin(db: Session, user_id: uuid.UUID) -> bool:
    """Check if a user is an active platform administrator with an active, verified user account."""
    user = db.get(UserProfile, user_id)
    if not user or user.account_status != "active" or user.email_verified_at is None:
        return False

    stmt = select(PlatformAdmin).where(
        PlatformAdmin.user_id == user_id,
        PlatformAdmin.is_active == True,
        PlatformAdmin.revoked_at == None,
    )
    admin = db.execute(stmt).scalar_one_or_none()
    return admin is not None


def validate_target_resource_scope(
    db: Session,
    organization_id: uuid.UUID,
    scope_type: str,
    scope_id: Optional[uuid.UUID],
) -> bool:
    """
    Validates that a target resource scope is structurally valid and bound to the organization.
    In Slice 3A, verifies real database records for programs, events, and departments,
    ensuring non-leakage, tenant ownership, and non-archived parent hierarchy.
    """
    if scope_type == "organization":
        return scope_id is None or scope_id == organization_id

    if scope_id is None:
        return False

    if scope_type == "program":
        prog = db.get(Program, scope_id)
        return (
            prog is not None
            and prog.archived_at is None
            and prog.organization_id == organization_id
        )

    if scope_type == "event":
        ev = db.get(Event, scope_id)
        if not ev or ev.archived_at is not None or ev.organization_id != organization_id:
            return False
        if ev.program_id is not None:
            prog = db.get(Program, ev.program_id)
            if not prog or prog.archived_at is not None:
                return False
        return True

    if scope_type == "department":
        dept = db.get(Department, scope_id)
        if not dept or dept.archived_at is not None or dept.organization_id != organization_id:
            return False
        if dept.program_id is not None:
            prog = db.get(Program, dept.program_id)
            if not prog or prog.archived_at is not None:
                return False
        if dept.standalone_event_id is not None:
            ev = db.get(Event, dept.standalone_event_id)
            if not ev or ev.archived_at is not None:
                return False
        return True

    if scope_type == "task":
        from app.models.task import Task
        task = db.get(Task, scope_id)
        if not task or task.archived_at is not None or task.organization_id != organization_id:
            return False
        if task.program_id is not None:
            prog = db.get(Program, task.program_id)
            if not prog or prog.archived_at is not None:
                return False
        if task.event_id is not None:
            ev = db.get(Event, task.event_id)
            if not ev or ev.archived_at is not None:
                return False
            if ev.program_id is not None:
                prog = db.get(Program, ev.program_id)
                if not prog or prog.archived_at is not None:
                    return False
        if task.department_id is not None:
            dept = db.get(Department, task.department_id)
            if not dept or dept.archived_at is not None:
                return False
            if dept.program_id is not None:
                prog = db.get(Program, dept.program_id)
                if not prog or prog.archived_at is not None:
                    return False
            if dept.standalone_event_id is not None:
                ev = db.get(Event, dept.standalone_event_id)
                if not ev or ev.archived_at is not None:
                    return False
        return True

    return False


def has_active_primary_admin(db: Session, organization_id: uuid.UUID) -> bool:
    """Checks whether an organization already has an active Primary Workspace Administrator."""
    stmt = (
        select(RoleAssignment)
        .join(OrganizationMembership, RoleAssignment.membership_id == OrganizationMembership.id)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.membership_status == "active",
            OrganizationMembership.removed_at == None,
            RoleAssignment.role_name == "PRIMARY_ADMIN",
            RoleAssignment.scope_type == "organization",
            RoleAssignment.revoked_at == None,
        )
    )
    admin_assignment = db.execute(stmt).scalar_one_or_none()
    return admin_assignment is not None


def can_perform(
    db: Session,
    user: UserProfile,
    action: str,
    organization_id: Optional[uuid.UUID] = None,
    scope_type: str = "organization",
    scope_id: Optional[uuid.UUID] = None,
) -> bool:
    """
    Centralized deny-by-default permission evaluation engine.
    Enforces user account status, email verification, tenant isolation,
    organization verification status, and strict scope matching.
    """
    # 0. User identity integrity check: must exist, be active, and have verified email
    if not user or user.account_status != "active" or user.email_verified_at is None:
        return False

    # 1. Platform-level actions (e.g. verifying an organization)
    if action == ACTION_VERIFY_ORG:
        return is_active_platform_admin(db, user.id)

    # All organization-scoped operations require an organization_id
    if organization_id is None:
        return False

    # Target resource scope validation
    if not validate_target_resource_scope(db, organization_id, scope_type, scope_id):
        return False

    # 2. Check organization exists
    org = db.get(Organization, organization_id)
    if not org or org.archived_at is not None:
        return False

    # Active platform administrators have platform-wide permission to view organization profiles
    if action == ACTION_VIEW_ORG_PROFILE and is_active_platform_admin(db, user.id):
        return True

    # 3. Check user has an active membership in this organization (tenant boundary)
    membership_stmt = select(OrganizationMembership).where(
        OrganizationMembership.organization_id == organization_id,
        OrganizationMembership.user_id == user.id,
        OrganizationMembership.membership_status == "active",
        OrganizationMembership.removed_at == None,
    )
    membership = db.execute(membership_stmt).scalar_one_or_none()
    if not membership:
        return False

    # 4. Check active role assignments for this membership
    roles_stmt = select(RoleAssignment).where(
        RoleAssignment.membership_id == membership.id,
        RoleAssignment.revoked_at == None,
    )
    role_assignments = list(db.execute(roles_stmt).scalars().all())
    if not role_assignments:
        return False

    # 5. Evaluate permissions based on role and organization verification status
    is_verified = org.verification_status == "verified"

    for ra in role_assignments:
        role = ra.role_name
        r_scope_type = ra.scope_type
        r_scope_id = ra.scope_id

        # Any active role assignment in the organization permits viewing the workspace profile
        if action == ACTION_VIEW_ORG_PROFILE:
            return True

        # Organization-level scope evaluation
        if r_scope_type == "organization":
            # An organization-level role cannot have an alien scope_id
            if r_scope_id is not None and r_scope_id != organization_id:
                continue

            if role == "PRIMARY_ADMIN":
                # Primary admin can always view and edit the org profile
                if action in (ACTION_VIEW_ORG_PROFILE, ACTION_EDIT_ORG_PROFILE):
                    return True
                # Privileged actions (invitations, event creation, role management, tasks, blockers) require verified org
                if not is_verified:
                    continue  # Restricted while pending_verification per FPC-02 / FPC-03

                if action in (
                    ACTION_INVITE_MEMBER,
                    ACTION_MANAGE_ROLES,
                    ACTION_CREATE_EVENT,
                    ACTION_CREATE_TASK,
                    ACTION_VIEW_TASK,
                    ACTION_ASSIGN_TASK,
                    ACTION_UPDATE_TASK,
                    ACTION_CHANGE_DEADLINE,
                    ACTION_REVIEW_PROOF,
                    ACTION_SUBMIT_PROOF,
                    ACTION_CREATE_BLOCKER,
                    ACTION_VIEW_BLOCKER,
                    ACTION_RESOLVE_BLOCKER,
                ):
                    return True

            elif role == "OFFICE_BEARER":
                if not is_verified:
                    if action == ACTION_VIEW_ORG_PROFILE:
                        return True
                    continue

                if action in (
                    ACTION_VIEW_ORG_PROFILE,
                    ACTION_CREATE_EVENT,
                    ACTION_INVITE_MEMBER,
                    ACTION_MANAGE_ROLES,
                    ACTION_CREATE_TASK,
                    ACTION_VIEW_TASK,
                    ACTION_ASSIGN_TASK,
                    ACTION_UPDATE_TASK,
                    ACTION_CHANGE_DEADLINE,
                    ACTION_REVIEW_PROOF,
                    ACTION_SUBMIT_PROOF,
                    ACTION_CREATE_BLOCKER,
                    ACTION_VIEW_BLOCKER,
                    ACTION_RESOLVE_BLOCKER,
                ):
                    return True

            elif role == "COORDINATOR":
                if is_verified:
                    if action in (ACTION_VIEW_TASK, ACTION_VIEW_BLOCKER):
                        return True

        # Program-level scope evaluation
        elif r_scope_type == "program":
            if r_scope_id is None:
                continue
            is_match = False
            if scope_type == "program" and r_scope_id == scope_id:
                is_match = True
            elif scope_type == "task" and scope_id is not None:
                from app.models.task import Task
                t = db.get(Task, scope_id)
                if t and t.program_id == r_scope_id:
                    is_match = True

            if is_match:
                if role in ("OFFICE_BEARER", "EVENT_LEAD"):
                    if action in (
                        ACTION_CREATE_TASK,
                        ACTION_VIEW_TASK,
                        ACTION_ASSIGN_TASK,
                        ACTION_UPDATE_TASK,
                        ACTION_CHANGE_DEADLINE,
                        ACTION_REVIEW_PROOF,
                        ACTION_SUBMIT_PROOF,
                        ACTION_CREATE_BLOCKER,
                        ACTION_VIEW_BLOCKER,
                        ACTION_RESOLVE_BLOCKER,
                    ):
                        return True
                elif role == "COORDINATOR":
                    if action in (
                        ACTION_VIEW_TASK,
                        ACTION_SUBMIT_PROOF,
                        ACTION_CREATE_BLOCKER,
                        ACTION_VIEW_BLOCKER,
                    ):
                        return True

        # Department-level scope evaluation (strict scope boundary, no leakage)
        elif r_scope_type == "department":
            if r_scope_id is None:
                continue
            is_match = False
            if scope_type == "department" and r_scope_id == scope_id:
                is_match = True
            elif scope_type == "task" and scope_id is not None:
                from app.models.task import Task
                t = db.get(Task, scope_id)
                if t and t.department_id == r_scope_id:
                    is_match = True

            if is_match:
                if role == "DEPARTMENT_LEAD":
                    if action in (
                        ACTION_VIEW_DEPARTMENT,
                        ACTION_MANAGE_DEPARTMENT,
                        ACTION_CREATE_TASK,
                        ACTION_VIEW_TASK,
                        ACTION_ASSIGN_TASK,
                        ACTION_UPDATE_TASK,
                        ACTION_CHANGE_DEADLINE,
                        ACTION_REVIEW_PROOF,
                        ACTION_SUBMIT_PROOF,
                        ACTION_CREATE_BLOCKER,
                        ACTION_VIEW_BLOCKER,
                        ACTION_RESOLVE_BLOCKER,
                    ):
                        return True
                elif role == "COORDINATOR":
                    if action in (
                        ACTION_VIEW_DEPARTMENT,
                        ACTION_VIEW_TASK,
                        ACTION_SUBMIT_PROOF,
                        ACTION_CREATE_BLOCKER,
                        ACTION_VIEW_BLOCKER,
                    ):
                        return True

        # Event-level scope evaluation (strict scope boundary, no leakage)
        elif r_scope_type == "event":
            if r_scope_id is None:
                continue
            is_match = False
            if scope_type == "event" and r_scope_id == scope_id:
                is_match = True
            elif scope_type == "task" and scope_id is not None:
                from app.models.task import Task
                t = db.get(Task, scope_id)
                if t and t.event_id == r_scope_id:
                    is_match = True

            if is_match:
                if role == "EVENT_LEAD":
                    if action in (
                        ACTION_CREATE_EVENT,
                        ACTION_CREATE_TASK,
                        ACTION_VIEW_TASK,
                        ACTION_ASSIGN_TASK,
                        ACTION_UPDATE_TASK,
                        ACTION_CHANGE_DEADLINE,
                        ACTION_REVIEW_PROOF,
                        ACTION_SUBMIT_PROOF,
                        ACTION_CREATE_BLOCKER,
                        ACTION_VIEW_BLOCKER,
                        ACTION_RESOLVE_BLOCKER,
                    ):
                        return True
                elif role == "COORDINATOR":
                    if action in (
                        ACTION_VIEW_TASK,
                        ACTION_SUBMIT_PROOF,
                        ACTION_CREATE_BLOCKER,
                        ACTION_VIEW_BLOCKER,
                    ):
                        return True

    # 6. Active Task Assignee evaluation (CO-FR-011)
    # An active task assignee is explicitly authorized to view and submit proof on their assigned task
    if scope_type == "task" and scope_id is not None:
        if action in (ACTION_VIEW_TASK, ACTION_SUBMIT_PROOF):
            from app.models.task import Task
            t = db.get(Task, scope_id)
            if t and t.organization_id == organization_id and t.archived_at is None:
                is_active_assignee = any(
                    a.assignment_status == "active"
                    and a.membership
                    and a.membership.user_id == user.id
                    and a.membership.membership_status == "active"
                    for a in t.assignees
                )
                if is_active_assignee:
                    return True

    # Deny by default if no matching grant was satisfied
    return False


def require_permission(
    db: Session,
    user: UserProfile,
    action: str,
    organization_id: Optional[uuid.UUID] = None,
    scope_type: str = "organization",
    scope_id: Optional[uuid.UUID] = None,
) -> None:
    """Enforce permission or raise PermissionDeniedError."""
    if not can_perform(
        db,
        user=user,
        action=action,
        organization_id=organization_id,
        scope_type=scope_type,
        scope_id=scope_id,
    ):
        raise PermissionDeniedError(
            f"User '{user.id}' is denied action '{action}' on scope '{scope_type}:{scope_id}' in org '{organization_id}'"
        )
