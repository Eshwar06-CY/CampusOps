from fastapi import APIRouter

from app.api.v1.endpoints import (
    blockers,
    departments,
    events,
    invitations,
    me,
    notifications,
    organizations,
    programs,
    tasks,
)

api_router = APIRouter()

api_router.include_router(me.router, tags=["Identity"])
api_router.include_router(organizations.router, tags=["Organizations"])
api_router.include_router(programs.router, tags=["Programs"])
api_router.include_router(events.router, tags=["Events"])
api_router.include_router(departments.router, tags=["Departments"])
api_router.include_router(invitations.router, tags=["Invitations"])
api_router.include_router(tasks.router, tags=["Tasks"])
api_router.include_router(blockers.router, tags=["Blockers"])
api_router.include_router(notifications.router, tags=["Notifications"])
