"""
Compliance checking endpoints
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import structlog

from api.database import get_db
from api.models import Application, Alert, Dashboard, ComplianceReport
from api.schemas import ComplianceReport as ComplianceReportSchema
from api.auth import verify_api_key, require_permissions
from api.exceptions import ApplicationNotFoundError
from api.monitoring import track_requests

logger = structlog.get_logger(__name__)

router = APIRouter()


# Compliance standards definitions
COMPLIANCE_STANDARDS = {
    "standard": {
        "name": "Standard Observability",
        "description": "Basic observability requirements for production applications",
        "requirements": {
            "alerts": {
                "cpu_usage": {"required": True, "description": "CPU usage monitoring"},
                "memory_usage": {"required": True, "description": "Memory usage monitoring"},
                "error_rate": {"required": True, "description": "Error rate monitoring"}
            },
            "dashboards": {
                "application_performance": {"required": True, "description": "Application performance dashboard"},
                "infrastructure": {"required": False, "description": "Infrastructure monitoring dashboard"}
            }
        }
    },
    "enhanced": {
        "name": "Enhanced Observability",
        "description": "Comprehensive observability for critical applications",
        "requirements": {
            "alerts": {
                "cpu_usage": {"required": True, "description": "CPU usage monitoring"},
                "memory_usage": {"required": True, "description": "Memory usage monitoring"},
                "disk_usage": {"required": True, "description": "Disk usage monitoring"},
                "response_time": {"required": True, "description": "Response time monitoring"},
                "error_rate": {"required": True, "description": "Error rate monitoring"}
            },
            "dashboards": {
                "application_performance": {"required": True, "description": "Application performance dashboard"},
                "infrastructure": {"required": True, "description": "Infrastructure monitoring dashboard"},
                "error_analysis": {"required": True, "description": "Error analysis dashboard"}
            }
        }
    },
    "strict": {
        "name": "Strict Observability",
        "description": "Enterprise-grade observability with comprehensive coverage",
        "requirements": {
            "alerts": {
                "cpu_usage": {"required": True, "description": "CPU usage monitoring"},
                "memory_usage": {"required": True, "description": "Memory usage monitoring"},
                "disk_usage": {"required": True, "description": "Disk usage monitoring"},
                "response_time": {"required": True, "description": "Response time monitoring"},
                "error_rate": {"required": True, "description": "Error rate monitoring"},
                "pod_health": {"required": True, "description": "Pod health monitoring"}
            },
            "dashboards": {
                "application_performance": {"required": True, "description": "Application performance dashboard"},
                "infrastructure": {"required": True, "description": "Infrastructure monitoring dashboard"},
                "error_analysis": {"required": True, "description": "Error analysis dashboard"},
                "business_metrics": {"required": True, "description": "Business metrics dashboard"}
            }
        }
    }
}


@router.get("/compliance", response_model=ComplianceReportSchema)
@track_requests
async def get_compliance_status(
    application_id: Optional[str] = Query(None, description="Filter by specific application ID"),
    environment: Optional[str] = Query(None, description="Filter by environment"),
    standard: str = Query("standard", description="Compliance standard (standard, enhanced, strict)"),
    save_report: bool = Query(False, description="Save compliance report to database"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Generate compliance report for applications against specified standards.
    
    - **application_id**: Check compliance for specific application
    - **environment**: Filter by environment
    - **standard**: Compliance standard to check against
    - **save_report**: Save the compliance report to database
    """
    if standard not in COMPLIANCE_STANDARDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid compliance standard. Must be one of: {list(COMPLIANCE_STANDARDS.keys())}"
        )
    
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
                "overall_compliance": 0.0,
                "applications": [],
                "standards": {},
                "generated_at": datetime.utcnow()
            }
    
    # Check compliance for each application
    compliance_results = []
    total_score = 0.0
    
    for app in applications:
        compliance_result = check_application_compliance(app, standard, db)
        compliance_results.append(compliance_result)
        total_score += compliance_result["score"]
        
        # Save report to database if requested
        if save_report:
            save_compliance_report(app.id, standard, compliance_result, db)
    
    # Calculate overall compliance
    overall_compliance = total_score / len(applications) if applications else 0.0
    
    # Prepare standards information
    standards_info = {
        standard: {
            "name": COMPLIANCE_STANDARDS[standard]["name"],
            "description": COMPLIANCE_STANDARDS[standard]["description"],
            "compliant": overall_compliance >= 80,
            "score": overall_compliance,
            "requirements": format_standard_requirements(COMPLIANCE_STANDARDS[standard]["requirements"])
        }
    }
    
    logger.info(
        "Generated compliance report",
        standard=standard,
        application_count=len(applications),
        overall_compliance=overall_compliance,
        environment=environment
    )
    
    return ComplianceReportSchema(
        overall_compliance=round(overall_compliance, 2),
        applications=compliance_results,
        standards=standards_info,
        generated_at=datetime.utcnow()
    )


@router.get("/compliance/{application_id}")
@track_requests
async def get_application_compliance(
    application_id: str,
    standard: str = Query("standard", description="Compliance standard (standard, enhanced, strict)"),
    save_report: bool = Query(False, description="Save compliance report to database"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Get detailed compliance report for a specific application.
    """
    if standard not in COMPLIANCE_STANDARDS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid compliance standard. Must be one of: {list(COMPLIANCE_STANDARDS.keys())}"
        )
    
    application = db.query(Application).filter(Application.id == application_id).first()
    
    if not application:
        raise ApplicationNotFoundError(application_id)
    
    compliance_result = check_application_compliance(application, standard, db)
    
    # Save report to database if requested
    if save_report:
        save_compliance_report(application_id, standard, compliance_result, db)
    
    logger.info(
        "Generated application compliance report",
        application_id=application_id,
        standard=standard,
        compliance_score=compliance_result["score"]
    )
    
    return {
        "application_id": application_id,
        "application_name": application.name,
        "environment": application.environment,
        "standard": standard,
        "compliance_result": compliance_result,
        "generated_at": datetime.utcnow()
    }


@router.get("/compliance/standards")
@track_requests
async def get_compliance_standards(
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Get available compliance standards and their requirements.
    """
    return {
        "standards": {
            key: {
                "name": value["name"],
                "description": value["description"],
                "requirements": format_standard_requirements(value["requirements"])
            }
            for key, value in COMPLIANCE_STANDARDS.items()
        }
    }


@router.get("/compliance/history")
@track_requests
async def get_compliance_history(
    application_id: Optional[str] = Query(None, description="Filter by specific application ID"),
    standard: str = Query("standard", description="Filter by compliance standard"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db),
    api_key: dict = Depends(require_permissions(["read"]))
):
    """
    Get compliance history for applications.
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = db.query(ComplianceReport).filter(
        ComplianceReport.created_at >= cutoff_date,
        ComplianceReport.standard == standard
    )
    
    if application_id:
        query = query.filter(ComplianceReport.application_id == application_id)
    
    reports = query.order_by(ComplianceReport.created_at.desc()).all()
    
    # Group by date
    history = {}
    for report in reports:
        date_key = report.created_at.date().isoformat()
        
        if date_key not in history:
            history[date_key] = {
                "date": date_key,
                "applications": [],
                "average_score": 0.0,
                "total_applications": 0
            }
        
        history[date_key]["applications"].append({
            "application_id": report.application_id,
            "score": report.overall_score,
            "compliant": report.compliant,
            "violations": report.violations
        })
        
        history[date_key]["total_applications"] += 1
    
    # Calculate daily averages
    for date_data in history.values():
        if date_data["applications"]:
            date_data["average_score"] = sum(
                app["score"] for app in date_data["applications"]
            ) / len(date_data["applications"])
    
    logger.info(
        "Retrieved compliance history",
        standard=standard,
        days=days,
        report_count=len(reports)
    )
    
    return {
        "standard": standard,
        "period_days": days,
        "history": list(history.values()),
        "generated_at": datetime.utcnow()
    }


def check_application_compliance(application, standard: str, db: Session) -> Dict[str, Any]:
    """
    Check compliance for a single application against a standard.
    """
    standard_config = COMPLIANCE_STANDARDS[standard]
    requirements = standard_config["requirements"]
    
    # Get application alerts and dashboards
    alerts = db.query(Alert).filter(Alert.application_id == application.id).all()
    dashboards = db.query(Dashboard).filter(Dashboard.application_id == application.id).all()
    
    # Check alert requirements
    alert_violations = []
    alert_types = [alert.type for alert in alerts]
    
    for alert_type, config in requirements["alerts"].items():
        if config["required"] and alert_type not in alert_types:
            alert_violations.append(f"Missing {config['description']}")
    
    # Check dashboard requirements
    dashboard_violations = []
    dashboard_types = [dashboard.type for dashboard in dashboards]
    
    for dashboard_type, config in requirements["dashboards"].items():
        if config["required"] and dashboard_type not in dashboard_types:
            dashboard_violations.append(f"Missing {config['description']}")
    
    # Additional quality checks
    quality_violations = []
    
    # Check for disabled alerts
    disabled_alerts = [alert for alert in alerts if not alert.enabled]
    if disabled_alerts:
        quality_violations.append(f"{len(disabled_alerts)} alerts are disabled")
    
    # Check for empty dashboards
    empty_dashboards = [dash for dash in dashboards if dash.widgets_count == 0]
    if empty_dashboards:
        quality_violations.append(f"{len(empty_dashboards)} dashboards have no widgets")
    
    # Calculate compliance score
    total_requirements = sum(
        1 for config in requirements["alerts"].values() if config["required"]
    ) + sum(
        1 for config in requirements["dashboards"].values() if config["required"]
    )
    
    met_requirements = total_requirements - len(alert_violations) - len(dashboard_violations)
    base_score = (met_requirements / total_requirements) * 100 if total_requirements > 0 else 100
    
    # Apply quality penalties
    quality_penalty = min(len(quality_violations) * 5, 20)  # Max 20% penalty
    final_score = max(0, base_score - quality_penalty)
    
    # Combine all violations
    all_violations = alert_violations + dashboard_violations + quality_violations
    
    return {
        "name": application.name,
        "environment": application.environment,
        "compliant": final_score >= 80,
        "score": round(final_score, 2),
        "violations": all_violations,
        "alert_violations": alert_violations,
        "dashboard_violations": dashboard_violations,
        "quality_violations": quality_violations,
        "requirements_met": met_requirements,
        "total_requirements": total_requirements
    }


def format_standard_requirements(requirements: Dict) -> List[Dict[str, Any]]:
    """
    Format standard requirements for API response.
    """
    formatted = []
    
    # Alert requirements
    for alert_type, config in requirements["alerts"].items():
        formatted.append({
            "name": config["description"],
            "category": "alerts",
            "type": alert_type,
            "required": config["required"],
            "met": False  # Will be updated per application
        })
    
    # Dashboard requirements
    for dashboard_type, config in requirements["dashboards"].items():
        formatted.append({
            "name": config["description"],
            "category": "dashboards",
            "type": dashboard_type,
            "required": config["required"],
            "met": False  # Will be updated per application
        })
    
    return formatted


def save_compliance_report(application_id: str, standard: str, compliance_result: Dict, db: Session):
    """
    Save compliance report to database.
    """
    # Check if recent report already exists
    recent_report = db.query(ComplianceReport).filter(
        ComplianceReport.application_id == application_id,
        ComplianceReport.standard == standard,
        ComplianceReport.created_at >= datetime.utcnow() - timedelta(hours=1)
    ).first()
    
    if recent_report:
        # Update existing report
        recent_report.overall_score = compliance_result["score"]
        recent_report.compliant = compliance_result["compliant"]
        recent_report.violations = compliance_result["violations"]
        recent_report.requirements = {
            "met": compliance_result["requirements_met"],
            "total": compliance_result["total_requirements"]
        }
    else:
        # Create new report
        report = ComplianceReport(
            application_id=application_id,
            standard=standard,
            overall_score=compliance_result["score"],
            compliant=compliance_result["compliant"],
            violations=compliance_result["violations"],
            requirements={
                "met": compliance_result["requirements_met"],
                "total": compliance_result["total_requirements"]
            }
        )
        db.add(report)
    
    db.commit()
