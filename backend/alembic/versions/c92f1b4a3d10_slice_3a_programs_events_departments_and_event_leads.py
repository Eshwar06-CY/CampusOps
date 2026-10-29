"""slice_3a_programs_events_departments_and_event_leads

Revision ID: c92f1b4a3d10
Revises: 880d8e4eb890
Create Date: 2026-10-28 23:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c92f1b4a3d10'
down_revision: Union[str, Sequence[str], None] = '880d8e4eb890'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema to Slice 3A foundation."""
    # 1. Create programs table
    op.create_table(
        'programs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('planned_start_date', sa.Date(), nullable=True),
        sa.Column('planned_end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['user_profiles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('organization_id', 'name', name='uq_programs_org_name'),
    )
    with op.batch_alter_table('programs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_programs_organization_id'), ['organization_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_programs_status'), ['status'], unique=False)
        batch_op.create_index('ix_programs_org_status', ['organization_id', 'status'], unique=False)

    # 2. Create events table
    op.create_table(
        'events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('program_id', sa.Uuid(), nullable=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('event_date', sa.Date(), nullable=True),
        sa.Column('planned_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('planned_end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('venue', sa.String(length=200), nullable=True),
        sa.Column('event_format', sa.String(length=50), nullable=False, server_default='in_person'),
        sa.Column('registration_mode', sa.String(length=50), nullable=False, server_default='individual'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='draft'),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['user_profiles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_events_organization_id'), ['organization_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_events_program_id'), ['program_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_events_status'), ['status'], unique=False)
        batch_op.create_index('ix_events_org_program', ['organization_id', 'program_id'], unique=False)
        batch_op.create_index('ix_events_org_status', ['organization_id', 'status'], unique=False)
        batch_op.create_index('ix_events_org_date', ['organization_id', 'event_date'], unique=False)

    # 3. Create departments table with exclusive parent check constraint
    op.create_table(
        'departments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('program_id', sa.Uuid(), nullable=True),
        sa.Column('standalone_event_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='active'),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "((program_id IS NOT NULL AND standalone_event_id IS NULL) OR (program_id IS NULL AND standalone_event_id IS NOT NULL))",
            name='ck_departments_exclusive_parent'
        ),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['user_profiles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['standalone_event_id'], ['events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_departments_organization_id'), ['organization_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_departments_program_id'), ['program_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_departments_standalone_event_id'), ['standalone_event_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_departments_status'), ['status'], unique=False)
        batch_op.create_index('ix_departments_org_program', ['organization_id', 'program_id'], unique=False)
        batch_op.create_index('ix_departments_org_event', ['organization_id', 'standalone_event_id'], unique=False)
        batch_op.create_index('ix_departments_org_status', ['organization_id', 'status'], unique=False)

    # 4. Create event_lead_assignments table
    op.create_table(
        'event_lead_assignments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('membership_id', sa.Uuid(), nullable=False),
        sa.Column('assigned_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by_user_id'], ['user_profiles.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['membership_id'], ['organization_memberships.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('event_lead_assignments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_event_lead_assignments_organization_id'), ['organization_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_event_lead_assignments_event_id'), ['event_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_event_lead_assignments_membership_id'), ['membership_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_event_lead_assignments_revoked_at'), ['revoked_at'], unique=False)
        batch_op.create_index('ix_event_leads_event_membership', ['event_id', 'membership_id'], unique=False)
        batch_op.create_index('ix_event_leads_org_status', ['organization_id', 'revoked_at'], unique=False)
        batch_op.create_index(
            'uq_event_lead_active',
            ['event_id', 'membership_id'],
            unique=True,
            sqlite_where=sa.text('revoked_at IS NULL')
        )


def downgrade() -> None:
    """Downgrade schema in reverse dependency order."""
    # 1. Drop event_lead_assignments table
    with op.batch_alter_table('event_lead_assignments', schema=None) as batch_op:
        batch_op.drop_index('uq_event_lead_active')
        batch_op.drop_index('ix_event_leads_org_status')
        batch_op.drop_index('ix_event_leads_event_membership')
        batch_op.drop_index(batch_op.f('ix_event_lead_assignments_revoked_at'))
        batch_op.drop_index(batch_op.f('ix_event_lead_assignments_membership_id'))
        batch_op.drop_index(batch_op.f('ix_event_lead_assignments_event_id'))
        batch_op.drop_index(batch_op.f('ix_event_lead_assignments_organization_id'))
    op.drop_table('event_lead_assignments')

    # 2. Drop departments table
    with op.batch_alter_table('departments', schema=None) as batch_op:
        batch_op.drop_index('ix_departments_org_status')
        batch_op.drop_index('ix_departments_org_event')
        batch_op.drop_index('ix_departments_org_program')
        batch_op.drop_index(batch_op.f('ix_departments_status'))
        batch_op.drop_index(batch_op.f('ix_departments_standalone_event_id'))
        batch_op.drop_index(batch_op.f('ix_departments_program_id'))
        batch_op.drop_index(batch_op.f('ix_departments_organization_id'))
    op.drop_table('departments')

    # 3. Drop events table
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_index('ix_events_org_date')
        batch_op.drop_index('ix_events_org_status')
        batch_op.drop_index('ix_events_org_program')
        batch_op.drop_index(batch_op.f('ix_events_status'))
        batch_op.drop_index(batch_op.f('ix_events_program_id'))
        batch_op.drop_index(batch_op.f('ix_events_organization_id'))
    op.drop_table('events')

    # 4. Drop programs table
    with op.batch_alter_table('programs', schema=None) as batch_op:
        batch_op.drop_index('ix_programs_org_status')
        batch_op.drop_index(batch_op.f('ix_programs_status'))
        batch_op.drop_index(batch_op.f('ix_programs_organization_id'))
    op.drop_table('programs')

