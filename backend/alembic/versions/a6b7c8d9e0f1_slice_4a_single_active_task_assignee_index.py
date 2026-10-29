"""slice_4a_single_active_task_assignee_index

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-10-29 15:00:00.000000

Additive migration to harden active task assignment by transitioning
the partial unique index uq_task_assignee_active from composite (task_id, membership_id)
to single (task_id) where assignment_status = 'active', ensuring at most one active assignee
per task at the database level while preserving full assignment history.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6b7c8d9e0f1'
down_revision: Union[str, Sequence[str], None] = 'f5a6b7c8d9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Harden active task assignee index to single active assignee per task."""
    op.drop_index('uq_task_assignee_active', table_name='task_assignees')
    op.create_index(
        'uq_task_assignee_active',
        'task_assignees',
        ['task_id'],
        unique=True,
        sqlite_where=sa.text("assignment_status = 'active'"),
        postgresql_where=sa.text("assignment_status = 'active'"),
    )


def downgrade() -> None:
    """Revert active task assignee index to per-membership uniqueness."""
    op.drop_index('uq_task_assignee_active', table_name='task_assignees')
    op.create_index(
        'uq_task_assignee_active',
        'task_assignees',
        ['task_id', 'membership_id'],
        unique=True,
        sqlite_where=sa.text("assignment_status = 'active'"),
        postgresql_where=sa.text("assignment_status = 'active'"),
    )

