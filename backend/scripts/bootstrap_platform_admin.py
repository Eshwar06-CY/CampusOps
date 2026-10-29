"""
Operational CLI script for initial Platform Administrator bootstrap.

Safety and Governance Rules:
- Server-side only: never exposed as an HTTP route or API endpoint.
- Strictly no hardcoded passwords, backdoor tokens, or auto-created unverified users.
- Target user must already exist in the database with an active account and verified email.
- Can only bootstrap without an appointing administrator if ZERO active platform administrators exist.
- Once an active platform administrator exists, all subsequent appointments require an appointing administrator.

Usage:
    python -m scripts.bootstrap_platform_admin <user_email> [--notes "Initial operator bootstrap"]
"""

import argparse
import sys
from sqlalchemy import select

from app.database import SessionLocal
from app.models.user import UserProfile
from app.services.platform import appoint_platform_admin
from app.services.errors import PermissionDeniedError


def bootstrap_admin(email: str, notes: str = "Initial platform operator bootstrap") -> int:
    norm_email = email.strip().lower()
    db = SessionLocal()
    try:
        user = db.execute(
            select(UserProfile).where(UserProfile.email_normalized == norm_email)
        ).scalar_one_or_none()

        if not user:
            print(f"Error: User with email '{norm_email}' not found.", file=sys.stderr)
            print("Target user must already be registered and have a verified email.", file=sys.stderr)
            return 1

        if user.account_status != "active":
            print(f"Error: User account '{norm_email}' is not active.", file=sys.stderr)
            return 1

        if user.email_verified_at is None:
            print(f"Error: User '{norm_email}' does not have a verified email address.", file=sys.stderr)
            return 1

        admin = appoint_platform_admin(
            db=db,
            target_user=user,
            appointing_admin=None,
            notes=notes,
        )
        print(f"Successfully appointed Platform Administrator: {user.email_normalized} (ID: {admin.id})")
        return 0
    except PermissionDeniedError as err:
        print(f"Security Rejection: {err}", file=sys.stderr)
        print("Initial bootstrap is blocked because active platform administrators already exist.", file=sys.stderr)
        return 2
    except Exception as err:
        print(f"Unexpected Error during bootstrap: {err}", file=sys.stderr)
        return 3
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Bootstrap initial Platform Administrator")
    parser.add_argument("email", help="Normalized email of existing, email-verified user")
    parser.add_argument("--notes", default="Initial platform operator bootstrap", help="Audit notes")
    args = parser.parse_args()

    sys.exit(bootstrap_admin(args.email, args.notes))


if __name__ == "__main__":
    main()

