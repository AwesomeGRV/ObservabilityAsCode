"""
Coverage reporting endpoints
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import structlog

from api.database import get_db
from api.models import Application, Alert, Dashboard
from api.schemas import CoverageReport, CoverageMetrics
from api.auth import verify_api_key, require_permissions
from api.exceptions import ApplicationNotFoundError
from api.monitoring import track_requests
from coverage.scoring import CoverageScorer

logger = structlog.get_logger(__name__)

router = APIRouter()
coverage_scorer = CoverageScorer()


@router.get("/coverage", response_model=CoverageReport)
@track_requests
async def get_coverage_report(
    application_id: Optional[str] = Query(None, description="Filter by specific application ID"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    include_recommendations: bool = Query(True, description="Include improvement recommendations"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Generate comprehensive coverage report for observability configurations.
    
    - **application_id**: Generate report for specific application
    - **environment**: Filter by environment (production, staging, development)
    - **include_recommendations**: Include improvement recommendations
    """
    # Build query for applications
    query = db.query(Application)
    
    if application_id:
        query = query.filter(Application.id == application_id)
    
    if environment:
        query = query.filter(Application.environment == environment)
    
    applications = query.all()
    
    if not applications:
        if application_id:
            raise ApplicationNotFoundError(application_id)
        else:
            return {
                "overall_coverage": 0.0,
                "application_count": 0,
                "applications": [],
                "generated_at": datetime.utcnow()
            }
    
    # Calculate coverage for each application
    coverage_metrics = []
    total_score = 0.0
    
    for app in applications:
        # Get application data
        alerts = db.query(Alert).filter(Alert.application_id == app.id).all()
        dashboards = db.query(Dashboard).filter(Dashboard.application_id == app.id).all()
        
        # Prepare data for coverage scoring
        app_data = {
            "name": app.name,
            "environment": app.environment,
            "alerts": [
                {"type": alert.type, "enabled": alert.enabled, "severity": alert.severity}
                for alert in alerts
            ],
            "dashboards": [
                {"type": dashboard.type, "widgets_count": dashboard.widgets_count}
                for dashboard in dashboards
            ],
            "entities": [
                {"type": "application", "id": app.entity_id},
                {"type": "infrastructure"}
            ]
        }
        
        # Calculate coverage metrics
        metrics = coverage_scorer.calculate_coverage(app_data)
        
        # Add application-specific information
        metrics.application_id = app.id
        metrics.application_name = app.name
        metrics.environment = app.environment
        
        # Add recommendations if requested
        if include_recommendations:
            metrics.recommendations = generate_recommendations(app_data, metrics)
        
        coverage_metrics.append(metrics)
        total_score += metrics.overall_score
        
        # Update application's coverage score in database
        app.coverage_score = metrics.overall_score
    
    # Commit coverage score updates
    db.commit()
    
    # Calculate overall coverage
    overall_coverage = total_score / len(applications) if applications else 0.0
    
    logger.info(
        "Generated coverage report",
        application_count=len(applications),
        overall_coverage=overall_coverage,
        environment=environment
    )
    
    return CoverageReport(
        overall_coverage=round(overall_coverage, 2),
        application_count=len(applications),
        applications=coverage_metrics,
        generated_at=datetime.utcnow()
    )


@router.get("/coverage/{application_id}", response_model=CoverageMetrics)
@track_requests
async def get_application_coverage(
    application_id: str,
    include_recommendations: bool = Query(True, description="Include improvement recommendations"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Get detailed coverage report for a specific application.
    """
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise ApplicationNotFoundError(application_id)
    
    # Get application data
    alerts = db.query(Alert).filter(Alert.application_id == application_id).all()
    dashboards = db.query(Dashboard).filter(Dashboard.application_id == application_id).all()
    
    # Prepare data for coverage scoring
    app_data = {
        "name": application.name,
        "environment": application.environment,
        "alerts": [
            {"type": alert.type, "enabled": alert.enabled, "severity": alert.severity}
            for alert in alerts
        ],
        "dashboards": [
            {"type": dashboard.type, "widgets_count": dashboard.widgets_count}
            for dashboard in dashboards
        ],
        "entities": [
            {"type": "application", "id": application.entity_id},
            {"type": "infrastructure"}
        ]
    }
    
    # Calculate coverage metrics
    metrics = coverage_scorer.calculate_coverage(app_data)
    
    # Add application-specific information
    metrics.application_id = application.id
    metrics.application_name = application.name
    metrics.environment = application.environment
    
    # Add recommendations if requested
    if include_recommendations:
        metrics.recommendations = generate_recommendations(app_data, metrics)
    
    # Update application's coverage score in database
    application.coverage_score = metrics.overall_score
    db.commit()
    
    logger.info(
        "Generated application coverage report",
        application_id=application_id,
        coverage_score=metrics.overall_score
    )
    
    return metrics


@router.get("/coverage/summary")
@track_requests
async def get_coverage_summary(
    environment: Optional[str] = Query(None, description="Filter by environment"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Get coverage summary statistics.
    """
    query = db.query(Application)
    
    if environment:
        query = query.filter(Application.environment == environment)
    
    applications = query.all()
    
    if not applications:
        return {
            "total_applications": 0,
            "average_coverage": 0.0,
            "coverage_distribution": {
                "excellent": 0,
                "good": 0,
                "fair": 0,
                "poor": 0,
                "critical": 0
            },
            "component_coverage": {
                "alerts": {"covered": 0, "total": 0},
                "dashboards": {"covered": 0, "total": 0}
            }
        }
    
    # Calculate coverage distribution
    coverage_distribution = {
        "excellent": 0,  # 90%+
        "good": 0,       # 75-89%
        "fair": 0,       # 60-74%
        "poor": 0,       # 40-59%
        "critical": 0    # <40%
    }
    
    total_coverage = 0.0
    total_alerts = 0
    covered_alerts = 0
    total_dashboards = 0
    covered_dashboards = 0
    
    for app in applications:
        # Get coverage score
        alerts = db.query(Alert).filter(Alert.application_id == app.id).all()
        dashboards = db.query(Dashboard).filter(Dashboard.application_id == app.id).all()
        
        app_data = {
            "alerts": [{"type": alert.type} for alert in alerts],
            "dashboards": [{"type": dashboard.type} for dashboard in dashboards],
            "entities": [{"type": "application"}, {"type": "infrastructure"}]
        }
        
        metrics = coverage_scorer.calculate_coverage(app_data)
        coverage_score = metrics.overall_score
        
        total_coverage += coverage_score
        
        # Categorize coverage
        if coverage_score >= 90:
            coverage_distribution["excellent"] += 1
        elif coverage_score >= 75:
            coverage_distribution["good"] += 1
        elif coverage_score >= 60:
            coverage_distribution["fair"] += 1
        elif coverage_score >= 40:
            coverage_distribution["poor"] += 1
        else:
            coverage_distribution["critical"] += 1
        
        # Component coverage
        total_alerts += len(metrics.expected_alerts)
        covered_alerts += len([a for a in metrics.expected_alerts if a in [alert.type for alert in alerts]])
        
        total_dashboards += len(metrics.expected_dashboards)
        covered_dashboards += len([d for d in metrics.expected_dashboards if d in [dashboard.type for dashboard in dashboards]])
    
    average_coverage = total_coverage / len(applications) if applications else 0.0
    
    logger.info(
        "Generated coverage summary",
        total_applications=len(applications),
        average_coverage=average_coverage,
        environment=environment
    )
    
    return {
        "total_applications": len(applications),
        "average_coverage": round(average_coverage, 2),
        "coverage_distribution": coverage_distribution,
        "component_coverage": {
            "alerts": {
                "covered": covered_alerts,
                "total": total_alerts,
                "percentage": round((covered_alerts / total_alerts * 100) if total_alerts > 0 else 0, 2)
            },
            "dashboards": {
                "covered": covered_dashboards,
                "total": total_dashboards,
                "percentage": round((covered_dashboards / total_dashboards * 100) if total_dashboards > 0 else 0, 2)
            }
        }
    }


@router.get("/coverage/recommendations")
@track_requests
async def get_coverage_recommendations(
    application_id: Optional[str] = Query(None, description="Filter by specific application ID"),
    priority: Optional[str] = Query(None, description="Filter by priority (high, medium, low)"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Get improvement recommendations for better coverage.
    """
    query = db.query(Application)
    
    if application_id:
        query = query.filter(Application.id == application_id)
    
    applications = query.all()
    
    all_recommendations = []
    
    for app in applications:
        # Get application data
        alerts = db.query(Alert).filter(Alert.application_id == app.id).all()
        dashboards = db.query(Dashboard).filter(Dashboard.application_id == app.id).all()
        
        app_data = {
            "name": app.name,
            "environment": app.environment,
            "alerts": [
                {"type": alert.type, "enabled": alert.enabled, "severity": alert.severity}
                for alert in alerts
            ],
            "dashboards": [
                {"type": dashboard.type, "widgets_count": dashboard.widgets_count}
                for dashboard in dashboards
            ],
            "entities": [
                {"type": "application", "id": app.entity_id},
                {"type": "infrastructure"}
            ]
        }
        
        # Calculate coverage metrics
        metrics = coverage_scorer.calculate_coverage(app_data)
        
        # Generate recommendations
        recommendations = generate_recommendations(app_data, metrics)
        
        # Add application context to recommendations
        for rec in recommendations:
            rec["application_id"] = app.id
            rec["application_name"] = app.name
            rec["environment"] = app.environment
        
        all_recommendations.extend(recommendations)
    
    # Filter by priority if specified
    if priority:
        all_recommendations = [r for r in all_recommendations if r.get("priority") == priority]
    
    # Sort by priority and impact
    priority_order = {"high": 0, "medium": 1, "low": 2}
    all_recommendations.sort(key=lambda x: (priority_order.get(x.get("priority", "low"), 3), -x.get("impact", 0)))
    
    logger.info(
        "Generated coverage recommendations",
        total_recommendations=len(all_recommendations),
        application_id=application_id,
        priority=priority
    )
    
    return {
        "recommendations": all_recommendations,
        "total_count": len(all_recommendations),
        "generated_at": datetime.utcnow()
    }


def generate_recommendations(app_data: dict, metrics) -> List[dict]:
    """
    Generate improvement recommendations based on coverage gaps.
    """
    recommendations = []
    
    # Alert recommendations
    missing_alerts = metrics.missing_alerts
    for alert_type in missing_alerts:
        priority = "high" if alert_type in ["cpu_usage", "memory_usage", "error_rate"] else "medium"
        
        recommendations.append({
            "type": "alert",
            "component": alert_type,
            "title": f"Add {alert_type.replace('_', ' ').title()} Alert",
            "description": f"Configure {alert_type.replace('_', ' ')} monitoring to improve system observability",
            "priority": priority,
            "impact": 15,  # Coverage percentage impact
            "effort": "low",
            "category": "monitoring"
        })
    
    # Dashboard recommendations
    missing_dashboards = metrics.missing_dashboards
    for dashboard_type in missing_dashboards:
        priority = "high" if dashboard_type in ["application_performance", "infrastructure"] else "medium"
        
        recommendations.append({
            "type": "dashboard",
            "component": dashboard_type,
            "title": f"Create {dashboard_type.replace('_', ' ').title()} Dashboard",
            "description": f"Build {dashboard_type.replace('_', ' ')} dashboard for better visualization",
            "priority": priority,
            "impact": 20,  # Coverage percentage impact
            "effort": "medium",
            "category": "visualization"
        })
    
    # Entity recommendations
    if metrics.entity_coverage < 100:
        recommendations.append({
            "type": "entity",
            "component": "entity_coverage",
            "title": "Improve Entity Coverage",
            "description": "Add more New Relic entities for comprehensive monitoring",
            "priority": "medium",
            "impact": 10,
            "effort": "medium",
            "category": "infrastructure"
        })
    
    # Quality recommendations
    disabled_alerts = [a for a in app_data.get("alerts", []) if not a.get("enabled", True)]
    if disabled_alerts:
        recommendations.append({
            "type": "quality",
            "component": "alert_health",
            "title": "Enable Disabled Alerts",
            "description": f"Review and enable {len(disabled_alerts)} disabled alerts",
            "priority": "medium",
            "impact": 5,
            "effort": "low",
            "category": "maintenance"
        })
    
    return recommendations
