"""
Dashboard management endpoints
"""

from fastapi import APIRouter, Depends, Query, Path, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog

from api.database import get_db
from api.models import Application, Dashboard
from api.schemas import (
    Dashboard, DashboardCreate, DashboardUpdate
)
from api.auth import verify_api_key, require_permissions
from api.exceptions import DashboardNotFoundError, ApplicationNotFoundError
from api.monitoring import track_requests

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/applications/{application_id}/dashboards", response_model=Dashboard, status_code=201)
@track_requests
async def create_dashboard(
    application_id: str = Path(..., description="Application ID"),
    dashboard_data: DashboardCreate = None,
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Create a new dashboard for an application.
    
    - **name**: Dashboard name (required)
    - **type**: Dashboard type (infrastructure, application_performance, error_analysis, business_metrics)
    - **description**: Optional description
    - **widgets**: List of widget configurations (required)
    """
    # Verify application exists
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise ApplicationNotFoundError(application_id)
    
    # Check if dashboard with same name already exists for this application
    existing_dashboard = db.query(Dashboard).filter(
        Dashboard.application_id == application_id,
        Dashboard.name == dashboard_data.name
    ).first()
    
    if existing_dashboard:
        raise HTTPException(
            status_code=409,
            detail="Dashboard with this name already exists for this application"
        )
    
    dashboard = Dashboard(
        application_id=application_id,
        name=dashboard_data.name,
        type=dashboard_data.type,
        description=dashboard_data.description,
        widgets=dashboard_data.widgets,
        widgets_count=len(dashboard_data.widgets)
    )
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    
    logger.info(
        "Created dashboard",
        dashboard_id=dashboard.id,
        application_id=application_id,
        name=dashboard.name,
        type=dashboard.type
    )
    
    return dashboard


@router.get("/dashboards/{dashboard_id}", response_model=Dashboard)
@track_requests
async def get_dashboard(
    dashboard_id: str = Path(..., description="Dashboard ID"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Retrieve a specific dashboard by ID.
    """
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    
    if not dashboard:
        raise DashboardNotFoundError(dashboard_id)
    
    logger.info(
        "Retrieved dashboard",
        dashboard_id=dashboard_id,
        name=dashboard.name
    )
    
    return dashboard


@router.put("/dashboards/{dashboard_id}", response_model=Dashboard)
@track_requests
async def update_dashboard(
    dashboard_id: str = Path(..., description="Dashboard ID"),
    dashboard_data: DashboardUpdate = None,
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Update an existing dashboard.
    
    All fields are optional. Only provided fields will be updated.
    """
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    
    if not dashboard:
        raise DashboardNotFoundError(dashboard_id)
    
    # Update only provided fields
    update_data = dashboard_data.dict(exclude_unset=True)
    
    # Update widgets_count if widgets are provided
    if "widgets" in update_data:
        update_data["widgets_count"] = len(update_data["widgets"])
    
    for field, value in update_data.items():
        setattr(dashboard, field, value)
    
    db.commit()
    db.refresh(dashboard)
    
    logger.info(
        "Updated dashboard",
        dashboard_id=dashboard_id,
        updated_fields=list(update_data.keys())
    )
    
    return dashboard


@router.delete("/dashboards/{dashboard_id}", status_code=204)
@track_requests
async def delete_dashboard(
    dashboard_id: str = Path(..., description="Dashboard ID"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["delete"]))
):
    """
    Delete a dashboard.
    """
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    
    if not dashboard:
        raise DashboardNotFoundError(dashboard_id)
    
    db.delete(dashboard)
    db.commit()
    
    logger.info(
        "Deleted dashboard",
        dashboard_id=dashboard_id,
        name=dashboard.name
    )


@router.get("/dashboards")
@track_requests
async def list_dashboards(
    application_id: Optional[str] = Query(None, description="Filter by application ID"),
    dashboard_type: Optional[str] = Query(None, description="Filter by dashboard type"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for dashboard names"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Retrieve a paginated list of dashboards with optional filtering.
    
    - **application_id**: Filter by specific application
    - **dashboard_type**: Filter by dashboard type
    - **page**: Page number for pagination
    - **limit**: Number of items per page (max 100)
    - **search**: Search term for dashboard names
    """
    query = db.query(Dashboard)
    
    # Apply filters
    if application_id:
        query = query.filter(Dashboard.application_id == application_id)
    
    if dashboard_type:
        query = query.filter(Dashboard.type == dashboard_type)
    
    if search:
        query = query.filter(Dashboard.name.ilike(f"%{search}%"))
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    dashboards = query.offset(offset).limit(limit).all()
    
    logger.info(
        "Retrieved dashboards",
        application_id=application_id,
        dashboard_type=dashboard_type,
        page=page,
        limit=limit,
        total=total
    )
    
    return {
        "dashboards": dashboards,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    }


@router.post("/dashboards/{dashboard_id}/clone", response_model=Dashboard, status_code=201)
@track_requests
async def clone_dashboard(
    dashboard_id: str = Path(..., description="Dashboard ID"),
    clone_data: dict = None,
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Clone a dashboard to a different application.
    
    - **application_id**: Target application ID
    - **name**: Optional new name (defaults to original name)
    """
    original_dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    
    if not original_dashboard:
        raise DashboardNotFoundError(dashboard_id)
    
    target_application_id = clone_data.get("application_id")
    new_name = clone_data.get("name", f"{original_dashboard.name} (Clone)")
    
    # Verify target application exists
    target_app = db.query(Application).filter(Application.id == target_application_id).first()
    if not target_app:
        raise ApplicationNotFoundError(target_application_id)
    
    # Check if clone already exists
    existing_clone = db.query(Dashboard).filter(
        Dashboard.application_id == target_application_id,
        Dashboard.name == new_name
    ).first()
    
    if existing_clone:
        raise HTTPException(
            status_code=409,
            detail="Dashboard with this name already exists in the target application"
        )
    
    # Create cloned dashboard
    cloned_dashboard = Dashboard(
        application_id=target_application_id,
        name=new_name,
        type=original_dashboard.type,
        description=original_dashboard.description,
        widgets=original_dashboard.widgets,
        widgets_count=original_dashboard.widgets_count
    )
    
    db.add(cloned_dashboard)
    db.commit()
    db.refresh(cloned_dashboard)
    
    logger.info(
        "Cloned dashboard",
        original_dashboard_id=dashboard_id,
        cloned_dashboard_id=cloned_dashboard.id,
        target_application_id=target_application_id
    )
    
    return cloned_dashboard


@router.get("/dashboards/types")
@track_requests
async def get_dashboard_types(
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Get available dashboard types with descriptions and sample widgets.
    """
    dashboard_types = {
        "infrastructure": {
            "name": "Infrastructure Monitoring",
            "description": "System infrastructure metrics and health",
            "sample_widgets": [
                {
                    "title": "CPU Usage",
                    "visualization": "line_chart",
                    "nrql": "SELECT average(cpuPercent) FROM SystemSample FACET hostname"
                },
                {
                    "title": "Memory Usage",
                    "visualization": "area_chart",
                    "nrql": "SELECT average(memoryUsedPercent) FROM SystemSample FACET hostname"
                },
                {
                    "title": "Disk Usage",
                    "visualization": "billboard",
                    "nrql": "SELECT average(diskUsedPercent) FROM SystemSample"
                }
            ]
        },
        "application_performance": {
            "name": "Application Performance",
            "description": "Application performance and user experience metrics",
            "sample_widgets": [
                {
                    "title": "Response Time",
                    "visualization": "line_chart",
                    "nrql": "SELECT percentile(duration, 50, 95, 99) FROM Transaction"
                },
                {
                    "title": "Throughput",
                    "visualization": "line_chart",
                    "nrql": "SELECT count(*) FROM Transaction"
                },
                {
                    "title": "Apdex Score",
                    "visualization": "billboard",
                    "nrql": "SELECT apdex(duration, t: 0.5) FROM Transaction"
                }
            ]
        },
        "error_analysis": {
            "name": "Error Analysis",
            "description": "Error tracking and analysis",
            "sample_widgets": [
                {
                    "title": "Error Rate",
                    "visualization": "line_chart",
                    "nrql": "SELECT percentage(count(*), WHERE error IS true) FROM Transaction"
                },
                {
                    "title": "Error Count by Type",
                    "visualization": "pie_chart",
                    "nrql": "SELECT count(*) FROM JavaScriptError FACET errorMessage"
                },
                {
                    "title": "HTTP Status Codes",
                    "visualization": "bar_chart",
                    "nrql": "SELECT count(*) FROM Transaction FACET httpResponseCode"
                }
            ]
        },
        "business_metrics": {
            "name": "Business Metrics",
            "description": "Business KPIs and custom metrics",
            "sample_widgets": [
                {
                    "title": "User Registrations",
                    "visualization": "line_chart",
                    "nrql": "SELECT count(*) FROM CustomEvent WHERE eventType = 'UserRegistration'"
                },
                {
                    "title": "Revenue",
                    "visualization": "line_chart",
                    "nrql": "SELECT sum(revenue) FROM CustomEvent WHERE eventType = 'Purchase'"
                },
                {
                    "title": "Conversion Rate",
                    "visualization": "billboard",
                    "nrql": "SELECT percentage(count(*), WHERE eventType = 'Purchase') FROM CustomEvent"
                }
            ]
        }
    }
    
    return dashboard_types


@router.post("/dashboards/{dashboard_id}/widgets", response_model=Dashboard)
@track_requests
async def add_widget(
    dashboard_id: str = Path(..., description="Dashboard ID"),
    widget_data: dict = None,
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Add a widget to an existing dashboard.
    
    - **widget**: Widget configuration object
    """
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    
    if not dashboard:
        raise DashboardNotFoundError(dashboard_id)
    
    # Add new widget to widgets list
    dashboard.widgets.append(widget_data)
    dashboard.widgets_count = len(dashboard.widgets)
    
    db.commit()
    db.refresh(dashboard)
    
    logger.info(
        "Added widget to dashboard",
        dashboard_id=dashboard_id,
        widget_title=widget_data.get("title"),
        total_widgets=dashboard.widgets_count
    )
    
    return dashboard


@router.delete("/dashboards/{dashboard_id}/widgets/{widget_index}", response_model=Dashboard)
@track_requests
async def remove_widget(
    dashboard_id: str = Path(..., description="Dashboard ID"),
    widget_index: int = Path(..., description="Widget index"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Remove a widget from a dashboard by index.
    """
    dashboard = db.query(Dashboard).filter(Dashboard.id == dashboard_id).first()
    
    if not dashboard:
        raise DashboardNotFoundError(dashboard_id)
    
    if widget_index < 0 or widget_index >= len(dashboard.widgets):
        raise HTTPException(
            status_code=400,
            detail="Invalid widget index"
        )
    
    # Remove widget
    removed_widget = dashboard.widgets.pop(widget_index)
    dashboard.widgets_count = len(dashboard.widgets)
    
    db.commit()
    db.refresh(dashboard)
    
    logger.info(
        "Removed widget from dashboard",
        dashboard_id=dashboard_id,
        widget_index=widget_index,
        widget_title=removed_widget.get("title"),
        total_widgets=dashboard.widgets_count
    )
    
    return dashboard
