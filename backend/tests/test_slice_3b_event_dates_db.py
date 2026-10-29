import uuid
from datetime import date, datetime, timezone
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.organization import Organization
from app.models.user import UserProfile


@pytest.fixture
def org_and_user(db: Session):
    """Fixture providing a verified organization and active user profile."""
    now = datetime.now(timezone.utc)
    user = UserProfile(
        auth_subject_id=f"user_{uuid.uuid4().hex[:8]}",
        email_normalized=f"user_{uuid.uuid4().hex[:8]}@example.edu",
        display_name="Test Creator",
        account_status="active",
        email_verified_at=now,
    )
    db.add(user)
    db.flush()

    org = Organization(
        college_name="Engineering College",
        club_name=f"Robotics Club {uuid.uuid4().hex[:6]}",
        verification_status="verified",
        verification_reviewed_at=now,
        created_by_user_id=user.id,
    )
    db.add(org)
    db.commit()
    return org, user


def test_db_permits_valid_single_day_event(db: Session, org_and_user):
    org, user = org_and_user
    now = datetime.now(timezone.utc)
    ev = Event(
        organization_id=org.id,
        name="Valid Single Day",
        event_date=date(2026, 11, 10),
        event_end_date=None,
        planned_start_time=datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc),
        planned_end_time=datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc),
        created_by_user_id=user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(ev)
    db.commit()
    assert ev.id is not None
    assert ev.event_end_date is None


def test_db_permits_explicit_same_day_end_date(db: Session, org_and_user):
    org, user = org_and_user
    now = datetime.now(timezone.utc)
    ev = Event(
        organization_id=org.id,
        name="Explicit Single Day",
        event_date=date(2026, 11, 10),
        event_end_date=date(2026, 11, 10),
        planned_start_time=datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc),
        planned_end_time=datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc),
        created_by_user_id=user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(ev)
    db.commit()
    assert ev.id is not None


def test_db_blocks_single_day_event_with_inverted_times(db: Session, org_and_user):
    org, user = org_and_user
    org_id = org.id
    user_id = user.id
    now = datetime.now(timezone.utc)

    with pytest.raises(IntegrityError):
        with db.begin_nested():
            ev = Event(
                organization_id=org_id,
                name="Inverted Single Day Times",
                event_date=date(2026, 11, 10),
                event_end_date=None,
                planned_start_time=datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc),
                planned_end_time=datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc),
                created_by_user_id=user_id,
                created_at=now,
                updated_at=now,
            )
            db.add(ev)
            db.flush()


def test_db_blocks_explicit_same_day_inverted_times(db: Session, org_and_user):
    org, user = org_and_user
    org_id = org.id
    user_id = user.id
    now = datetime.now(timezone.utc)

    with pytest.raises(IntegrityError):
        with db.begin_nested():
            ev = Event(
                organization_id=org_id,
                name="Inverted Explicit Same Day Times",
                event_date=date(2026, 11, 10),
                event_end_date=date(2026, 11, 10),
                planned_start_time=datetime(2026, 11, 10, 18, 0, tzinfo=timezone.utc),
                planned_end_time=datetime(2026, 11, 10, 2, 0, tzinfo=timezone.utc),
                created_by_user_id=user_id,
                created_at=now,
                updated_at=now,
            )
            db.add(ev)
            db.flush()


def test_db_blocks_invalid_date_ordering(db: Session, org_and_user):
    org, user = org_and_user
    org_id = org.id
    user_id = user.id
    now = datetime.now(timezone.utc)

    with pytest.raises(IntegrityError):
        with db.begin_nested():
            ev = Event(
                organization_id=org_id,
                name="Inverted Dates",
                event_date=date(2026, 11, 10),
                event_end_date=date(2026, 11, 9),  # earlier than start date
                created_by_user_id=user_id,
                created_at=now,
                updated_at=now,
            )
            db.add(ev)
            db.flush()


def test_db_permits_multi_day_overnight_schedule(db: Session, org_and_user):
    """
    Key D-SLICE3-05 invariant:
    A multi-day event may end at an earlier clock time than it starts,
    provided its end date is strictly later than its start date.
    """
    org, user = org_and_user
    now = datetime.now(timezone.utc)
    ev = Event(
        organization_id=org.id,
        name="Hackathon Overnight",
        event_date=date(2026, 11, 10),
        event_end_date=date(2026, 11, 11),  # next day
        planned_start_time=datetime(2026, 11, 10, 18, 0, tzinfo=timezone.utc),  # 6 PM
        planned_end_time=datetime(2026, 11, 10, 2, 0, tzinfo=timezone.utc),    # 2 AM (earlier clock time)
        created_by_user_id=user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(ev)
    db.commit()
    assert ev.id is not None
    assert ev.event_end_date == date(2026, 11, 11)


def test_db_permits_unfinalized_times(db: Session, org_and_user):
    org, user = org_and_user
    now = datetime.now(timezone.utc)
    ev = Event(
        organization_id=org.id,
        name="Unfinalized Times Multi-Day",
        event_date=date(2026, 11, 10),
        event_end_date=date(2026, 11, 13),
        planned_start_time=None,
        planned_end_time=None,
        created_by_user_id=user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(ev)
    db.commit()
    assert ev.id is not None
    assert ev.planned_start_time is None
    assert ev.planned_end_time is None
