from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.services.errors import (
    DomainError,
    DuplicateMembershipError,
    InvitationEmailMismatchError,
    InvitationError,
    InvitationNotFoundError,
    OrganizationVerificationError,
    PermissionDeniedError,
)

app = FastAPI(
    title="CampusOps API",
    version="0.1.0",
    description="CampusOps event operations management backend",
)


@app.exception_handler(PermissionDeniedError)
def permission_denied_handler(request: Request, exc: PermissionDeniedError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": str(exc)},
    )


@app.exception_handler(DuplicateMembershipError)
def duplicate_membership_handler(request: Request, exc: DuplicateMembershipError):
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


@app.exception_handler(InvitationNotFoundError)
def invitation_not_found_handler(request: Request, exc: InvitationNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


@app.exception_handler(OrganizationVerificationError)
def org_verification_handler(request: Request, exc: OrganizationVerificationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.exception_handler(DomainError)
def domain_error_handler(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(api_router, prefix="/api/v1")
