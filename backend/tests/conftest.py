import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Generator

# Enforce pure-Python SQLAlchemy to avoid Windows AppLocker / WDAC C-extension blocks
os.environ.setdefault("DISABLE_SQLALCHEMY_CEXT", "1")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.auth.principal import AuthenticatedPrincipal, get_current_principal
from app.database import Base, get_db
from app.main import app
from app.models.organization import Organization, OrganizationMembership
from app.models.role import PlatformAdmin, RoleAssignment
from app.models.user import UserProfile
from app.services.email import TestEmailDeliverySink, get_email_service


@pytest.fixture(scope="session")
def engine():
    """Create a SQLite engine for tests with foreign keys enforced."""
    test_db_url = "sqlite:///:memory:"
    test_engine = create_engine(
        test_db_url,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(test_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    # Create all schema tables for tests
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def db(engine) -> Generator[Session, None, None]:
    """Provide a clean transactional database session per test."""
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = session_factory()

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def api_client(db: Session) -> Generator[TestClient, None, None]:
    """Provide a TestClient with database session overridden to the test transaction."""
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client(api_client: TestClient) -> TestClient:
    """Convenient alias for api_client."""
    return api_client


@pytest.fixture
def test_email_sink() -> Generator[TestEmailDeliverySink, None, None]:
    """In-memory email delivery sink fixture for testing invitation delivery."""
    sink = TestEmailDeliverySink()
    app.dependency_overrides[get_email_service] = lambda: sink
    yield sink
    sink.clear()
    if get_email_service in app.dependency_overrides:
        del app.dependency_overrides[get_email_service]


@pytest.fixture
def auth_principal():
    """Helper to inject an AuthenticatedPrincipal dependency override."""
    def _set(
        auth_subject_id: str,
        email: str,
        email_verified: bool = True,
        display_name: str = "Test User",
    ) -> AuthenticatedPrincipal:
        principal = AuthenticatedPrincipal(
            auth_subject_id=auth_subject_id,
            email=email.strip().lower(),
            email_verified=email_verified,
            display_name=display_name,
        )
        app.dependency_overrides[get_current_principal] = lambda: principal
        return principal
    return _set


@pytest.fixture
def auth_user(auth_principal):
    """Helper to authenticate as an existing UserProfile."""
    def _as_user(user: UserProfile, email_verified: bool = True) -> AuthenticatedPrincipal:
        return auth_principal(
            auth_subject_id=user.auth_subject_id or f"sub_{user.id.hex[:12]}",
            email=user.email_normalized,
            email_verified=email_verified and (user.email_verified_at is not None),
            display_name=user.display_name,
        )
    return _as_user


@pytest.fixture
def create_synthetic_user(db: Session):
    """Helper fixture to create synthetic users for tests."""
    def _create(
        email: str,
        display_name: str = "Synthetic User",
        auth_subject_id: str = None,
        account_status: str = "active",
        verified: bool = True,
    ) -> UserProfile:
        if auth_subject_id is None:
            auth_subject_id = f"sub_{uuid.uuid4().hex[:12]}"
        user = UserProfile(
            auth_subject_id=auth_subject_id,
            email_normalized=email.strip().lower(),
            display_name=display_name,
            email_verified_at=datetime.now(timezone.utc) if verified else None,
            account_status=account_status,
        )
        db.add(user)
        db.flush()
        return user
    return _create


@pytest.fixture
def create_synthetic_platform_admin(db: Session, create_synthetic_user):
    """Helper fixture to create an explicitly assigned platform admin."""
    def _create(email: str = "admin@campusops.internal") -> UserProfile:
        user = create_synthetic_user(email=email, display_name="Platform Admin")
        admin = PlatformAdmin(
            user_id=user.id,
            is_active=True,
            notes="Authorized platform operator for tests",
        )
        db.add(admin)
        db.flush()
        return user
    return _create
