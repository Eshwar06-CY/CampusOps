"""slice_5_registration_ticketing_and_attendance

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-10-29 18:20:00.000000

Additive migration to establish the Slice 5 domain schema:
1. event_registration_settings (1:1 with event, capacity and format rules)
2. registrations (administrative transaction header for solo or team)
3. participants (canonical attendee records with non-unique email for shared email support)
4. registration_participants (normalized join table linking registrations to participants)
5. tickets (non-payment admission passes with hashed tokens and single active pass index)
6. check_ins (verified attendance log with single active check-in partial unique index)
7. check_in_corrections (immutable audit ledger for check-in voids and adjustments)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = 'a6b7c8d9e0f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create event_registration_settings
    op.create_table(
        'event_registration_settings',
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('is_open', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('registration_format', sa.String(length=30), server_default='both', nullable=False),
        sa.Column('capacity_limit', sa.Integer(), nullable=True),
        sa.Column('current_confirmed_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('current_attended_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('waitlist_enabled', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('team_size_min', sa.Integer(), server_default='2', nullable=False),
        sa.Column('team_size_max', sa.Integer(), server_default='4', nullable=False),
        sa.Column('registration_open_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('registration_close_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('registration_key_hash', sa.String(length=64), nullable=True),
        sa.Column('access_code_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['event_id', 'organization_id'],
            ['events.id', 'events.organization_id'],
            name='fk_event_reg_settings_event_org',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], name='fk_event_reg_settings_event', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_event_reg_settings_org', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('event_id'),
        sa.CheckConstraint("registration_format IN ('solo_only', 'team_only', 'both')", name='ck_event_reg_settings_format'),
        sa.CheckConstraint("team_size_min >= 1 AND team_size_max >= team_size_min", name='ck_event_reg_settings_team_bounds'),
        sa.CheckConstraint("capacity_limit IS NULL OR capacity_limit >= 0", name='ck_event_reg_settings_capacity'),
        sa.CheckConstraint("current_confirmed_count >= 0", name='ck_event_reg_settings_confirmed_nonneg'),
        sa.CheckConstraint("current_attended_count >= 0", name='ck_event_reg_settings_attended_nonneg'),
        sa.CheckConstraint("registration_open_at IS NULL OR registration_close_at IS NULL OR registration_close_at >= registration_open_at", name='ck_event_reg_settings_dates'),
    )
    op.create_index('ix_event_reg_settings_org', 'event_registration_settings', ['organization_id'], unique=False)
    op.create_index('ix_event_reg_settings_key_hash', 'event_registration_settings', ['registration_key_hash'], unique=False)

    # 2. Create registrations
    op.create_table(
        'registrations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('registration_type', sa.String(length=20), server_default='individual', nullable=False),
        sa.Column('registration_status', sa.String(length=30), server_default='confirmed', nullable=False),
        sa.Column('registration_channel', sa.String(length=20), server_default='native_web', nullable=False),
        sa.Column('team_name', sa.String(length=150), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=False),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('confirmation_code', sa.String(length=32), nullable=False),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('source_type', sa.String(length=30), server_default='native', nullable=False),
        sa.Column('external_source_id', sa.String(length=255), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['event_id', 'organization_id'],
            ['events.id', 'events.organization_id'],
            name='fk_registrations_event_org',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_registrations_org', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', 'organization_id', name='uq_registrations_id_org'),
        sa.UniqueConstraint('id', 'event_id', name='uq_registrations_id_event'),
        sa.UniqueConstraint('id', 'event_id', 'organization_id', name='uq_registrations_id_event_org'),
        sa.UniqueConstraint('event_id', 'confirmation_code', name='uq_registrations_event_code'),
        sa.CheckConstraint("registration_type IN ('individual', 'team')", name='ck_registrations_type'),
        sa.CheckConstraint("registration_status IN ('confirmed', 'waitlisted', 'cancelled')", name='ck_registrations_status'),
        sa.CheckConstraint("registration_channel IN ('native_web', 'walk_in', 'external_import')", name='ck_registrations_channel'),
        sa.CheckConstraint("(registration_type = 'team' AND team_name IS NOT NULL) OR (registration_type = 'individual')", name='ck_registrations_team_name'),
        sa.CheckConstraint("(registration_status = 'cancelled' AND cancelled_at IS NOT NULL) OR (registration_status != 'cancelled' AND cancelled_at IS NULL)", name='ck_registrations_cancellation'),
    )
    op.create_index('ix_registrations_org_event', 'registrations', ['organization_id', 'event_id'], unique=False)
    op.create_index('ix_registrations_event_status', 'registrations', ['event_id', 'registration_status'], unique=False)
    op.create_index('ix_registrations_event_contact', 'registrations', ['event_id', 'contact_email'], unique=False)
    op.create_index('ix_registrations_idempotency', 'registrations', ['event_id', 'idempotency_key'], unique=False)

    # 3. Create participants
    op.create_table(
        'participants',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('email_normalized', sa.String(length=255), nullable=False),
        sa.Column('phone_number', sa.String(length=50), nullable=True),
        sa.Column('college_name', sa.String(length=200), nullable=True),
        sa.Column('student_id', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=30), server_default='registered', nullable=False),
        sa.Column('custom_answers', sa.JSON(), nullable=True),
        sa.Column('external_participant_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['event_id', 'organization_id'],
            ['events.id', 'events.organization_id'],
            name='fk_participants_event_org',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_participants_org', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', 'organization_id', name='uq_participants_id_org'),
        sa.UniqueConstraint('id', 'event_id', name='uq_participants_id_event'),
        sa.UniqueConstraint('id', 'event_id', 'organization_id', name='uq_participants_id_event_org'),
        sa.CheckConstraint("status IN ('registered', 'cancelled', 'attended')", name='ck_participants_status'),
    )
    op.create_index('ix_participants_org_event', 'participants', ['organization_id', 'event_id'], unique=False)
    op.create_index('ix_participants_event_email', 'participants', ['event_id', 'email_normalized'], unique=False)
    op.create_index('ix_participants_event_name', 'participants', ['event_id', 'full_name'], unique=False)

    # 4. Create registration_participants
    op.create_table(
        'registration_participants',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('registration_id', sa.Uuid(), nullable=False),
        sa.Column('participant_id', sa.Uuid(), nullable=False),
        sa.Column('is_primary_contact', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('team_role', sa.String(length=50), nullable=True),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['event_id', 'organization_id'],
            ['events.id', 'events.organization_id'],
            name='fk_reg_parts_event_org',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['registration_id', 'event_id', 'organization_id'],
            ['registrations.id', 'registrations.event_id', 'registrations.organization_id'],
            name='fk_reg_parts_registration',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['participant_id', 'event_id', 'organization_id'],
            ['participants.id', 'participants.event_id', 'participants.organization_id'],
            name='fk_reg_parts_participant',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('registration_id', 'participant_id', name='uq_reg_part_reg_participant'),
    )
    op.create_index('ix_reg_parts_participant', 'registration_participants', ['participant_id'], unique=False)
    op.create_index('ix_reg_parts_registration', 'registration_participants', ['registration_id'], unique=False)
    op.create_index('ix_reg_parts_event', 'registration_participants', ['event_id'], unique=False)

    # 5. Create tickets
    op.create_table(
        'tickets',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('participant_id', sa.Uuid(), nullable=False),
        sa.Column('registration_id', sa.Uuid(), nullable=False),
        sa.Column('ticket_reference', sa.String(length=32), nullable=False),
        sa.Column('pass_code_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='issued', nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revocation_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['event_id', 'organization_id'],
            ['events.id', 'events.organization_id'],
            name='fk_tickets_event_org',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['participant_id', 'event_id', 'organization_id'],
            ['participants.id', 'participants.event_id', 'participants.organization_id'],
            name='fk_tickets_participant',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['registration_id', 'event_id', 'organization_id'],
            ['registrations.id', 'registrations.event_id', 'registrations.organization_id'],
            name='fk_tickets_registration',
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', 'organization_id', name='uq_tickets_id_org'),
        sa.UniqueConstraint('id', 'event_id', name='uq_tickets_id_event'),
        sa.UniqueConstraint('id', 'event_id', 'organization_id', name='uq_tickets_id_event_org'),
        sa.UniqueConstraint('event_id', 'pass_code_hash', name='uq_tickets_event_hash'),
        sa.CheckConstraint("status IN ('issued', 'used', 'revoked', 'cancelled')", name='ck_tickets_status'),
        sa.CheckConstraint("(status = 'used' AND used_at IS NOT NULL) OR (status != 'used')", name='ck_tickets_used_at'),
        sa.CheckConstraint("(status = 'revoked' AND revoked_at IS NOT NULL) OR (status != 'revoked' AND revoked_at IS NULL)", name='ck_tickets_revoked_at'),
    )
    op.create_index(
        'uq_ticket_participant_active',
        'tickets',
        ['participant_id'],
        unique=True,
        sqlite_where=sa.text("status = 'issued'"),
        postgresql_where=sa.text("status = 'issued'"),
    )
    op.create_index('ix_tickets_participant', 'tickets', ['participant_id'], unique=False)
    op.create_index('ix_tickets_registration', 'tickets', ['registration_id'], unique=False)
    op.create_index('ix_tickets_event_hash', 'tickets', ['event_id', 'pass_code_hash'], unique=False)

    # 6. Create check_ins
    op.create_table(
        'check_ins',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('event_id', sa.Uuid(), nullable=False),
        sa.Column('participant_id', sa.Uuid(), nullable=False),
        sa.Column('ticket_id', sa.Uuid(), nullable=False),
        sa.Column('check_in_status', sa.String(length=30), server_default='valid', nullable=False),
        sa.Column('method', sa.String(length=30), server_default='qr_scan', nullable=False),
        sa.Column('station_id', sa.String(length=50), nullable=True),
        sa.Column('checked_in_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('checked_in_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('voided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('voided_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['event_id', 'organization_id'],
            ['events.id', 'events.organization_id'],
            name='fk_check_ins_event_org',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['participant_id', 'event_id', 'organization_id'],
            ['participants.id', 'participants.event_id', 'participants.organization_id'],
            name='fk_check_ins_participant',
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['ticket_id', 'event_id', 'organization_id'],
            ['tickets.id', 'tickets.event_id', 'tickets.organization_id'],
            name='fk_check_ins_ticket',
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(['checked_in_by_user_id'], ['user_profiles.id'], name='fk_check_ins_checked_by', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['voided_by_user_id'], ['user_profiles.id'], name='fk_check_ins_voided_by', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', 'organization_id', name='uq_check_ins_id_org'),
        sa.CheckConstraint("check_in_status IN ('valid', 'voided')", name='ck_check_ins_status'),
        sa.CheckConstraint("method IN ('qr_scan', 'manual_search', 'walk_in_direct')", name='ck_check_ins_method'),
        sa.CheckConstraint(
            "((check_in_status = 'voided' AND voided_at IS NOT NULL AND voided_by_user_id IS NOT NULL) "
            "OR (check_in_status = 'valid' AND voided_at IS NULL AND voided_by_user_id IS NULL))",
            name='ck_check_ins_void_integrity',
        ),
    )
    op.create_index(
        'uq_check_in_event_participant',
        'check_ins',
        ['event_id', 'participant_id'],
        unique=True,
        sqlite_where=sa.text("check_in_status = 'valid'"),
        postgresql_where=sa.text("check_in_status = 'valid'"),
    )
    op.create_index('ix_check_ins_org_event', 'check_ins', ['organization_id', 'event_id'], unique=False)
    op.create_index('ix_check_ins_participant', 'check_ins', ['participant_id'], unique=False)
    op.create_index('ix_check_ins_ticket', 'check_ins', ['ticket_id'], unique=False)

    # 7. Create check_in_corrections
    op.create_table(
        'check_in_corrections',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('check_in_id', sa.Uuid(), nullable=False),
        sa.Column('previous_status', sa.String(length=30), nullable=False),
        sa.Column('new_status', sa.String(length=30), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('corrected_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('corrected_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['check_in_id'], ['check_ins.id'], name='fk_corrections_check_in', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['corrected_by_user_id'], ['user_profiles.id'], name='fk_corrections_corrected_by', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("length(trim(reason)) >= 10", name='ck_corrections_reason_min_length'),
    )
    op.create_index('ix_check_in_corrections_item', 'check_in_corrections', ['check_in_id'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table('check_in_corrections')
    op.drop_table('check_ins')
    op.drop_table('tickets')
    op.drop_table('registration_participants')
    op.drop_table('participants')
    op.drop_table('registrations')
    op.drop_table('event_registration_settings')

