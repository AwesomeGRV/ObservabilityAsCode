"""
FastAPI application for Observability as Code API
"""

from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from coverage.scoring import CoverageScorer, CoverageMetrics
from nerdgraph.nerdgraph_client import NERDGraphClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Observability as Code API",
    description="API for managing New Relic observability configurations",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key authentication
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)

# Pydantic models
class Application(BaseModel):
    id: str
    name: str
    environment: str
    status: str
    created_at: datetime
    updated_at: datetime
    coverage_score: Optional[float] = None

class CreateApplicationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    environment: str = Field(..., regex="^(production|staging|development)$")
    entity_id: str = Field(..., min_length=1)
    description: Optional[str] = None
    team: Optional[str] = None

class Alert(BaseModel):
    id: str
    name: str
    type: str
    enabled: bool
    nrql_query: str
    thresholds: Dict[str, Any]
    created_at: datetime

class CreateAlertRequest(BaseModel):
    name: str = Field(..., min_length=1)
    type: str = Field(..., regex="^(cpu_usage|memory_usage|disk_usage|response_time|error_rate|pod_health)$")
    nrql_query: str = Field(..., min_length=1)
    thresholds: Dict[str, Any] = Field(...)
    enabled: bool = True

class Dashboard(BaseModel):
    id: str
    name: str
    type: str
    widgets_count: int
    created_at: datetime
    updated_at: datetime

class CreateDashboardRequest(BaseModel):
    name: str = Field(..., min_length=1)
    type: str = Field(..., regex="^(infrastructure|application_performance|error_analysis|business_metrics)$")
    description: Optional[str] = None
    widgets: List[Dict[str, Any]] = Field(..., min_items=1)

class DeployRequest(BaseModel):
    application_ids: List[str] = Field(..., min_items=1)
    dry_run: bool = False
    force: bool = False
    components: Optional[List[str]] = Field(default=["alerts", "dashboards", "policies"])

# In-memory storage (replace with database in production)
applications_db: Dict[str, Application] = {}
alerts_db: Dict[str, List[Alert]] = {}
dashboards_db: Dict[str, List[Dashboard]] = {}

# Global instances
coverage_scorer = CoverageScorer()
nerdgraph_client = None  # Initialize with proper credentials

async def verify_api_key(api_key: str = Depends(API_KEY_HEADER)):
    """Verify API key authentication"""
    # Implement proper API key validation
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")
    return api_key

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Observability as Code API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/applications", response_model=Dict[str, Any])
async def get_applications(
    environment: Optional[str] = Query(None, regex="^(production|staging|development)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    api_key: str = Depends(verify_api_key)
):
    """Get all applications"""
    filtered_apps = list(applications_db.values())
    
    if environment:
        filtered_apps = [app for app in filtered_apps if app.environment == environment]
    
    # Pagination
    start = (page - 1) * limit
    end = start + limit
    paginated_apps = filtered_apps[start:end]
    
    return {
        "applications": paginated_apps,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": len(filtered_apps),
            "total_pages": (len(filtered_apps) + limit - 1) // limit
        }
    }

@app.post("/applications", response_model=Application)
async def create_application(
    app_data: CreateApplicationRequest,
    api_key: str = Depends(verify_api_key)
):
    """Create new application"""
    app_id = f"app-{len(applications_db) + 1:06d}"
    
    if app_id in applications_db:
        raise HTTPException(status_code=409, detail="Application already exists")
    
    application = Application(
        id=app_id,
        name=app_data.name,
        environment=app_data.environment,
        status="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    applications_db[app_id] = application
    alerts_db[app_id] = []
    dashboards_db[app_id] = []
    
    logger.info(f"Created application: {app_id}")
    return application

@app.get("/applications/{application_id}", response_model=Application)
async def get_application(
    application_id: str = Path(..., min_length=1),
    api_key: str = Depends(verify_api_key)
):
    """Get application details"""
    if application_id not in applications_db:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return applications_db[application_id]

@app.get("/applications/{application_id}/alerts", response_model=Dict[str, List[Alert]])
async def get_application_alerts(
    application_id: str = Path(..., min_length=1),
    api_key: str = Depends(verify_api_key)
):
    """Get application alerts"""
    if application_id not in applications_db:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return {"alerts": alerts_db.get(application_id, [])}

@app.post("/applications/{application_id}/alerts", response_model=Alert)
async def create_alert(
    application_id: str = Path(..., min_length=1),
    alert_data: CreateAlertRequest = None,
    api_key: str = Depends(verify_api_key)
):
    """Create alert for application"""
    if application_id not in applications_db:
        raise HTTPException(status_code=404, detail="Application not found")
    
    alert_id = f"alert-{len(alerts_db.get(application_id, [])) + 1:06d}"
    
    alert = Alert(
        id=alert_id,
        name=alert_data.name,
        type=alert_data.type,
        enabled=alert_data.enabled,
        nrql_query=alert_data.nrql_query,
        thresholds=alert_data.thresholds,
        created_at=datetime.utcnow()
    )
    
    if application_id not in alerts_db:
        alerts_db[application_id] = []
    
    alerts_db[application_id].append(alert)
    
    logger.info(f"Created alert {alert_id} for application {application_id}")
    return alert

@app.get("/applications/{application_id}/dashboards", response_model=Dict[str, List[Dashboard]])
async def get_application_dashboards(
    application_id: str = Path(..., min_length=1),
    api_key: str = Depends(verify_api_key)
):
    """Get application dashboards"""
    if application_id not in applications_db:
        raise HTTPException(status_code=404, detail="Application not found")
    
    return {"dashboards": dashboards_db.get(application_id, [])}

@app.post("/applications/{application_id}/dashboards", response_model=Dashboard)
async def create_dashboard(
    application_id: str = Path(..., min_length=1),
    dashboard_data: CreateDashboardRequest = None,
    api_key: str = Depends(verify_api_key)
):
    """Create dashboard for application"""
    if application_id not in applications_db:
        raise HTTPException(status_code=404, detail="Application not found")
    
    dashboard_id = f"dashboard-{len(dashboards_db.get(application_id, [])) + 1:06d}"
    
    dashboard = Dashboard(
        id=dashboard_id,
        name=dashboard_data.name,
        type=dashboard_data.type,
        widgets_count=len(dashboard_data.widgets),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    if application_id not in dashboards_db:
        dashboards_db[application_id] = []
    
    dashboards_db[application_id].append(dashboard)
    
    logger.info(f"Created dashboard {dashboard_id} for application {application_id}")
    return dashboard

@app.get("/coverage")
async def get_coverage_report(
    application_id: Optional[str] = Query(None),
    environment: Optional[str] = Query(None, regex="^(production|staging|development)$"),
    api_key: str = Depends(verify_api_key)
):
    """Get coverage report"""
    apps_to_analyze = []
    
    if application_id:
        if application_id not in applications_db:
            raise HTTPException(status_code=404, detail="Application not found")
        apps_to_analyze = [applications_db[application_id]]
    else:
        apps_to_analyze = list(applications_db.values())
        if environment:
            apps_to_analyze = [app for app in apps_to_analyze if app.environment == environment]
    
    # Prepare data for coverage scoring
    coverage_data = []
    for app in apps_to_analyze:
        app_data = {
            "name": app.name,
            "alerts": [
                {"type": alert.type} for alert in alerts_db.get(app.id, [])
            ],
            "dashboards": [
                {"type": dashboard.type} for dashboard in dashboards_db.get(app.id, [])
            ],
            "entities": [
                {"type": "application"},
                {"type": "infrastructure"}
            ]
        }
        coverage_data.append(app_data)
    
    # Calculate coverage scores
    coverage_metrics = []
    for data in coverage_data:
        metrics = coverage_scorer.calculate_coverage(data)
        coverage_metrics.append(metrics)
    
    # Generate report
    report = coverage_scorer.generate_coverage_report(coverage_metrics)
    
    return report

@app.get("/compliance")
async def get_compliance_status(
    application_id: Optional[str] = Query(None),
    standard: str = Query("standard"),
    api_key: str = Depends(verify_api_key)
):
    """Get compliance status"""
    # This is a simplified compliance check
    apps_to_check = []
    
    if application_id:
        if application_id not in applications_db:
            raise HTTPException(status_code=404, detail="Application not found")
        apps_to_check = [applications_db[application_id]]
    else:
        apps_to_check = list(applications_db.values())
    
    compliance_results = []
    for app in apps_to_check:
        app_alerts = alerts_db.get(app.id, [])
        app_dashboards = dashboards_db.get(app.id, [])
        
        # Basic compliance rules
        has_cpu_alert = any(alert.type == "cpu_usage" for alert in app_alerts)
        has_memory_alert = any(alert.type == "memory_usage" for alert in app_alerts)
        has_perf_dashboard = any(dashboard.type == "application_performance" for dashboard in app_dashboards)
        
        compliant = has_cpu_alert and has_memory_alert and has_perf_dashboard
        score = 100 if compliant else 50
        
        violations = []
        if not has_cpu_alert:
            violations.append("Missing CPU usage alert")
        if not has_memory_alert:
            violations.append("Missing memory usage alert")
        if not has_perf_dashboard:
            violations.append("Missing performance dashboard")
        
        compliance_results.append({
            "name": app.name,
            "compliant": compliant,
            "score": score,
            "violations": violations
        })
    
    overall_compliance = sum(result["score"] for result in compliance_results) / len(compliance_results) if compliance_results else 0
    
    return {
        "overall_compliance": overall_compliance,
        "applications": compliance_results,
        "standards": {
            standard: {
                "compliant": overall_compliance >= 80,
                "score": overall_compliance,
                "requirements": [
                    {"name": "CPU Monitoring", "met": True, "description": "CPU usage alerts configured"},
                    {"name": "Memory Monitoring", "met": True, "description": "Memory usage alerts configured"},
                    {"name": "Performance Dashboard", "met": True, "description": "Application performance dashboard created"}
                ]
            }
        }
    }

@app.post("/deploy")
async def deploy_configurations(
    deploy_request: DeployRequest,
    api_key: str = Depends(verify_api_key)
):
    """Deploy configurations to New Relic"""
    deployment_id = f"deploy-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    results = []
    for app_id in deploy_request.application_ids:
        if app_id not in applications_db:
            results.append({
                "application_id": app_id,
                "status": "failed",
                "components_deployed": [],
                "error": "Application not found"
            })
            continue
        
        # Simulate deployment
        components_deployed = []
        if "alerts" in deploy_request.components:
            components_deployed.append("alerts")
        if "dashboards" in deploy_request.components:
            components_deployed.append("dashboards")
        if "policies" in deploy_request.components:
            components_deployed.append("policies")
        
        results.append({
            "application_id": app_id,
            "status": "deployed" if not deploy_request.dry_run else "pending",
            "components_deployed": components_deployed
        })
    
    logger.info(f"Deployment {deployment_id} initiated for {len(deploy_request.application_ids)} applications")
    
    return {
        "deployment_id": deployment_id,
        "status": "completed" if not deploy_request.dry_run else "initiated",
        "applications": results,
        "estimated_completion": datetime.utcnow()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
