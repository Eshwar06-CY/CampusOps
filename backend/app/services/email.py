import abc
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class DeliveredEmailRecord:
    recipient_email: str
    organization_name: str
    role_name: str
    raw_token: str
    expires_at: datetime


class EmailDeliveryService(abc.ABC):
    @abc.abstractmethod
    def is_configured(self) -> bool:
        """Returns True if a delivery adapter is configured and verified."""
        pass

    @abc.abstractmethod
    def send_invitation_email(
        self,
        recipient_email: str,
        organization_name: str,
        role_name: str,
        raw_token: str,
        expires_at: datetime,
    ) -> bool:
        """Sends an invitation email containing the acceptance token."""
        pass


class DefaultEmailDeliveryService(EmailDeliveryService):
    """
    Default email service for CampusOps.
    Transactional email provider selection (FPC-06) is deferred in this slice.
    Returns is_configured() == False to fail closed in production.
    """
    def is_configured(self) -> bool:
        return False

    def send_invitation_email(
        self,
        recipient_email: str,
        organization_name: str,
        role_name: str,
        raw_token: str,
        expires_at: datetime,
    ) -> bool:
        return False


class TestEmailDeliverySink(EmailDeliveryService):
    """
    In-memory email delivery sink for automated integration tests.
    Captures invitations for test assertions without public token disclosure.
    """
    def __init__(self):
        self.sent_messages: List[DeliveredEmailRecord] = []

    def is_configured(self) -> bool:
        return True

    def send_invitation_email(
        self,
        recipient_email: str,
        organization_name: str,
        role_name: str,
        raw_token: str,
        expires_at: datetime,
    ) -> bool:
        self.sent_messages.append(
            DeliveredEmailRecord(
                recipient_email=recipient_email,
                organization_name=organization_name,
                role_name=role_name,
                raw_token=raw_token,
                expires_at=expires_at,
            )
        )
        return True

    def get_latest_token_for(self, email: str) -> Optional[str]:
        for msg in reversed(self.sent_messages):
            if msg.recipient_email.strip().lower() == email.strip().lower():
                return msg.raw_token
        return None

    def clear(self):
        self.sent_messages.clear()


_default_email_service = DefaultEmailDeliveryService()


def get_email_service() -> EmailDeliveryService:
    return _default_email_service
