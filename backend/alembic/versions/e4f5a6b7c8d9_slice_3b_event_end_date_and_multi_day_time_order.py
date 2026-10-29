"""slice_3b_event_end_date_and_multi_day_time_order

Revision ID: e4f5a6b7c8d9
Revises: d81e3a5f2c90
Create Date: 2026-10-29 11:00:00.000000

Additive migration to add event_end_date to operational events, enforce date ordering
constraints, and replace the single-day-only time ordering constraint with a multi-day
aware constraint permitting overnight/multi-day schedules when event_end_date > event_date.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4f5a6b7c8d9'
down_revision: Union[str, Sequence[str], None] = 'd81e3a5f2c90'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add event_end_date and upgrade time/date sequencing constraints on events table."""
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('event_end_date', sa.Date(), nullable=True))
        batch_op.create_check_constraint(
            'ck_events_date_order',
            'event_end_date IS NULL OR event_date IS NULL OR event_end_date >= event_date',
        )
        batch_op.drop_constraint('ck_events_time_order', type_='check')
        batch_op.create_check_constraint(
            'ck_events_time_order',
            '(planned_start_time IS NULL OR planned_end_time IS NULL) '
            'OR (event_end_date IS NOT NULL AND event_date IS NOT NULL AND event_end_date > event_date) '
            'OR (planned_end_time >= planned_start_time)',
        )


def downgrade() -> None:
    """Revert event_end_date and restore previous single-day-only time sequencing constraint."""
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_constraint('ck_events_time_order', type_='check')
        batch_op.drop_constraint('ck_events_date_order', type_='check')
        batch_op.drop_column('event_end_date')
        batch_op.create_check_constraint(
            'ck_events_time_order',
            'planned_start_time IS NULL OR planned_end_time IS NULL OR planned_end_time >= planned_start_time',
        )

