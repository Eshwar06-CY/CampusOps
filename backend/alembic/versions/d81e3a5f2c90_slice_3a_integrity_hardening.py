"""slice_3a_integrity_hardening

Revision ID: d81e3a5f2c90
Revises: c92f1b4a3d10
Create Date: 2026-10-29 10:00:00.000000

Additive migration to harden cross-tenant relational integrity with composite foreign keys,
enforce date/time sequencing check constraints, eliminate status/archived_at contradictions,
and ensure timezone specification on operational events.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd81e3a5f2c90'
down_revision: Union[str, Sequence[str], None] = 'c92f1b4a3d10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply cross-tenant composite foreign keys and lifecycle check constraints."""
    # 1. Organization memberships: add unique constraint for composite foreign keys
    with op.batch_alter_table('organization_memberships', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_org_memberships_id_org', ['id', 'organization_id'])

    # 2. Programs: add composite unique constraint and lifecycle check constraints
    with op.batch_alter_table('programs', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_programs_id_org', ['id', 'organization_id'])
        batch_op.create_check_constraint(
            'ck_programs_date_order',
            'planned_start_date IS NULL OR planned_end_date IS NULL OR planned_end_date >= planned_start_date',
        )
        batch_op.create_check_constraint(
            'ck_programs_status_archived',
            "(status = 'archived' AND archived_at IS NOT NULL) OR (status != 'archived' AND archived_at IS NULL)",
        )

    # 3. Events: add timezone, composite unique constraint, composite foreign key to programs, and check constraints
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('timezone', sa.String(length=50), nullable=False, server_default='Asia/Kolkata')
        )
        batch_op.create_unique_constraint('uq_events_id_org', ['id', 'organization_id'])
        batch_op.create_foreign_key(
            'fk_events_program_org',
            'programs',
            ['program_id', 'organization_id'],
            ['id', 'organization_id'],
            ondelete='CASCADE',
        )
        batch_op.create_check_constraint(
            'ck_events_time_order',
            'planned_start_time IS NULL OR planned_end_time IS NULL OR planned_end_time >= planned_start_time',
        )
        batch_op.create_check_constraint(
            'ck_events_status_archived',
            "(status = 'archived' AND archived_at IS NOT NULL) OR (status != 'archived' AND archived_at IS NULL)",
        )

    # 4. Departments: add composite foreign keys and status/archived check constraint
    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_departments_program_org',
            'programs',
            ['program_id', 'organization_id'],
            ['id', 'organization_id'],
            ondelete='CASCADE',
        )
        batch_op.create_foreign_key(
            'fk_departments_event_org',
            'events',
            ['standalone_event_id', 'organization_id'],
            ['id', 'organization_id'],
            ondelete='CASCADE',
        )
        batch_op.create_check_constraint(
            'ck_departments_status_archived',
            "(status = 'archived' AND archived_at IS NOT NULL) OR (status != 'archived' AND archived_at IS NULL)",
        )

    # 5. Event lead assignments: add composite foreign keys to events and memberships
    with op.batch_alter_table('event_lead_assignments', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_event_lead_event_org',
            'events',
            ['event_id', 'organization_id'],
            ['id', 'organization_id'],
            ondelete='CASCADE',
        )
        batch_op.create_foreign_key(
            'fk_event_lead_membership_org',
            'organization_memberships',
            ['membership_id', 'organization_id'],
            ['id', 'organization_id'],
            ondelete='CASCADE',
        )


def downgrade() -> None:
    """Revert constraints and columns in reverse dependency order."""
    # 1. Event lead assignments: drop composite foreign keys
    with op.batch_alter_table('event_lead_assignments', schema=None) as batch_op:
        batch_op.drop_constraint('fk_event_lead_membership_org', type_='foreignkey')
        batch_op.drop_constraint('fk_event_lead_event_org', type_='foreignkey')

    # 2. Departments: drop composite foreign keys and check constraint
    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.drop_constraint('ck_departments_status_archived', type_='check')
        batch_op.drop_constraint('fk_departments_event_org', type_='foreignkey')
        batch_op.drop_constraint('fk_departments_program_org', type_='foreignkey')

    # 3. Events: drop check constraints, composite foreign key, unique constraint, and timezone
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_constraint('ck_events_status_archived', type_='check')
        batch_op.drop_constraint('ck_events_time_order', type_='check')
        batch_op.drop_constraint('fk_events_program_org', type_='foreignkey')
        batch_op.drop_constraint('uq_events_id_org', type_='unique')
        batch_op.drop_column('timezone')

    # 4. Programs: drop check constraints and unique constraint
    with op.batch_alter_table('programs', schema=None) as batch_op:
        batch_op.drop_constraint('ck_programs_status_archived', type_='check')
        batch_op.drop_constraint('ck_programs_date_order', type_='check')
        batch_op.drop_constraint('uq_programs_id_org', type_='unique')

    # 5. Organization memberships: drop unique constraint
    with op.batch_alter_table('organization_memberships', schema=None) as batch_op:
        batch_op.drop_constraint('uq_org_memberships_id_org', type_='unique')

