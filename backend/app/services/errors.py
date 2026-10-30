class DomainError(Exception):
    """Base domain exception for CampusOps."""
    pass


class PermissionDeniedError(DomainError):
    """Raised when an actor lacks permission for an operation or scope."""
    pass


class OrganizationVerificationError(DomainError):
    """Raised when an organization verification action is invalid or unauthorized."""
    pass


class InvitationError(DomainError):
    """Base exception for invitation lifecycle failures."""
    pass


class InvitationNotFoundError(InvitationError):
    """Raised when an invitation token hash does not exist."""
    pass


class InvitationInvalidError(InvitationError):
    """Raised when an invitation is not in pending state or has been altered."""
    pass


class InvitationExpiredError(InvitationError):
    """Raised when an invitation has passed its 7-day expiration."""
    pass


class InvitationEmailMismatchError(InvitationError):
    """Raised when the accepting user's email does not match the invitation email."""
    pass


class DuplicateMembershipError(DomainError):
    """Raised when a user is already a member of the organization."""
    pass


class ProgramError(DomainError):
    """Base exception for Program domain errors."""
    pass


class ProgramNotFoundError(ProgramError):
    """Raised when a Program does not exist or is inaccessible."""
    pass


class EventError(DomainError):
    """Base exception for Event domain errors."""
    pass


class EventNotFoundError(EventError):
    """Raised when an Event does not exist or is inaccessible."""
    pass


class DepartmentError(DomainError):
    """Base exception for Department domain errors."""
    pass


class DepartmentNotFoundError(DepartmentError):
    """Raised when a Department does not exist or is inaccessible."""
    pass


class EventLeadError(DomainError):
    """Base exception for EventLead assignment errors."""
    pass


class DuplicateEventLeadError(EventLeadError):
    """Raised when an active Event Lead assignment already exists for the member."""
    pass


class ScopeIntegrityError(DomainError):
    """Raised when cross-tenant or mismatched entity relationships are detected."""
    pass


# =========================================================================
# Slice 4A: Task Management and Operational Blocker Domain Errors
# =========================================================================

class TaskError(DomainError):
    """Base exception for Task domain errors."""
    pass


class TaskNotFoundError(TaskError):
    """Raised when a Task does not exist or is inaccessible."""
    pass


class TaskWorkflowError(TaskError):
    """Raised when an invalid task status transition is attempted."""
    pass


class TaskAssigneeError(TaskError):
    """Raised when task assignment or reassignment rules are violated."""
    pass


class EvidenceSubmissionError(TaskError):
    """Raised when an evidence submission is invalid or violates proof invariants."""
    pass


class ReviewError(TaskError):
    """Base exception for task evidence review errors."""
    pass


class SelfReviewError(ReviewError, PermissionDeniedError):
    """Raised when a task submitter or active assignee attempts to review their own work."""
    pass


class OperationalBlockerError(DomainError):
    """Base exception for Operational Blocker errors."""
    pass


class OperationalBlockerNotFoundError(OperationalBlockerError):
    """Raised when an operational blocker does not exist or is inaccessible."""
    pass


# =========================================================================
# Slice 5B: Registration, Ticketing, and Attendance Domain Errors
# =========================================================================

class RegistrationError(DomainError):
    """Base exception for event registration errors."""
    pass


class RegistrationNotFoundError(RegistrationError):
    """Raised when a Registration does not exist or is inaccessible."""
    pass


class RegistrationClosedError(RegistrationError):
    """Raised when registration is disabled or closed for an event."""
    pass


class RegistrationWindowError(RegistrationError):
    """Raised when registration is attempted outside configured temporal windows."""
    pass


class CapacityExhaustedError(RegistrationError):
    """Raised when an event has reached maximum participant capacity."""
    pass


class InvalidTeamSizeError(RegistrationError):
    """Raised when team size does not conform to event settings."""
    pass


class DuplicateRegistrationError(RegistrationError):
    """Raised when an exact duplicate registration submission is detected."""
    pass


class IdempotencyConflictError(RegistrationError):
    """Raised when an idempotency key is reused with a different payload."""
    pass


class TicketError(DomainError):
    """Base exception for Ticket and admission pass domain errors."""
    pass


class TicketNotFoundError(TicketError):
    """Raised when an admission pass credential cannot be found."""
    pass


class TicketInvalidError(TicketError):
    """Raised when an admission pass credential is tampered, cancelled, or invalid."""
    pass


class TicketRevokedError(TicketError):
    """Raised when an admission pass credential has been revoked."""
    pass


class CheckInError(DomainError):
    """Base exception for attendance check-in errors."""
    pass


class CheckInNotFoundError(CheckInError):
    """Raised when a check-in record does not exist or is inaccessible."""
    pass


class AlreadyCheckedInError(CheckInError):
    """Raised when a participant is already actively checked in."""
    pass


class CheckInCorrectionError(DomainError):
    """Raised when check-in correction or void invariants are violated."""
    pass

