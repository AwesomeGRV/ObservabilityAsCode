"""
API v1 router configuration
"""

from fastapi import APIRouter
from .endpoints import applications, alerts, dashboards, deployments, coverage, compliance, auth

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

api_router.include_router(
    applications.router,
    prefix="/applications",
    tags=["Applications"]
)

api_router.include_router(
    alerts.router,
    tags=["Alerts"]
)

api_router.include_router(
    dashboards.router,
    prefix="/dashboards",
    tags=["Dashboards"]
)

api_router.include_router(
    deployments.router,
    prefix="/deployments",
    tags=["Deployments"]
)

api_router.include_router(
    coverage.router,
    prefix="/coverage",
    tags=["Coverage"]
)

api_router.include_router(
    compliance.router,
    prefix="/compliance",
    tags=["Compliance"]
)
