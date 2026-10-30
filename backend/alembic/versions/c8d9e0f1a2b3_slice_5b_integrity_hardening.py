"""slice 5b integrity hardening

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-10-29 18:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Hardening registrations idempotency index to partial unique index
    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.drop_index('ix_registrations_idempotency')
        batch_op.create_index(
            'uq_registrations_event_idempotency',
            ['event_id', 'idempotency_key'],
            unique=True,
            sqlite_where=sa.text('idempotency_key IS NOT NULL'),
            postgresql_where=sa.text('idempotency_key IS NOT NULL'),
        )

    # 2. Hardening event_registration_settings registration_key_hash to partial unique index
    with op.batch_alter_table('event_registration_settings', schema=None) as batch_op:
        batch_op.drop_index('ix_event_reg_settings_key_hash')
        batch_op.create_index(
            'uq_event_reg_settings_key_hash',
            ['registration_key_hash'],
            unique=True,
            sqlite_where=sa.text('registration_key_hash IS NOT NULL'),
            postgresql_where=sa.text('registration_key_hash IS NOT NULL'),
        )


def downgrade() -> None:
    # 1. Revert event_registration_settings registration_key_hash index
    with op.batch_alter_table('event_registration_settings', schema=None) as batch_op:
        batch_op.drop_index('uq_event_reg_settings_key_hash')
        batch_op.create_index(
            'ix_event_reg_settings_key_hash',
            ['registration_key_hash'],
            unique=False,
        )

    # 2. Revert registrations idempotency index
    with op.batch_alter_table('registrations', schema=None) as batch_op:
        batch_op.drop_index('uq_registrations_event_idempotency')
        batch_op.create_index(
            'ix_registrations_idempotency',
            ['event_id', 'idempotency_key'],
            unique=False,
        )

