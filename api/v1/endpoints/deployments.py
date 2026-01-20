"""
Deployment management endpoints
"""

from fastapi import APIRouter, Depends, Query, Path, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import structlog

from api.database import get_db
from api.models import Application, Deployment, Alert, Dashboard
from api.schemas import (
    DeploymentCreate, DeploymentResponse, Deployment as DeploymentSchema
)
from api.auth import verify_api_key, require_permissions
from api.exceptions import ApplicationNotFoundError, DeploymentError
from api.monitoring import track_requests

logger = structlog.get_logger(__name__)

router = APIRouter()


async def execute_deployment(
    deployment_id: str,
    application_ids: List[str],
    components: List[str],
    dry_run: bool,
    db: Session
):
    """
    Background task to execute deployment
    """
    try:
        deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
        if not deployment:
            logger.error("Deployment not found", deployment_id=deployment_id)
            return
        
        deployment.status = "running"
        deployment.started_at = datetime.utcnow()
        db.commit()
        
        results = []
        
        for app_id in application_ids:
            app_result = {
                "application_id": app_id,
                "status": "pending",
                "components_deployed": [],
                "error": None
            }
            
            try:
                application = db.query(Application).filter(Application.id == app_id).first()
                if not application:
                    app_result["status"] = "failed"
                    app_result["error"] = "Application not found"
                    results.append(app_result)
                    continue
                
                deployed_components = []
                
                if "alerts" in components:
                    alerts = db.query(Alert).filter(Alert.application_id == app_id).all()
                    if alerts:
                        # Simulate alert deployment
                        if not dry_run:
                            # Here you would integrate with New Relic API
                            pass
                        deployed_components.append("alerts")
                
                if "dashboards" in components:
                    dashboards = db.query(Dashboard).filter(Dashboard.application_id == app_id).all()
                    if dashboards:
                        # Simulate dashboard deployment
                        if not dry_run:
                            # Here you would integrate with New Relic API
                            pass
                        deployed_components.append("dashboards")
                
                if "policies" in components:
                    # Simulate policy deployment
                    if not dry_run:
                        # Here you would integrate with New Relic API
                        pass
                    deployed_components.append("policies")
                
                app_result["status"] = "deployed" if not dry_run else "pending"
                app_result["components_deployed"] = deployed_components
                
            except Exception as e:
                app_result["status"] = "failed"
                app_result["error"] = str(e)
                logger.error(
                    "Application deployment failed",
                    application_id=app_id,
                    error=str(e)
                )
            
            results.append(app_result)
        
        # Update deployment status
        deployment.status = "completed" if not dry_run else "pending"
        deployment.completed_at = datetime.utcnow()
        deployment.components_deployed = components
        
        # Store results in a separate table or as JSON
        # For now, we'll log them
        logger.info(
            "Deployment completed",
            deployment_id=deployment_id,
            dry_run=dry_run,
            results=results
        )
        
        db.commit()
        
    except Exception as e:
        logger.error(
            "Deployment execution failed",
            deployment_id=deployment_id,
            error=str(e)
        )
        
        if deployment:
            deployment.status = "failed"
            deployment.error_message = str(e)
            db.commit()


@router.post("/deploy", response_model=DeploymentResponse)
@track_requests
async def create_deployment(
    deployment_data: DeploymentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Create and execute a new deployment.
    
    - **application_ids**: List of application IDs to deploy
    - **dry_run**: Simulate deployment without making changes
    - **force**: Force deployment even if validation fails
    - **components**: List of components to deploy (alerts, dashboards, policies)
    """
    # Validate applications exist
    applications = db.query(Application).filter(
        Application.id.in_(deployment_data.application_ids)
    ).all()
    
    if len(applications) != len(deployment_data.application_ids):
        found_ids = [app.id for app in applications]
        missing_ids = set(deployment_data.application_ids) - set(found_ids)
        raise HTTPException(
            status_code=404,
            detail=f"Applications not found: {list(missing_ids)}"
        )
    
    # Create deployment record
    deployment = Deployment(
        application_id=deployment_data.application_ids[0],  # Primary application
        status="pending",
        components_deployed=deployment_data.components,
        deployment_type="full",
        dry_run=deployment_data.dry_run,
        estimated_completion=datetime.utcnow() + timedelta(minutes=30)
    )
    
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    
    # Start background deployment task
    background_tasks.add_task(
        execute_deployment,
        deployment.id,
        deployment_data.application_ids,
        deployment_data.components,
        deployment_data.dry_run,
        db
    )
    
    logger.info(
        "Deployment initiated",
        deployment_id=deployment.id,
        application_ids=deployment_data.application_ids,
        dry_run=deployment_data.dry_run,
        components=deployment_data.components
    )
    
    return DeploymentResponse(
        deployment_id=deployment.id,
        status="initiated",
        applications=[
            {
                "application_id": app_id,
                "status": "pending",
                "components_deployed": []
            }
            for app_id in deployment_data.application_ids
        ],
        estimated_completion=deployment.estimated_completion
    )


@router.get("/deployments/{deployment_id}", response_model=DeploymentSchema)
@track_requests
async def get_deployment(
    deployment_id: str = Path(..., description="Deployment ID"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Retrieve deployment details by ID.
    """
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    
    if not deployment:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found"
        )
    
    logger.info(
        "Retrieved deployment",
        deployment_id=deployment_id,
        status=deployment.status
    )
    
    return deployment


@router.get("/deployments")
@track_requests
async def list_deployments(
    application_id: Optional[str] = Query(None, description="Filter by application ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    deployment_type: Optional[str] = Query(None, description="Filter by deployment type"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Retrieve a paginated list of deployments with optional filtering.
    
    - **application_id**: Filter by specific application
    - **status**: Filter by deployment status
    - **deployment_type**: Filter by deployment type
    - **page**: Page number for pagination
    - **limit**: Number of items per page (max 100)
    """
    query = db.query(Deployment)
    
    # Apply filters
    if application_id:
        query = query.filter(Deployment.application_id == application_id)
    
    if status:
        query = query.filter(Deployment.status == status)
    
    if deployment_type:
        query = query.filter(Deployment.deployment_type == deployment_type)
    
    # Order by most recent first
    query = query.order_by(Deployment.started_at.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    deployments = query.offset(offset).limit(limit).all()
    
    logger.info(
        "Retrieved deployments",
        application_id=application_id,
        status=status,
        page=page,
        limit=limit,
        total=total
    )
    
    return {
        "deployments": deployments,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit
        }
    }


@router.post("/deployments/{deployment_id}/cancel", response_model=DeploymentSchema)
@track_requests
async def cancel_deployment(
    deployment_id: str = Path(..., description="Deployment ID"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Cancel a running deployment.
    """
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    
    if not deployment:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found"
        )
    
    if deployment.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel deployment in status: {deployment.status}"
        )
    
    deployment.status = "cancelled"
    deployment.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(deployment)
    
    logger.info(
        "Cancelled deployment",
        deployment_id=deployment_id
    )
    
    return deployment


@router.post("/deployments/{deployment_id}/retry", response_model=DeploymentResponse)
@track_requests
async def retry_deployment(
    deployment_id: str = Path(..., description="Deployment ID"),
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["write"]))
):
    """
    Retry a failed deployment.
    """
    original_deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    
    if not original_deployment:
        raise HTTPException(
            status_code=404,
            detail="Deployment not found"
        )
    
    if original_deployment.status != "failed":
        raise HTTPException(
            status_code=400,
            detail="Can only retry failed deployments"
        )
    
    # Get application IDs from original deployment
    # This is a simplified approach - in reality you'd store this properly
    application_ids = [original_deployment.application_id]
    
    # Create new deployment
    new_deployment = Deployment(
        application_id=original_deployment.application_id,
        status="pending",
        components_deployed=original_deployment.components_deployed,
        deployment_type="retry",
        dry_run=original_deployment.dry_run,
        estimated_completion=datetime.utcnow() + timedelta(minutes=30)
    )
    
    db.add(new_deployment)
    db.commit()
    db.refresh(new_deployment)
    
    # Start background deployment task
    background_tasks.add_task(
        execute_deployment,
        new_deployment.id,
        application_ids,
        original_deployment.components_deployed,
        original_deployment.dry_run,
        db
    )
    
    logger.info(
        "Deployment retry initiated",
        original_deployment_id=deployment_id,
        new_deployment_id=new_deployment.id
    )
    
    return DeploymentResponse(
        deployment_id=new_deployment.id,
        status="initiated",
        applications=[
            {
                "application_id": app_id,
                "status": "pending",
                "components_deployed": []
            }
            for app_id in application_ids
        ],
        estimated_completion=new_deployment.estimated_completion
    )


@router.get("/deployments/summary")
@track_requests
async def get_deployment_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to summarize"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Get deployment summary statistics for the last N days.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    deployments = db.query(Deployment).filter(
        Deployment.started_at >= cutoff_date
    ).all()
    
    # Calculate statistics
    total_deployments = len(deployments)
    successful_deployments = len([d for d in deployments if d.status == "completed"])
    failed_deployments = len([d for d in deployments if d.status == "failed"])
    pending_deployments = len([d for d in deployments if d.status in ["pending", "running"]])
    
    # Calculate success rate
    success_rate = (successful_deployments / total_deployments * 100) if total_deployments > 0 else 0
    
    # Component deployment statistics
    component_stats = {}
    for deployment in deployments:
        if deployment.components_deployed:
            for component in deployment.components_deployed:
                if component not in component_stats:
                    component_stats[component] = 0
                component_stats[component] += 1
    
    logger.info(
        "Generated deployment summary",
        days=days,
        total_deployments=total_deployments,
        success_rate=success_rate
    )
    
    return {
        "period_days": days,
        "total_deployments": total_deployments,
        "successful_deployments": successful_deployments,
        "failed_deployments": failed_deployments,
        "pending_deployments": pending_deployments,
        "success_rate": round(success_rate, 2),
        "component_statistics": component_stats,
        "generated_at": datetime.utcnow()
    }
