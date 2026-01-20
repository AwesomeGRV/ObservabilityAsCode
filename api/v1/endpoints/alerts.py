"""
Alert management endpoints
"""

from fastapi import APIRouter, Depends, Query, Path, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog

from api.database import get_db
from api.models import Application, Alert
from api.schemas import (
    Alert, AlertCreate, AlertUpdate
)
from api.auth import verify_api_key, require_permissions
from api.exceptions import AlertNotFoundError, ApplicationNotFoundError
from api.monitoring import track_requests

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/applications/{application_id}/alerts", response_model=Alert, status_code=201)
@track_requests
async def create_alert(
    application_id: str = Path(..., description="Application ID"),
    alert_data: AlertCreate = None,
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Create a new alert for an application.
    
    - **name**: Alert name (required)
    - **type**: Alert type (cpu_usage, memory_usage, disk_usage, response_time, error_rate, pod_health)
    - **nrql_query**: NRQL query for the alert (required)
    - **thresholds**: Alert thresholds object (required)
    - **enabled**: Whether alert is enabled (default: true)
    - **severity**: Alert severity (critical, warning, info)
    """
    # Verify application exists
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise ApplicationNotFoundError(application_id)
    
    # Check if alert with same name already exists for this application
    existing_alert = db.query(Alert).filter(
        Alert.application_id == application_id,
        Alert.name == alert_data.name
    ).first()
    
    if existing_alert:
        raise HTTPException(
            status_code=409,
            detail="Alert with this name already exists for this application"
        )
    
    alert = Alert(
        application_id=application_id,
        **alert_data.dict()
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    logger.info(
        "Created alert",
        alert_id=alert.id,
        application_id=application_id,
        name=alert.name,
        type=alert.type
    )
    
    return alert


@router.get("/alerts/{alert_id}", response_model=Alert)
@track_requests
async def get_alert(
    alert_id: str = Path(..., description="Alert ID"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Retrieve a specific alert by ID.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise AlertNotFoundError(alert_id)
    
    logger.info(
        "Retrieved alert",
        alert_id=alert_id,
        name=alert.name
    )
    
    return alert


@router.put("/alerts/{alert_id}", response_model=Alert)
@track_requests
async def update_alert(
    alert_id: str = Path(..., description="Alert ID"),
    alert_data: AlertUpdate = None,
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Update an existing alert.
    
    All fields are optional. Only provided fields will be updated.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise AlertNotFoundError(alert_id)
    
    # Update only provided fields
    update_data = alert_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)
    
    db.commit()
    db.refresh(alert)
    
    logger.info(
        "Updated alert",
        alert_id=alert_id,
        updated_fields=list(update_data.keys())
    )
    
    return alert


@router.delete("/alerts/{alert_id}", status_code=204)
@track_requests
async def delete_alert(
    alert_id: str = Path(..., description="Alert ID"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["delete"]))
):
    """
    Delete an alert.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise AlertNotFoundError(alert_id)
    
    db.delete(alert)
    db.commit()
    
    logger.info(
        "Deleted alert",
        alert_id=alert_id,
        name=alert.name
    )


@router.get("/alerts")
@track_requests
async def list_alerts(
    application_id: Optional[str] = Query(None, description="Filter by application ID"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    enabled_only: bool = Query(False, description="Filter enabled alerts only"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Retrieve a paginated list of alerts with optional filtering.
    
    - **application_id**: Filter by specific application
    - **alert_type**: Filter by alert type
    - **enabled_only**: Show only enabled alerts
    - **severity**: Filter by severity level
    - **page**: Page number for pagination
    - **limit**: Number of items per page (max 100)
    """
    query = db.query(Alert)
    
    # Apply filters
    if application_id:
        query = query.filter(Alert.application_id == application_id)
    
    if alert_type:
        query = query.filter(Alert.type == alert_type)
    
    if enabled_only:
        query = query.filter(Alert.enabled == True)
    
    if severity:
        query = query.filter(Alert.severity == severity)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    alerts = query.offset(offset).limit(limit).all()
    
    logger.info(
        "Retrieved alerts",
        application_id=application_id,
        alert_type=alert_type,
        enabled_only=enabled_only,
        severity=severity,
        page=page,
        limit=limit,
        total=total
    )
    
    return {
        "alerts": alerts,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    }


@router.post("/alerts/{alert_id}/enable", response_model=Alert)
@track_requests
async def enable_alert(
    alert_id: str = Path(..., description="Alert ID"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Enable an alert.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise AlertNotFoundError(alert_id)
    
    alert.enabled = True
    db.commit()
    db.refresh(alert)
    
    logger.info(
        "Enabled alert",
        alert_id=alert_id,
        name=alert.name
    )
    
    return alert


@router.post("/alerts/{alert_id}/disable", response_model=Alert)
@track_requests
async def disable_alert(
    alert_id: str = Path(..., description="Alert ID"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Disable an alert.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    
    if not alert:
        raise AlertNotFoundError(alert_id)
    
    alert.enabled = False
    db.commit()
    db.refresh(alert)
    
    logger.info(
        "Disabled alert",
        alert_id=alert_id,
        name=alert.name
    )
    
    return alert


@router.post("/alerts/batch-update")
@track_requests
async def batch_update_alerts(
    batch_data: dict = None,
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Update multiple alerts at once.
    
    - **alert_ids**: List of alert IDs to update
    - **updates**: Dictionary of fields to update
    - **filters**: Optional filters to select alerts (alternative to alert_ids)
    """
    alert_ids = batch_data.get("alert_ids", [])
    updates = batch_data.get("updates", {})
    filters = batch_data.get("filters", {})
    
    if not alert_ids and not filters:
        raise HTTPException(
            status_code=400,
            detail="Either alert_ids or filters must be provided"
        )
    
    query = db.query(Alert)
    
    if alert_ids:
        query = query.filter(Alert.id.in_(alert_ids))
    
    if filters:
        if "application_id" in filters:
            query = query.filter(Alert.application_id == filters["application_id"])
        if "alert_type" in filters:
            query = query.filter(Alert.type == filters["alert_type"])
        if "enabled" in filters:
            query = query.filter(Alert.enabled == filters["enabled"])
        if "severity" in filters:
            query = query.filter(Alert.severity == filters["severity"])
    
    alerts = query.all()
    
    if not alerts:
        return {"updated_count": 0, "alerts": []}
    
    # Update alerts
    for alert in alerts:
        for field, value in updates.items():
            if hasattr(alert, field):
                setattr(alert, field, value)
    
    db.commit()
    
    logger.info(
        "Batch updated alerts",
        alert_count=len(alerts),
        updates=updates
    )
    
    return {
        "updated_count": len(alerts),
        "alerts": alerts
    }


@router.get("/alerts/types")
@track_requests
async def get_alert_types(
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Get available alert types with descriptions.
    """
    alert_types = {
        "cpu_usage": {
            "name": "CPU Usage",
            "description": "Monitors CPU utilization percentage",
            "default_thresholds": {"critical": 80, "warning": 60},
            "recommended_nrql": "SELECT average(cpuPercent) FROM SystemSample"
        },
        "memory_usage": {
            "name": "Memory Usage",
            "description": "Monitors memory utilization percentage",
            "default_thresholds": {"critical": 85, "warning": 70},
            "recommended_nrql": "SELECT average(memoryUsedPercent) FROM SystemSample"
        },
        "disk_usage": {
            "name": "Disk Usage",
            "description": "Monitors disk utilization percentage",
            "default_thresholds": {"critical": 90, "warning": 75},
            "recommended_nrql": "SELECT average(diskUsedPercent) FROM SystemSample"
        },
        "response_time": {
            "name": "Response Time",
            "description": "Monitors application response time",
            "default_thresholds": {"critical": 2.0, "warning": 1.0},
            "recommended_nrql": "SELECT average(duration) FROM Transaction"
        },
        "error_rate": {
            "name": "Error Rate",
            "description": "Monitors application error rate percentage",
            "default_thresholds": {"critical": 5.0, "warning": 2.0},
            "recommended_nrql": "SELECT percentage(count(*), WHERE error IS true) FROM Transaction"
        },
        "pod_health": {
            "name": "Pod Health",
            "description": "Monitors Kubernetes pod restarts",
            "default_thresholds": {"critical": 5, "warning": 2},
            "recommended_nrql": "SELECT count(kubernetes.restartCount) FROM K8sPodSample"
        }
    }
    
    return alert_types
