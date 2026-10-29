import uuid
import zoneinfo
from datetime import date, datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event import Department, Event, EventLeadAssignment, Program
from app.models.organization import Organization, OrganizationMembership
from app.models.role import RoleAssignment
from app.models.user import UserProfile
from app.services.errors import (
    DepartmentNotFoundError,
    DuplicateEventLeadError,
    EventLeadError,
    EventNotFoundError,
    ProgramNotFoundError,
    ScopeIntegrityError,
)
from app.services.permissions import (
    ACTION_CREATE_EVENT,
    ACTION_MANAGE_ROLES,
    require_permission,
)
from app.services.timezones import is_valid_timezone


def create_program(
    db: Session,
    creator: UserProfile,
    organization_id: uuid.UUID,
    name: str,
    description: Optional[str] = None,
    planned_start_date: Optional[date] = None,
    planned_end_date: Optional[date] = None,
) -> Program:
    """
    Creates a multi-event program umbrella within a verified organization workspace.
    Enforces organization ownership, role permission, and unique name per organization.
    """
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Program name must not be empty.")

    # 1. Authorize: requires verified organization and event creation permission
    require_permission(
        db, user=creator, action=ACTION_CREATE_EVENT, organization_id=organization_id
    )

    # 2. Check name uniqueness within the organization
    if planned_start_date and planned_end_date and planned_end_date < planned_start_date:
        raise ValueError("Planned end date cannot be earlier than planned start date.")

    existing = db.execute(
        select(Program).where(
            Program.organization_id == organization_id,
            Program.name == clean_name,
            Program.archived_at == None,
        )
    ).scalar_one_or_none()
    if existing:
        raise ValueError(f"Program with name '{clean_name}' already exists in this organization.")

    # 3. Create program
    now = datetime.now(timezone.utc)
    program = Program(
        organization_id=organization_id,
        name=clean_name,
        description=description.strip() if description else None,
        planned_start_date=planned_start_date,
        planned_end_date=planned_end_date,
        status="draft",
        created_by_user_id=creator.id,
        created_at=now,
        updated_at=now,
    )
    db.add(program)
    db.commit()
    db.refresh(program)
    return program


def archive_program(
    db: Session,
    user: UserProfile,
    program_id: uuid.UUID,
) -> Program:
    """
    Non-destructively archives a program (D-SLICE3-04).
    Preserves child records and assignments, but marks parent as archived.
    """
    program = db.get(Program, program_id)
    if not program or program.archived_at is not None:
        raise ProgramNotFoundError(f"Program '{program_id}' not found.")

    require_permission(
        db, user=user, action=ACTION_CREATE_EVENT, organization_id=program.organization_id
    )

    program.archived_at = datetime.now(timezone.utc)
    program.status = "archived"
    db.commit()
    db.refresh(program)
    return program


def get_program(
    db: Session,
    program_id: uuid.UUID,
    organization_id: Optional[uuid.UUID] = None,
) -> Program:
    """Retrieves an active program, validating organization tenancy if specified."""
    program = db.get(Program, program_id)
    if not program or program.archived_at is not None:
        raise ProgramNotFoundError(f"Program '{program_id}' not found.")

    if organization_id and program.organization_id != organization_id:
        raise ScopeIntegrityError("Program belongs to a different organization.")

    return program


def list_programs(
    db: Session,
    organization_id: uuid.UUID,
    include_archived: bool = False,
) -> List[Program]:
    """Lists programs for an organization, excluding archived ones by default."""
    stmt = select(Program).where(Program.organization_id == organization_id)
    if not include_archived:
        stmt = stmt.where(Program.archived_at == None)
    stmt = stmt.order_by(Program.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def update_program(
    db: Session,
    user: UserProfile,
    organization_id: uuid.UUID,
    program_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    planned_start_date: Optional[date] = None,
    planned_end_date: Optional[date] = None,
) -> Program:
    """
    Updates program metadata and date ranges.
    Validates name uniqueness within the organization, temporal date order,
    and ensures that existing child events are not violated by new date boundaries.
    """
    program = get_program(db, program_id=program_id, organization_id=organization_id)
    require_permission(
        db, user=user, action=ACTION_CREATE_EVENT, organization_id=organization_id
    )

    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Program name must not be empty.")
        if clean_name != program.name:
            existing = db.execute(
                select(Program).where(
                    Program.organization_id == organization_id,
                    Program.name == clean_name,
                    Program.id != program_id,
                    Program.archived_at == None,
                )
            ).scalar_one_or_none()
            if existing:
                raise ValueError(f"Program with name '{clean_name}' already exists in this organization.")
            program.name = clean_name

    if description is not None:
        program.description = description.strip() if description.strip() else None

    # Temporal range consistency
    new_start = planned_start_date if planned_start_date is not None else program.planned_start_date
    new_end = planned_end_date if planned_end_date is not None else program.planned_end_date
    if new_start and new_end and new_end < new_start:
        raise ValueError("Planned end date cannot be earlier than planned start date.")

    # Child event date bounds consistency (Section 2)
    for child in program.events:
        if child.archived_at is None:
            if new_start and child.event_date and child.event_date < new_start:
                raise ValueError(
                    f"Cannot update program start date to '{new_start}': child event '{child.name}' occurs on '{child.event_date}'."
                )
            child_effective_end = child.event_end_date or child.event_date
            if new_end and child_effective_end and child_effective_end > new_end:
                raise ValueError(
                    f"Cannot update program end date to '{new_end}': child event '{child.name}' ends on '{child_effective_end}'."
                )

    if planned_start_date is not None:
        program.planned_start_date = planned_start_date
    if planned_end_date is not None:
        program.planned_end_date = planned_end_date

    program.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(program)
    return program


def create_event(
    db: Session,
    creator: UserProfile,
    organization_id: uuid.UUID,
    name: str,
    description: Optional[str] = None,
    program_id: Optional[uuid.UUID] = None,
    event_date: Optional[date] = None,
    event_end_date: Optional[date] = None,
    planned_start_time: Optional[datetime] = None,
    planned_end_time: Optional[datetime] = None,
    venue: Optional[str] = None,
    event_format: str = "in_person",
    registration_mode: str = "individual",
    timezone_name: str = "Asia/Kolkata",
) -> Event:
    """
    Creates an event instance.
    - If program_id is None -> Standalone Event (Workflow A)
    - If program_id is provided -> Child Event under Program (Workflow B)
    Enforces D-SLICE3-05 date/time sequencing and parent program date boundaries.
    """
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Event name must not be empty.")

    # Timezone validation
    clean_tz = timezone_name.strip()
    if not is_valid_timezone(clean_tz):
        raise ValueError(f"Invalid timezone identifier: '{clean_tz}'. Must be a valid IANA timezone.")

    # Date ordering validation
    if event_end_date is not None and event_date is None:
        raise ValueError("Event end date cannot be specified without an event start date.")
    if event_date and event_end_date and event_end_date < event_date:
        raise ValueError("Event end date cannot be earlier than event start date.")

    # Time ordering validation
    is_single_day = (event_end_date is None or event_end_date == event_date)
    if is_single_day and planned_start_time and planned_end_time and planned_end_time < planned_start_time:
        raise ValueError("Planned end time cannot be earlier than planned start time for a single-day event.")

    # 1. Authorize: requires verified organization and event creation permission
    require_permission(
        db, user=creator, action=ACTION_CREATE_EVENT, organization_id=organization_id
    )

    # 2. If child event, validate parent program exists, is not archived, and belongs to org
    if program_id is not None:
        parent_program = db.get(Program, program_id)
        if not parent_program or parent_program.archived_at is not None:
            raise ProgramNotFoundError(f"Parent program '{program_id}' not found or is archived.")
        if parent_program.organization_id != organization_id:
            raise ScopeIntegrityError(
                f"Parent program '{program_id}' not found or belongs to a different organization."
            )

        # Validate event dates against parent program date range
        if parent_program.planned_start_date and event_date and event_date < parent_program.planned_start_date:
            raise ValueError(
                f"Event date '{event_date}' cannot be earlier than parent program start date '{parent_program.planned_start_date}'."
            )
        effective_end = event_end_date or event_date
        if parent_program.planned_end_date and effective_end and effective_end > parent_program.planned_end_date:
            raise ValueError(
                f"Event end date '{effective_end}' cannot be later than parent program end date '{parent_program.planned_end_date}'."
            )

    # 3. Create event
    now = datetime.now(timezone.utc)
    event = Event(
        organization_id=organization_id,
        program_id=program_id,
        name=clean_name,
        description=description.strip() if description else None,
        event_date=event_date,
        event_end_date=event_end_date,
        planned_start_time=planned_start_time,
        planned_end_time=planned_end_time,
        venue=venue.strip() if venue else None,
        event_format=event_format,
        registration_mode=registration_mode,
        timezone=clean_tz,
        status="draft",
        created_by_user_id=creator.id,
        created_at=now,
        updated_at=now,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(
    db: Session,
    organization_id: uuid.UUID,
    program_id: Optional[uuid.UUID] = None,
    include_archived: bool = False,
) -> List[Event]:
    """Lists events for an organization, optionally filtered by parent program."""
    stmt = select(Event).where(Event.organization_id == organization_id)
    if not include_archived:
        stmt = stmt.where(Event.archived_at == None)
    if program_id is not None:
        stmt = stmt.where(Event.program_id == program_id)
    stmt = stmt.order_by(Event.event_date.asc(), Event.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def update_event(
    db: Session,
    user: UserProfile,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    venue: Optional[str] = None,
    event_format: Optional[str] = None,
    registration_mode: Optional[str] = None,
    timezone_name: Optional[str] = None,
    event_date: Optional[date] = None,
    event_end_date: Optional[date] = None,
    planned_start_time: Optional[datetime] = None,
    planned_end_time: Optional[datetime] = None,
) -> Event:
    """
    Updates event metadata, timing, venue, and format.
    Parentage (program_id) is immutable (D-SLICE3-03).
    Enforces D-SLICE3-05 date/time constraints and parent program date boundaries.
    """
    event = get_event(db, event_id=event_id, organization_id=organization_id)

    require_permission(
        db,
        user=user,
        action=ACTION_CREATE_EVENT,
        organization_id=organization_id,
        scope_type="event",
        scope_id=event_id,
    )

    if event.archived_at is not None:
        raise EventNotFoundError("Archived event cannot be updated.")

    parent_program = None
    if event.program_id is not None:
        parent_program = db.get(Program, event.program_id)
        if not parent_program or parent_program.archived_at is not None:
            raise ScopeIntegrityError("Parent program is archived or inaccessible.")

    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Event name must not be empty.")
        event.name = clean_name

    if description is not None:
        event.description = description.strip() if description.strip() else None

    if venue is not None:
        event.venue = venue.strip() if venue.strip() else None

    if event_format is not None:
        clean_format = event_format.strip()
        if not clean_format:
            raise ValueError("Event format must not be empty.")
        event.event_format = clean_format

    if registration_mode is not None:
        clean_mode = registration_mode.strip()
        if not clean_mode:
            raise ValueError("Registration mode must not be empty.")
        event.registration_mode = clean_mode

    if timezone_name is not None:
        clean_tz = timezone_name.strip()
        if not is_valid_timezone(clean_tz):
            raise ValueError(f"Invalid timezone identifier: '{clean_tz}'. Must be a valid IANA timezone.")
        event.timezone = clean_tz

    new_date = event_date if event_date is not None else event.event_date
    new_end_date = event_end_date if event_end_date is not None else event.event_end_date
    if new_end_date is not None and new_date is None:
        raise ValueError("Event end date cannot be specified without an event start date.")
    if new_date and new_end_date and new_end_date < new_date:
        raise ValueError("Event end date cannot be earlier than event start date.")

    new_start_time = planned_start_time if planned_start_time is not None else event.planned_start_time
    new_end_time = planned_end_time if planned_end_time is not None else event.planned_end_time

    is_single_day = (new_end_date is None or new_end_date == new_date)
    if is_single_day and new_start_time and new_end_time and new_end_time < new_start_time:
        raise ValueError("Planned end time cannot be earlier than planned start time for a single-day event.")

    if parent_program:
        if parent_program.planned_start_date and new_date and new_date < parent_program.planned_start_date:
            raise ValueError(
                f"Event date '{new_date}' cannot be earlier than parent program start date '{parent_program.planned_start_date}'."
            )
        effective_end = new_end_date or new_date
        if parent_program.planned_end_date and effective_end and effective_end > parent_program.planned_end_date:
            raise ValueError(
                f"Event end date '{effective_end}' cannot be later than parent program end date '{parent_program.planned_end_date}'."
            )

    if event_date is not None:
        event.event_date = event_date
    if event_end_date is not None:
        event.event_end_date = event_end_date
    if planned_start_time is not None:
        event.planned_start_time = planned_start_time
    if planned_end_time is not None:
        event.planned_end_time = planned_end_time

    event.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(event)
    return event


def archive_event(
    db: Session,
    user: UserProfile,
    event_id: uuid.UUID,
) -> Event:
    """Non-destructively archives an event (D-SLICE3-04)."""
    event = db.get(Event, event_id)
    if not event or event.archived_at is not None:
        raise EventNotFoundError(f"Event '{event_id}' not found.")

    require_permission(
        db, user=user, action=ACTION_CREATE_EVENT, organization_id=event.organization_id
    )

    event.archived_at = datetime.now(timezone.utc)
    event.status = "archived"
    db.commit()
    db.refresh(event)
    return event


def get_event(
    db: Session,
    event_id: uuid.UUID,
    organization_id: Optional[uuid.UUID] = None,
) -> Event:
    """Retrieves an active event, validating organization tenancy if specified."""
    event = db.get(Event, event_id)
    if not event or event.archived_at is not None:
        raise EventNotFoundError(f"Event '{event_id}' not found.")

    if organization_id and event.organization_id != organization_id:
        raise ScopeIntegrityError("Event belongs to a different organization.")

    return event


def create_department(
    db: Session,
    creator: UserProfile,
    organization_id: uuid.UUID,
    name: str,
    description: Optional[str] = None,
    program_id: Optional[uuid.UUID] = None,
    standalone_event_id: Optional[uuid.UUID] = None,
) -> Department:
    """
    Creates a functional department.
    Enforces the exclusive parent invariant (ck_departments_exclusive_parent):
    - Multi-event program shared department: program_id is set, standalone_event_id is None (D-SLICE3-01).
    - Standalone event department: standalone_event_id is set, program_id is None.
    Validates parent entity exists, is active, and matches organization_id.
    """
    clean_name = name.strip()
    if not clean_name:
        raise ValueError("Department name must not be empty.")

    # 1. Authorize: requires verified organization and event creation/management permission
    require_permission(
        db, user=creator, action=ACTION_CREATE_EVENT, organization_id=organization_id
    )

    # 2. Enforce exclusive parent rule
    if (program_id is None and standalone_event_id is None) or (
        program_id is not None and standalone_event_id is not None
    ):
        raise ValueError(
            "Department must belong to exactly one parent: either program_id XOR standalone_event_id."
        )

    # 3. Validate parent entity and tenant ownership
    if program_id is not None:
        program = db.get(Program, program_id)
        if not program or program.archived_at is not None:
            raise ProgramNotFoundError(f"Program '{program_id}' not found or is archived.")
        if program.organization_id != organization_id:
            raise ScopeIntegrityError("Parent program belongs to a different organization.")

    if standalone_event_id is not None:
        event = db.get(Event, standalone_event_id)
        if not event or event.archived_at is not None:
            raise EventNotFoundError(f"Event '{standalone_event_id}' not found or is archived.")
        if event.organization_id != organization_id:
            raise ScopeIntegrityError("Parent standalone event belongs to a different organization.")
        # D-SLICE3-01: Child events under a program use shared program departments;
        # standalone departments cannot be attached to a program's child event.
        if event.program_id is not None:
            raise ValueError(
                f"Event '{standalone_event_id}' is a child event in program '{event.program_id}'. "
                "Child events share program departments and cannot own separate departments in this release (D-SLICE3-01)."
            )

    # 4. Create department
    now = datetime.now(timezone.utc)
    department = Department(
        organization_id=organization_id,
        name=clean_name,
        description=description.strip() if description else None,
        program_id=program_id,
        standalone_event_id=standalone_event_id,
        status="active",
        created_by_user_id=creator.id,
        created_at=now,
        updated_at=now,
    )
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


def archive_department(
    db: Session,
    user: UserProfile,
    department_id: uuid.UUID,
) -> Department:
    """Non-destructively archives a department (D-SLICE3-04)."""
    dept = db.get(Department, department_id)
    if not dept or dept.archived_at is not None:
        raise DepartmentNotFoundError(f"Department '{department_id}' not found.")

    require_permission(
        db, user=user, action=ACTION_CREATE_EVENT, organization_id=dept.organization_id
    )

    dept.archived_at = datetime.now(timezone.utc)
    dept.status = "archived"
    db.commit()
    db.refresh(dept)
    return dept


def get_department(
    db: Session,
    department_id: uuid.UUID,
    organization_id: Optional[uuid.UUID] = None,
) -> Department:
    """Retrieves an active department, validating organization tenancy if specified."""
    dept = db.get(Department, department_id)
    if not dept or dept.archived_at is not None:
        raise DepartmentNotFoundError(f"Department '{department_id}' not found.")

    if organization_id and dept.organization_id != organization_id:
        raise ScopeIntegrityError("Department belongs to a different organization.")

    return dept


def list_departments(
    db: Session,
    organization_id: uuid.UUID,
    program_id: Optional[uuid.UUID] = None,
    standalone_event_id: Optional[uuid.UUID] = None,
    include_archived: bool = False,
) -> List[Department]:
    """Lists departments for an organization, optionally filtered by program or standalone event."""
    stmt = select(Department).where(Department.organization_id == organization_id)
    if not include_archived:
        stmt = stmt.where(Department.archived_at == None)
    if program_id is not None:
        stmt = stmt.where(Department.program_id == program_id)
    if standalone_event_id is not None:
        stmt = stmt.where(Department.standalone_event_id == standalone_event_id)
    stmt = stmt.order_by(Department.name.asc())
    return list(db.execute(stmt).scalars().all())


def update_department(
    db: Session,
    user: UserProfile,
    organization_id: uuid.UUID,
    department_id: uuid.UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> Department:
    """
    Updates department name or description.
    Parent links (program_id, standalone_event_id) are immutable.
    """
    dept = get_department(db, department_id=department_id, organization_id=organization_id)
    require_permission(
        db, user=user, action=ACTION_CREATE_EVENT, organization_id=organization_id
    )

    if dept.archived_at is not None:
        raise DepartmentNotFoundError("Archived department cannot be updated.")

    if dept.program_id is not None:
        program = db.get(Program, dept.program_id)
        if not program or program.archived_at is not None:
            raise ScopeIntegrityError("Parent program is archived or inaccessible.")
    if dept.standalone_event_id is not None:
        event = db.get(Event, dept.standalone_event_id)
        if not event or event.archived_at is not None:
            raise ScopeIntegrityError("Parent standalone event is archived or inaccessible.")

    if name is not None:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Department name must not be empty.")
        dept.name = clean_name

    if description is not None:
        dept.description = description.strip() if description.strip() else None

    dept.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(dept)
    return dept


def assign_event_lead(
    db: Session,
    assigner: UserProfile,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> EventLeadAssignment:
    """
    Assigns an eligible workspace member as an Event Lead for an event.
    Requirements:
    1. Assigner must have ACTION_MANAGE_ROLES in verified organization.
    2. Event must exist, be active (not archived), and belong to organization_id.
    3. If event belongs to a program, parent program must not be archived.
    4. Member must hold an active membership in the same organization_id.
    5. Enforces D-SLICE3-02: only one active lead assignment per member per event.
    6. Synchronizes RoleAssignment(role_name='EVENT_LEAD', scope_type='event', scope_id=event.id)
       transactionally as the authoritative authorization record.
    """
    # 1. Authorize: requires role management permission in verified organization
    require_permission(
        db, user=assigner, action=ACTION_MANAGE_ROLES, organization_id=organization_id
    )

    # 2. Validate Event
    event = db.get(Event, event_id)
    if not event or event.archived_at is not None:
        raise EventNotFoundError(f"Event '{event_id}' not found or is archived.")
    if event.organization_id != organization_id:
        raise ScopeIntegrityError("Event belongs to a different organization.")

    # 3. If child event, validate parent program is operational (D-SLICE3-04)
    if event.program_id is not None:
        program = db.get(Program, event.program_id)
        if not program or program.archived_at is not None:
            raise ScopeIntegrityError("Parent program is archived or inaccessible.")

    # 4. Validate Membership
    membership = db.get(OrganizationMembership, membership_id)
    if not membership or membership.removed_at is not None or membership.membership_status != "active":
        raise EventLeadError("Target member is not an active member of this organization.")
    if membership.organization_id != organization_id:
        raise ScopeIntegrityError("Target member belongs to a different organization.")
    if not membership.user or membership.user.account_status != "active" or membership.user.email_verified_at is None:
        raise EventLeadError("Target member user account is not active or email is unverified.")

    # 5. Prevent duplicate active event lead assignment (D-SLICE3-02)
    existing_active = db.execute(
        select(EventLeadAssignment).where(
            EventLeadAssignment.event_id == event_id,
            EventLeadAssignment.membership_id == membership_id,
            EventLeadAssignment.revoked_at == None,
        )
    ).scalar_one_or_none()
    if existing_active:
        raise DuplicateEventLeadError(
            f"Member '{membership_id}' is already an active Event Lead for event '{event_id}'."
        )

    # 6. Create EventLeadAssignment and synchronized RoleAssignment
    now = datetime.now(timezone.utc)
    assignment = EventLeadAssignment(
        organization_id=organization_id,
        event_id=event_id,
        membership_id=membership_id,
        assigned_by_user_id=assigner.id,
        assigned_at=now,
    )
    db.add(assignment)

    # Synchronize RoleAssignment transactionally
    role_assignment = RoleAssignment(
        membership_id=membership_id,
        role_name="EVENT_LEAD",
        scope_type="event",
        scope_id=event_id,
        granted_by_user_id=assigner.id,
        created_at=now,
    )
    db.add(role_assignment)

    try:
        db.commit()
        db.refresh(assignment)
        return assignment
    except Exception:
        db.rollback()
        raise


def revoke_event_lead(
    db: Session,
    revoker: UserProfile,
    organization_id: uuid.UUID,
    assignment_id: uuid.UUID,
    event_id: Optional[uuid.UUID] = None,
) -> EventLeadAssignment:
    """
    Revokes an active Event Lead assignment.
    Synchronously marks the corresponding RoleAssignment as revoked,
    ensuring revoked assignments immediately cease authorizing actions.
    """
    assignment = db.get(EventLeadAssignment, assignment_id)
    if not assignment or assignment.revoked_at is not None:
        raise EventLeadError(f"Active EventLeadAssignment '{assignment_id}' not found.")

    if assignment.organization_id != organization_id:
        raise ScopeIntegrityError("Assignment belongs to a different organization.")

    if event_id is not None and assignment.event_id != event_id:
        raise ScopeIntegrityError("Assignment belongs to a different event.")

    require_permission(
        db, user=revoker, action=ACTION_MANAGE_ROLES, organization_id=organization_id
    )

    now = datetime.now(timezone.utc)
    assignment.revoked_at = now

    # Synchronously revoke active RoleAssignment for this event scope
    active_roles = db.execute(
        select(RoleAssignment).where(
            RoleAssignment.membership_id == assignment.membership_id,
            RoleAssignment.role_name == "EVENT_LEAD",
            RoleAssignment.scope_type == "event",
            RoleAssignment.scope_id == assignment.event_id,
            RoleAssignment.revoked_at == None,
        )
    ).scalars().all()
    for ra in active_roles:
        ra.revoked_at = now

    try:
        db.commit()
        db.refresh(assignment)
        return assignment
    except Exception:
        db.rollback()
        raise


def get_active_event_leads(
    db: Session,
    event_id: uuid.UUID,
    organization_id: Optional[uuid.UUID] = None,
) -> List[EventLeadAssignment]:
    """Returns all currently active EventLeadAssignments for an event, validating org tenancy if specified."""
    if organization_id is not None:
        get_event(db, event_id=event_id, organization_id=organization_id)

    stmt = (
        select(EventLeadAssignment)
        .where(
            EventLeadAssignment.event_id == event_id,
            EventLeadAssignment.revoked_at == None,
        )
        .order_by(EventLeadAssignment.assigned_at.asc())
    )
    return list(db.execute(stmt).scalars().all())


# =========================================================================
# Domain Scope Validation Helpers (For Permissions and Future Slice 3B APIs)
# =========================================================================


def validate_program_scope_assignment(
    db: Session,
    organization_id: uuid.UUID,
    program_id: uuid.UUID,
) -> Program:
    """Validates that a program exists, is operational, and belongs to organization_id."""
    return get_program(db=db, program_id=program_id, organization_id=organization_id)


def validate_event_scope_assignment(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
) -> Event:
    """Validates that an event exists, is operational, and belongs to organization_id."""
    event = get_event(db=db, event_id=event_id, organization_id=organization_id)
    if event.program_id is not None:
        program = db.get(Program, event.program_id)
        if not program or program.archived_at is not None:
            raise ScopeIntegrityError("Parent program is archived or inaccessible.")
    return event


def validate_department_scope_assignment(
    db: Session,
    organization_id: uuid.UUID,
    department_id: uuid.UUID,
) -> Department:
    """Validates that a department exists, is operational, and belongs to organization_id."""
    dept = get_department(db=db, department_id=department_id, organization_id=organization_id)
    if dept.program_id is not None:
        program = db.get(Program, dept.program_id)
        if not program or program.archived_at is not None:
            raise ScopeIntegrityError("Parent program is archived or inaccessible.")
    if dept.standalone_event_id is not None:
        event = db.get(Event, dept.standalone_event_id)
        if not event or event.archived_at is not None:
            raise ScopeIntegrityError("Parent standalone event is archived or inaccessible.")
    return dept


def validate_event_lead_eligibility(
    db: Session,
    organization_id: uuid.UUID,
    event_id: uuid.UUID,
    membership_id: uuid.UUID,
) -> Tuple[Event, OrganizationMembership]:
    """Validates that both the event and member are eligible for lead assignment."""
    event = validate_event_scope_assignment(db, organization_id, event_id)
    membership = db.get(OrganizationMembership, membership_id)
    if not membership or membership.removed_at is not None or membership.membership_status != "active":
        raise EventLeadError("Target member is not active.")
    if membership.organization_id != organization_id:
        raise ScopeIntegrityError("Member belongs to a different organization.")
    if not membership.user or membership.user.account_status != "active" or membership.user.email_verified_at is None:
        raise EventLeadError("Target member user account is not active or email is unverified.")
    return event, membership

