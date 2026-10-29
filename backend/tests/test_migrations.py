import os
import tempfile
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.database import create_app_engine


def test_alembic_migrations_clean_lifecycle():
    """Verify Alembic migration applies cleanly to an isolated SQLite database and downgrades."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        sqlite_url = f"sqlite:///{tmp_db_path.replace('\\', '/')}"

        # Configure Alembic to point to the isolated temp DB
        alembic_ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", sqlite_url)

        # 1. Run upgrade head
        command.upgrade(alembic_cfg, "head")

        # 2. Inspect created tables
        engine = create_app_engine(sqlite_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        expected_tables = {
            "user_profiles",
            "organizations",
            "organization_memberships",
            "role_assignments",
            "platform_admins",
            "invitations",
            "programs",
            "events",
            "departments",
            "event_lead_assignments",
            "tasks",
            "task_assignees",
            "task_deadline_history",
            "task_status_history",
            "evidence_submissions",
            "evidence_artifacts",
            "task_reviews",
            "operational_blockers",
            "operational_blocker_history",
            "notifications",
            "alembic_version",
        }
        assert expected_tables.issubset(tables), f"Missing tables: {expected_tables - tables}"

        # 3. Verify specific column names on user_profiles, events, and tasks
        user_cols = {col["name"] for col in inspector.get_columns("user_profiles")}
        assert "password" not in user_cols
        assert "password_hash" not in user_cols
        assert "auth_subject_id" in user_cols
        assert "email_normalized" in user_cols

        event_cols = {col["name"] for col in inspector.get_columns("events")}
        assert "timezone" in event_cols
        assert "event_end_date" in event_cols

        task_cols = {col["name"] for col in inspector.get_columns("tasks")}
        assert "due_date" in task_cols
        assert "proof_required" in task_cols
        assert "scope_type" in task_cols
        assert "priority" in task_cols

        # 4. Verify unique constraints on organization_memberships, programs, and events
        org_mem_uqs = [uq["name"] for uq in inspector.get_unique_constraints("organization_memberships")]
        assert "uq_org_membership_user" in org_mem_uqs or len(org_mem_uqs) > 0

        # Verify foreign keys on events include composite foreign key
        event_fks = inspector.get_foreign_keys("events")
        has_composite_prog_fk = any(
            fk["referred_table"] == "programs" and len(fk["constrained_columns"]) == 2
            for fk in event_fks
        )
        assert has_composite_prog_fk, f"Missing composite program FK on events: {event_fks}"

        engine.dispose()

        # 5. Run downgrade base
        command.downgrade(alembic_cfg, "base")
        engine_after_down = create_app_engine(sqlite_url)
        inspector_after_down = inspect(engine_after_down)
        tables_after_down = set(inspector_after_down.get_table_names())
        assert "user_profiles" not in tables_after_down
        assert "organizations" not in tables_after_down
        assert "programs" not in tables_after_down
        assert "events" not in tables_after_down
        assert "departments" not in tables_after_down
        assert "event_lead_assignments" not in tables_after_down
        engine_after_down.dispose()

        # 6. Run re-upgrade head to verify roundtrip
        command.upgrade(alembic_cfg, "head")
        engine_reup = create_app_engine(sqlite_url)
        inspector_reup = inspect(engine_reup)
        tables_reup = set(inspector_reup.get_table_names())
        assert expected_tables.issubset(tables_reup)
        engine_reup.dispose()

    finally:
        if os.path.exists(tmp_db_path):
            os.remove(tmp_db_path)


def test_slice_4a_assignee_index_migration_lifecycle():
    """Verify incremental upgrade and downgrade of task assignee unique index between f5a6b7c8d9e0 and a6b7c8d9e0f1."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        sqlite_url = f"sqlite:///{tmp_db_path.replace(os.sep, '/')}"
        alembic_ini_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        alembic_cfg = Config(alembic_ini_path)
        alembic_cfg.set_main_option("sqlalchemy.url", sqlite_url)

        # 1. Upgrade to f5a6b7c8d9e0 (original Slice 4A migration)
        command.upgrade(alembic_cfg, "f5a6b7c8d9e0")
        engine1 = create_app_engine(sqlite_url)
        with engine1.connect() as conn:
            idx_sql1 = conn.exec_driver_sql("SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_task_assignee_active'").scalar()
            assert idx_sql1 is not None
            assert "task_id" in idx_sql1 and "membership_id" in idx_sql1
        engine1.dispose()

        # 2. Upgrade to a6b7c8d9e0f1 (Slice 4A additive hardening migration)
        command.upgrade(alembic_cfg, "a6b7c8d9e0f1")
        engine2 = create_app_engine(sqlite_url)
        with engine2.connect() as conn:
            idx_sql2 = conn.exec_driver_sql("SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_task_assignee_active'").scalar()
            assert idx_sql2 is not None
            assert "task_id" in idx_sql2 and "membership_id" not in idx_sql2
        engine2.dispose()

        # 3. Downgrade back to f5a6b7c8d9e0
        command.downgrade(alembic_cfg, "f5a6b7c8d9e0")
        engine3 = create_app_engine(sqlite_url)
        with engine3.connect() as conn:
            idx_sql3 = conn.exec_driver_sql("SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_task_assignee_active'").scalar()
            assert idx_sql3 is not None
            assert "task_id" in idx_sql3 and "membership_id" in idx_sql3
        engine3.dispose()

        # 4. Re-upgrade to head
        command.upgrade(alembic_cfg, "head")
        engine4 = create_app_engine(sqlite_url)
        with engine4.connect() as conn:
            idx_sql4 = conn.exec_driver_sql("SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_task_assignee_active'").scalar()
            assert idx_sql4 is not None
            assert "task_id" in idx_sql4 and "membership_id" not in idx_sql4
        engine4.dispose()

    finally:
        if os.path.exists(tmp_db_path):
            os.remove(tmp_db_path)

