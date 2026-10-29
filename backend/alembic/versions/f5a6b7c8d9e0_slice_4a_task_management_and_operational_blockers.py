"""slice_4a_task_management_and_operational_blockers

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-10-29 12:28:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create tasks table
    op.create_table(
        'tasks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('scope_type', sa.String(length=30), nullable=False),
        sa.Column('scope_id', sa.Uuid(), nullable=True),
        sa.Column('program_id', sa.Uuid(), nullable=True),
        sa.Column('event_id', sa.Uuid(), nullable=True),
        sa.Column('department_id', sa.Uuid(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(length=20), server_default='medium', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='not_started', nullable=False),
        sa.Column('proof_required', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('due_time', sa.Time(), nullable=True),
        sa.Column('timezone', sa.String(length=50), server_default='Asia/Kolkata', nullable=False),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['user_profiles.id'], name='fk_tasks_creator', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name='fk_tasks_department', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_id', 'organization_id'], ['events.id', 'events.organization_id'], name='fk_tasks_event_org', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_tasks_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id', 'organization_id'], ['programs.id', 'programs.organization_id'], name='fk_tasks_program_org', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('id', 'organization_id', name='uq_tasks_id_org'),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'urgent')", name='ck_tasks_priority'),
        sa.CheckConstraint("status IN ('not_started', 'assigned', 'in_progress', 'submitted_for_review', 'changes_requested', 'completed', 'cancelled')", name='ck_tasks_status'),
        sa.CheckConstraint("scope_type IN ('organization', 'program', 'event', 'department')", name='ck_tasks_scope_type'),
        sa.CheckConstraint("(status = 'completed' AND completed_at IS NOT NULL) OR (status != 'completed' AND completed_at IS NULL)", name='ck_tasks_status_completed'),
    )
    op.create_index('ix_tasks_organization_id', 'tasks', ['organization_id'], unique=False)
    op.create_index('ix_tasks_org_status', 'tasks', ['organization_id', 'status'], unique=False)
    op.create_index('ix_tasks_org_scope', 'tasks', ['organization_id', 'scope_type', 'scope_id'], unique=False)
    op.create_index('ix_tasks_org_event', 'tasks', ['organization_id', 'event_id'], unique=False)
    op.create_index('ix_tasks_org_due', 'tasks', ['organization_id', 'due_date'], unique=False)

    # 2. Create task_assignees table
    op.create_table(
        'task_assignees',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('membership_id', sa.Uuid(), nullable=False),
        sa.Column('assignment_status', sa.String(length=20), server_default='active', nullable=False),
        sa.Column('assigned_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('unassigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('unassigned_by_user_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by_user_id'], ['user_profiles.id'], name='fk_task_assignees_assigned_by', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['membership_id', 'organization_id'], ['organization_memberships.id', 'organization_memberships.organization_id'], name='fk_task_assignees_membership_org', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_task_assignees_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id', 'organization_id'], ['tasks.id', 'tasks.organization_id'], name='fk_task_assignees_task_org', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['unassigned_by_user_id'], ['user_profiles.id'], name='fk_task_assignees_unassigned_by', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("assignment_status IN ('active', 'unassigned')", name='ck_task_assignees_status'),
    )
    op.create_index('ix_task_assignees_task_id', 'task_assignees', ['task_id'], unique=False)
    op.create_index('ix_task_assignees_membership_id', 'task_assignees', ['membership_id'], unique=False)
    op.create_index(
        'uq_task_assignee_active',
        'task_assignees',
        ['task_id', 'membership_id'],
        unique=True,
        sqlite_where=sa.text("assignment_status = 'active'"),
        postgresql_where=sa.text("assignment_status = 'active'"),
    )

    # 3. Create task_deadline_history table
    op.create_table(
        'task_deadline_history',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('previous_due_date', sa.Date(), nullable=False),
        sa.Column('previous_due_time', sa.Time(), nullable=True),
        sa.Column('new_due_date', sa.Date(), nullable=False),
        sa.Column('new_due_time', sa.Time(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('changed_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['user_profiles.id'], name='fk_task_deadline_history_changed_by', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name='fk_task_deadline_history_task', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_task_deadline_history_task_id', 'task_deadline_history', ['task_id'], unique=False)

    # 4. Create task_status_history table
    op.create_table(
        'task_status_history',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('previous_status', sa.String(length=30), nullable=True),
        sa.Column('new_status', sa.String(length=30), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('changed_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['user_profiles.id'], name='fk_task_status_history_changed_by', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name='fk_task_status_history_task', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_task_status_history_task_id', 'task_status_history', ['task_id'], unique=False)

    # 5. Create evidence_submissions table
    op.create_table(
        'evidence_submissions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('submitted_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('submitted_by_membership_id', sa.Uuid(), nullable=False),
        sa.Column('submission_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('submitter_note', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), server_default='pending_review', nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['submitted_by_membership_id'], ['organization_memberships.id'], name='fk_evidence_submissions_membership', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['submitted_by_user_id'], ['user_profiles.id'], name='fk_evidence_submissions_user', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name='fk_evidence_submissions_task', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id', 'submission_number', name='uq_evidence_submissions_task_num'),
        sa.CheckConstraint("status IN ('pending_review', 'approved', 'changes_requested')", name='ck_evidence_submissions_status'),
    )
    op.create_index('ix_evidence_submissions_task_id', 'evidence_submissions', ['task_id'], unique=False)

    # 6. Create evidence_artifacts table
    op.create_table(
        'evidence_artifacts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('submission_id', sa.Uuid(), nullable=False),
        sa.Column('artifact_type', sa.String(length=30), server_default='url', nullable=False),
        sa.Column('url', sa.Text(), nullable=True),
        sa.Column('file_reference', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['submission_id'], ['evidence_submissions.id'], name='fk_evidence_artifacts_submission', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("artifact_type IN ('url', 'file_reference')", name='ck_evidence_artifacts_type'),
        sa.CheckConstraint("(artifact_type = 'url' AND url IS NOT NULL AND file_reference IS NULL) OR (artifact_type = 'file_reference' AND file_reference IS NOT NULL AND url IS NULL)", name='ck_evidence_artifacts_payload'),
    )
    op.create_index('ix_evidence_artifacts_submission_id', 'evidence_artifacts', ['submission_id'], unique=False)

    # 7. Create task_reviews table
    op.create_table(
        'task_reviews',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('evidence_submission_id', sa.Uuid(), nullable=False),
        sa.Column('task_id', sa.Uuid(), nullable=False),
        sa.Column('reviewer_user_id', sa.Uuid(), nullable=False),
        sa.Column('reviewer_membership_id', sa.Uuid(), nullable=False),
        sa.Column('decision', sa.String(length=30), nullable=False),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['evidence_submission_id'], ['evidence_submissions.id'], name='fk_task_reviews_submission', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_membership_id'], ['organization_memberships.id'], name='fk_task_reviews_membership', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_user_id'], ['user_profiles.id'], name='fk_task_reviews_user', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name='fk_task_reviews_task', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('evidence_submission_id', name='uq_task_reviews_submission'),
        sa.CheckConstraint("decision IN ('approved', 'changes_requested')", name='ck_task_reviews_decision'),
        sa.CheckConstraint("(decision = 'changes_requested' AND review_note IS NOT NULL) OR (decision = 'approved')", name='ck_task_reviews_note_on_rejection'),
    )
    op.create_index('ix_task_reviews_task_id', 'task_reviews', ['task_id'], unique=False)

    # 8. Create operational_blockers table
    op.create_table(
        'operational_blockers',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('scope_type', sa.String(length=30), nullable=False),
        sa.Column('scope_id', sa.Uuid(), nullable=True),
        sa.Column('task_id', sa.Uuid(), nullable=True),
        sa.Column('event_id', sa.Uuid(), nullable=True),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.String(length=20), server_default='medium', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='open', nullable=False),
        sa.Column('created_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('owner_membership_id', sa.Uuid(), nullable=True),
        sa.Column('resolved_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['user_profiles.id'], name='fk_operational_blockers_creator', ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], name='fk_operational_blockers_event', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_operational_blockers_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_membership_id'], ['organization_memberships.id'], name='fk_operational_blockers_owner', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['resolved_by_user_id'], ['user_profiles.id'], name='fk_operational_blockers_resolved_by', ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], name='fk_operational_blockers_task', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("scope_type IN ('organization', 'program', 'event', 'department', 'task')", name='ck_operational_blockers_scope'),
        sa.CheckConstraint("priority IN ('low', 'medium', 'high', 'critical')", name='ck_operational_blockers_priority'),
        sa.CheckConstraint("status IN ('open', 'in_progress', 'resolved', 'wont_fix')", name='ck_operational_blockers_status'),
        sa.CheckConstraint("(status IN ('resolved', 'wont_fix') AND resolved_at IS NOT NULL) OR (status IN ('open', 'in_progress') AND resolved_at IS NULL)", name='ck_operational_blockers_resolved'),
    )
    op.create_index('ix_operational_blockers_organization_id', 'operational_blockers', ['organization_id'], unique=False)
    op.create_index('ix_operational_blockers_org_status', 'operational_blockers', ['organization_id', 'status'], unique=False)
    op.create_index('ix_operational_blockers_org_scope', 'operational_blockers', ['organization_id', 'scope_type', 'scope_id'], unique=False)

    # 9. Create operational_blocker_history table
    op.create_table(
        'operational_blocker_history',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('blocker_id', sa.Uuid(), nullable=False),
        sa.Column('previous_status', sa.String(length=30), nullable=True),
        sa.Column('new_status', sa.String(length=30), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('changed_by_user_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['blocker_id'], ['operational_blockers.id'], name='fk_operational_blocker_history_blocker', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['user_profiles.id'], name='fk_operational_blocker_history_changed_by', ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_operational_blocker_history_blocker_id', 'operational_blocker_history', ['blocker_id'], unique=False)

    # 10. Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('organization_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('related_entity_type', sa.String(length=50), nullable=False),
        sa.Column('related_entity_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('is_read', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name='fk_notifications_organization', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.id'], name='fk_notifications_user', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_organization_id', 'notifications', ['organization_id'], unique=False)
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('operational_blocker_history')
    op.drop_table('operational_blockers')
    op.drop_table('task_reviews')
    op.drop_table('evidence_artifacts')
    op.drop_table('evidence_submissions')
    op.drop_table('task_status_history')
    op.drop_table('task_deadline_history')
    op.drop_table('task_assignees')
    op.drop_table('tasks')
