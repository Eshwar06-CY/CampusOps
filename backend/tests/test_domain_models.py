import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.invitation import Invitation
from app.models.organization import Organization, OrganizationMembership
from app.models.user import UserProfile


def test_user_profile_has_no_password_fields():
    """Verify strictly no password or hash fields exist on UserProfile."""
    user = UserProfile(
        email_normalized="user@example.com",
        display_name="Test User",
    )
    assert not hasattr(user, "password")
    assert not hasattr(user, "password_hash")
    assert not hasattr(user, "hashed_password")
    assert not hasattr(user, "salt")


def test_user_profile_unique_email_constraint(db, create_synthetic_user):
    """Verify unique constraint on email_normalized."""
    create_synthetic_user("alice@campus.edu", "Alice")
    db.commit()

    with pytest.raises(IntegrityError):
        duplicate_user = UserProfile(
            auth_subject_id="sub_different",
            email_normalized="alice@campus.edu",
            display_name="Duplicate Alice",
        )
        db.add(duplicate_user)
        db.commit()
    db.rollback()


def test_sqlite_foreign_key_enforcement(db):
    """Verify SQLite foreign key constraints are strictly enforced."""
    non_existent_user_id = uuid.uuid4()
    non_existent_org_id = uuid.uuid4()

    # Attempt to insert membership with invalid foreign keys
    membership = OrganizationMembership(
        organization_id=non_existent_org_id,
        user_id=non_existent_user_id,
        membership_status="active",
    )
    db.add(membership)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_duplicate_organization_membership_prevented(db, create_synthetic_user):
    """Verify unique constraint (organization_id, user_id) on OrganizationMembership."""
    user = create_synthetic_user("member@campus.edu", "Member")
    org = Organization(
        college_name="Engineering College",
        club_name="Robotics Club",
        created_by_user_id=user.id,
    )
    db.add(org)
    db.flush()

    m1 = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        membership_status="active",
    )
    db.add(m1)
    db.flush()

    # Attempt to create duplicate membership
    m2 = OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        membership_status="active",
    )
    db.add(m2)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_invitation_model_stores_only_hash(create_synthetic_user, db):
    """Verify Invitation model persists token_hash and has no raw token attribute."""
    user = create_synthetic_user("inviter@campus.edu")
    org = Organization(
        college_name="Arts College",
        club_name="Drama Club",
        created_by_user_id=user.id,
    )
    db.add(org)
    db.flush()

    invitation = Invitation(
        organization_id=org.id,
        email_normalized="invitee@campus.edu",
        role_name="COORDINATOR",
        scope_type="organization",
        token_hash="a" * 64,  # 64-char sha256 hex digest
        invited_by_user_id=user.id,
        expires_at=datetime.now(timezone.utc),
    )
    db.add(invitation)
    db.flush()

    assert hasattr(invitation, "token_hash")
    assert not hasattr(invitation, "token")
    assert not hasattr(invitation, "raw_token")
    assert len(invitation.token_hash) == 64


def test_user_profile_unique_auth_subject_id_constraint(db, create_synthetic_user):
    """Verify external auth subject identifier cannot identify multiple user profiles."""
    user1 = create_synthetic_user(
        email="auth1@campus.edu",
        display_name="User One",
        auth_subject_id="auth_ext_unique_12345",
    )
    db.commit()

    with pytest.raises(IntegrityError):
        user2 = UserProfile(
            auth_subject_id="auth_ext_unique_12345",  # Duplicate external subject ID
            email_normalized="auth2@campus.edu",
            display_name="User Two",
            email_verified_at=datetime.now(timezone.utc),
            account_status="active",
        )
        db.add(user2)
        db.commit()
    db.rollback()
