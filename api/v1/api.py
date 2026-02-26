"""
API v1 router configuration
"""

from fastapi import APIRouter
from .endpoints import applications, alerts, dashboards, deployments, coverage, compliance, auth, synthetics, frontend, backend, infrastructure, microservices, transactions

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

api_router.include_router(
    synthetics.router,
    tags=["Synthetic Monitoring"]
)

api_router.include_router(
    frontend.router,
    tags=["Frontend Monitoring"]
)

api_router.include_router(
    backend.router,
    tags=["Backend Monitoring"]
)

api_router.include_router(
    infrastructure.router,
    tags=["Infrastructure Monitoring"]
)

api_router.include_router(
    microservices.router,
    tags=["Microservices Monitoring"]
)

api_router.include_router(
    transactions.router,
    tags=["Transaction Monitoring"]
)
