"""
Application management endpoints
"""

from fastapi import APIRouter, Depends, Query, Path, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog

from api.database import get_db
from api.models import Application, Alert, Dashboard
from api.schemas import (
    Application, ApplicationCreate, ApplicationUpdate, ApplicationList
)
from api.auth import verify_api_key, require_permissions
from api.exceptions import ApplicationNotFoundError
from api.monitoring import track_requests

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/", response_model=ApplicationList)
@track_requests
async def get_applications(
    environment: Optional[str] = Query(None, description="Filter by environment"),
    status: Optional[str] = Query(None, description="Filter by status"),
    team: Optional[str] = Query(None, description="Filter by team"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Retrieve a paginated list of applications.
    
    - **environment**: Filter by environment (production, staging, development)
    - **status**: Filter by status (active, inactive)
    - **team**: Filter by team name
    - **page**: Page number for pagination
    - **limit**: Number of items per page (max 100)
    - **search**: Search term for application names
    """
    query = db.query(Application)
    
    # Apply filters
    if environment:
        query = query.filter(Application.environment == environment)
    
    if status:
        query = query.filter(Application.status == status)
    
    if team:
        query = query.filter(Application.team == team)
    
    if search:
        query = query.filter(Application.name.ilike(f"%{search}%"))
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    applications = query.offset(offset).limit(limit).all()
    
    logger.info(
        "Retrieved applications",
        environment=environment,
        status=status,
        team=team,
        page=page,
        limit=limit,
        total=total
    )
    
    return ApplicationList(
        applications=applications,
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    )


@router.post("/", response_model=Application, status_code=201)
@track_requests
async def create_application(
    application_data: ApplicationCreate,
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Create a new application.
    
    - **name**: Application name (required)
    - **environment**: Environment (production, staging, development)
    - **entity_id**: New Relic entity ID (required)
    - **description**: Optional description
    - **team**: Optional team name
    """
    # Check if application with same name and environment exists
    existing_app = db.query(Application).filter(
        Application.name == application_data.name,
        Application.environment == application_data.environment
    ).first()
    
    if existing_app:
        raise HTTPException(
            status_code=409,
            detail="Application with this name already exists in the specified environment"
        )
    
    application = Application(**application_data.dict())
    db.add(application)
    db.commit()
    db.refresh(application)
    
    logger.info(
        "Created application",
        application_id=application.id,
        name=application.name,
        environment=application.environment
    )
    
    return application


@router.get("/{application_id}", response_model=Application)
@track_requests
async def get_application(
    application_id: str = Path(..., description="Application ID"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Retrieve a specific application by ID.
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise ApplicationNotFoundError(application_id)
    
    logger.info(
        "Retrieved application",
        application_id=application_id,
        name=application.name
    )
    
    return application


@router.put("/{application_id}", response_model=Application)
@track_requests
async def update_application(
    application_id: str = Path(..., description="Application ID"),
    application_data: ApplicationUpdate = None,
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Update an existing application.
    
    All fields are optional. Only provided fields will be updated.
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise ApplicationNotFoundError(application_id)
    
    # Update only provided fields
    update_data = application_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(application, field, value)
    
    db.commit()
    db.refresh(application)
    
    logger.info(
        "Updated application",
        application_id=application_id,
        updated_fields=list(update_data.keys())
    )
    
    return application


@router.delete("/{application_id}", status_code=204)
@track_requests
async def delete_application(
    application_id: str = Path(..., description="Application ID"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["delete"]))
):
    """
    Delete an application and all associated alerts and dashboards.
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise ApplicationNotFoundError(application_id)
    
    # Delete associated alerts and dashboards (cascade delete)
    db.delete(application)
    db.commit()
    
    logger.info(
        "Deleted application",
        application_id=application_id,
        name=application.name
    )


@router.get("/{application_id}/alerts")
@track_requests
async def get_application_alerts(
    application_id: str = Path(..., description="Application ID"),
    enabled_only: bool = Query(False, description="Filter enabled alerts only"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Retrieve all alerts for a specific application.
    """
    # Verify application exists
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise ApplicationNotFoundError(application_id)
    
    query = db.query(Alert).filter(Alert.application_id == application_id)
    
    if enabled_only:
        query = query.filter(Alert.enabled == True)
    
    if alert_type:
        query = query.filter(Alert.type == alert_type)
    
    alerts = query.all()
    
    logger.info(
        "Retrieved application alerts",
        application_id=application_id,
        alert_count=len(alerts),
        enabled_only=enabled_only,
        alert_type=alert_type
    )
    
    return {"alerts": alerts}


@router.get("/{application_id}/dashboards")
@track_requests
async def get_application_dashboards(
    application_id: str = Path(..., description="Application ID"),
    dashboard_type: Optional[str] = Query(None, description="Filter by dashboard type"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Retrieve all dashboards for a specific application.
    """
    # Verify application exists
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise ApplicationNotFoundError(application_id)
    
    query = db.query(Dashboard).filter(Dashboard.application_id == application_id)
    
    if dashboard_type:
        query = query.filter(Dashboard.type == dashboard_type)
    
    dashboards = query.all()
    
    logger.info(
        "Retrieved application dashboards",
        application_id=application_id,
        dashboard_count=len(dashboards),
        dashboard_type=dashboard_type
    )
    
    return {"dashboards": dashboards}


@router.post("/{application_id}/clone", response_model=Application, status_code=201)
@track_requests
async def clone_application(
    application_id: str = Path(..., description="Application ID"),
    clone_data: dict = None,
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Clone an application to a different environment.
    
    - **environment**: Target environment for the clone
    - **name**: Optional new name (defaults to original name)
    """
    original_app = db.query(Application).filter(Application.id == application_id).first()
    
    if not original_app:
        raise ApplicationNotFoundError(application_id)
    
    target_environment = clone_data.get("environment")
    new_name = clone_data.get("name", f"{original_app.name} (Clone)")
    
    # Check if clone already exists
    existing_clone = db.query(Application).filter(
        Application.name == new_name,
        Application.environment == target_environment
    ).first()
    
    if existing_clone:
        raise HTTPException(
            status_code=409,
            detail="Application with this name already exists in the target environment"
        )
    
    # Create cloned application
    cloned_app = Application(
        name=new_name,
        environment=target_environment,
        entity_id=clone_data.get("entity_id", original_app.entity_id),
        description=original_app.description,
        team=original_app.team,
        status="active"
    )
    
    db.add(cloned_app)
    db.commit()
    db.refresh(cloned_app)
    
    # Clone alerts
    original_alerts = db.query(Alert).filter(Alert.application_id == application_id).all()
    for alert in original_alerts:
        cloned_alert = Alert(
            application_id=cloned_app.id,
            name=alert.name,
            type=alert.type,
            enabled=alert.enabled,
            nrql_query=alert.nrql_query,
            thresholds=alert.thresholds,
            severity=alert.severity
        )
        db.add(cloned_alert)
    
    # Clone dashboards
    original_dashboards = db.query(Dashboard).filter(Dashboard.application_id == application_id).all()
    for dashboard in original_dashboards:
        cloned_dashboard = Dashboard(
            application_id=cloned_app.id,
            name=dashboard.name,
            type=dashboard.type,
            description=dashboard.description,
            widgets=dashboard.widgets,
            widgets_count=dashboard.widgets_count
        )
        db.add(cloned_dashboard)
    
    db.commit()
    
    logger.info(
        "Cloned application",
        original_application_id=application_id,
        cloned_application_id=cloned_app.id,
        target_environment=target_environment
    )
    
    return cloned_app
