"""
Custom monitoring endpoints for business metrics, security, cost, and compliance
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
import structlog

from ...monitoring import (
    CUSTOM_BUSINESS_EVENTS,
    CUSTOM_USER_BEHAVIOR,
    CUSTOM_FEATURE_USAGE,
    CUSTOM_PERFORMANCE_SCORES,
    CUSTOM_BUSINESS_KPI,
    SECURITY_EVENTS,
    SECURITY_THREATS,
    SECURITY_VIOLATIONS,
    AUTHENTICATION_ATTEMPTS,
    AUTHORIZATION_FAILURES,
    SECURITY_SCORE,
    COST_BY_SERVICE,
    COST_BY_RESOURCE,
    COST_OPTIMIZATION_SAVINGS,
    RESOURCE_UTILIZATION_COST,
    COMPLIANCE_VIOLATIONS,
    AUDIT_EVENTS,
    DATA_ACCESS_EVENTS,
    POLICY_COMPLIANCE_SCORE,
    APPLICATION_HEALTH_SCORE,
    CUSTOM_SLA_COMPLIANCE,
    CUSTOM_ERROR_BUDGET,
    ANOMALY_DETECTION_EVENTS,
    ML_PREDICTION_ACCURACY,
    PATTERN_DETECTION_EVENTS,
    metrics_store
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/custom", tags=["custom-monitoring"])


class CustomBusinessEvent(BaseModel):
    event_type: str  # purchase, signup, upgrade, downgrade, etc.
    product: str
    user_segment: str
    region: str
    value: Optional[float] = 0.0
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class UserBehaviorEvent(BaseModel):
    behavior_type: str  # click, scroll, dwell_time, form_interaction
    feature: str
    user_type: str
    duration: float
    success: bool
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class FeatureUsageEvent(BaseModel):
    feature_name: str
    feature_category: str
    user_tier: str
    usage_count: int
    session_duration: float
    timestamp: Optional[datetime] = None


class SecurityEvent(BaseModel):
    event_type: str
    severity: str  # low, medium, high, critical
    source: str
    category: str
    description: str
    user_id: Optional[str] = ""
    ip_address: str
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class SecurityThreatEvent(BaseModel):
    threat_type: str
    confidence: float  # 0.0 to 1.0
    target: str
    description: str
    mitigation_status: str
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class AuthenticationEvent(BaseModel):
    auth_method: str
    result: str  # success, failure, locked, etc.
    user_type: str
    ip_location: str
    user_agent: str
    failure_reason: Optional[str] = ""
    timestamp: Optional[datetime] = None


class CostMetricEvent(BaseModel):
    service_name: str
    cost_type: str  # compute, storage, network, license
    environment: str
    amount: float
    currency: str = "USD"
    billing_period: str
    usage_metrics: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class ComplianceViolationEvent(BaseModel):
    standard: str  # GDPR, HIPAA, SOX, PCI-DSS, etc.
    violation_type: str
    severity: str
    department: str
    description: str
    remediation_status: str
    affected_data: Optional[str] = ""
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class AuditEvent(BaseModel):
    event_type: str
    user_role: str
    resource_type: str
    action: str
    action_result: str
    resource_id: Optional[str] = ""
    user_id: Optional[str] = ""
    ip_address: str
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class ApplicationHealthEvent(BaseModel):
    app_name: str
    environment: str
    health_category: str  # performance, availability, security, business
    score: float  # 0-100
    factors: Optional[Dict[str, float]] = {}
    timestamp: Optional[datetime] = None


class AnomalyDetectionEvent(BaseModel):
    anomaly_type: str
    severity: str
    metric_name: str
    detection_method: str
    confidence: float
    baseline_value: float
    actual_value: float
    description: str
    timestamp: Optional[datetime] = None


class CustomMetricsResponse(BaseModel):
    business_metrics: Dict[str, Any]
    security_metrics: Dict[str, Any]
    cost_metrics: Dict[str, Any]
    compliance_metrics: Dict[str, Any]
    application_health: Dict[str, Any]
    analytics_metrics: Dict[str, Any]
    last_updated: datetime


@router.post("/business-event")
async def track_custom_business_event(event: CustomBusinessEvent):
    """Track custom business events"""
    try:
        # Update Prometheus metrics
        CUSTOM_BUSINESS_EVENTS.labels(
            event_type=event.event_type,
            product=event.product,
            user_segment=event.user_segment,
            region=event.region
        ).inc()
        
        # Store in memory for analysis
        if 'business_events' not in metrics_store['custom_business_metrics']:
            metrics_store['custom_business_metrics']['business_events'] = {}
        
        key = f"{event.event_type}:{event.product}:{event.user_segment}"
        if key not in metrics_store['custom_business_metrics']['business_events']:
            metrics_store['custom_business_metrics']['business_events'][key] = {
                'count': 0,
                'total_value': 0.0,
                'events': []
            }
        
        business_data = metrics_store['custom_business_metrics']['business_events'][key]
        business_data['count'] += 1
        business_data['total_value'] += event.value or 0.0
        
        business_data['events'].append({
            'timestamp': event.timestamp or datetime.utcnow(),
            'value': event.value,
            'region': event.region,
            'metadata': event.metadata or {}
        })
        
        logger.info(
            "Custom business event tracked",
            event_type=event.event_type,
            product=event.product,
            user_segment=event.user_segment,
            value=event.value,
            region=event.region
        )
        
        return {"status": "success", "message": "Business event tracked"}
        
    except Exception as e:
        logger.error("Failed to track business event", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track business event")


@router.post("/user-behavior")
async def track_user_behavior(event: UserBehaviorEvent):
    """Track custom user behavior metrics"""
    try:
        # Update Prometheus metrics
        CUSTOM_USER_BEHAVIOR.labels(
            behavior_type=event.behavior_type,
            feature=event.feature,
            user_type=event.user_type
        ).observe(event.duration)
        
        # Store in memory for analysis
        if 'user_behavior' not in metrics_store['custom_business_metrics']:
            metrics_store['custom_business_metrics']['user_behavior'] = {}
        
        key = f"{event.behavior_type}:{event.feature}:{event.user_type}"
        if key not in metrics_store['custom_business_metrics']['user_behavior']:
            metrics_store['custom_business_metrics']['user_behavior'][key] = {
                'count': 0,
                'durations': [],
                'success_count': 0,
                'total_duration': 0.0
            }
        
        behavior_data = metrics_store['custom_business_metrics']['user_behavior'][key]
        behavior_data['count'] += 1
        behavior_data['durations'].append(event.duration)
        behavior_data['total_duration'] += event.duration
        
        if event.success:
            behavior_data['success_count'] += 1
        
        logger.info(
            "User behavior tracked",
            behavior_type=event.behavior_type,
            feature=event.feature,
            user_type=event.user_type,
            duration=event.duration,
            success=event.success
        )
        
        return {"status": "success", "message": "User behavior tracked"}
        
    except Exception as e:
        logger.error("Failed to track user behavior", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track user behavior")


@router.post("/feature-usage")
async def track_feature_usage(event: FeatureUsageEvent):
    """Track custom feature usage metrics"""
    try:
        # Update Prometheus metrics
        CUSTOM_FEATURE_USAGE.labels(
            feature_name=event.feature_name,
            feature_category=event.feature_category,
            user_tier=event.user_tier
        ).inc(event.usage_count)
        
        # Store in memory for analysis
        if 'feature_usage' not in metrics_store['custom_business_metrics']:
            metrics_store['custom_business_metrics']['feature_usage'] = {}
        
        key = f"{event.feature_name}:{event.user_tier}"
        if key not in metrics_store['custom_business_metrics']['feature_usage']:
            metrics_store['custom_business_metrics']['feature_usage'][key] = {
                'total_usage': 0,
                'session_count': 0,
                'total_session_duration': 0.0,
                'usage_events': []
            }
        
        feature_data = metrics_store['custom_business_metrics']['feature_usage'][key]
        feature_data['total_usage'] += event.usage_count
        feature_data['session_count'] += 1
        feature_data['total_session_duration'] += event.session_duration
        
        feature_data['usage_events'].append({
            'timestamp': event.timestamp or datetime.utcnow(),
            'usage_count': event.usage_count,
            'session_duration': event.session_duration,
            'feature_category': event.feature_category
        })
        
        logger.info(
            "Feature usage tracked",
            feature_name=event.feature_name,
            feature_category=event.feature_category,
            user_tier=event.user_tier,
            usage_count=event.usage_count
        )
        
        return {"status": "success", "message": "Feature usage tracked"}
        
    except Exception as e:
        logger.error("Failed to track feature usage", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track feature usage")


@router.post("/security-event")
async def track_security_event(event: SecurityEvent):
    """Track security events and incidents"""
    try:
        # Update Prometheus metrics
        SECURITY_EVENTS.labels(
            event_type=event.event_type,
            severity=event.severity,
            source=event.source,
            category=event.category
        ).inc()
        
        # Store in memory for analysis
        if 'security_events' not in metrics_store['security_metrics']:
            metrics_store['security_metrics']['security_events'] = {}
        
        key = f"{event.event_type}:{event.severity}"
        if key not in metrics_store['security_metrics']['security_events']:
            metrics_store['security_metrics']['security_events'][key] = {
                'count': 0,
                'events': []
            }
        
        security_data = metrics_store['security_metrics']['security_events'][key]
        security_data['count'] += 1
        
        security_data['events'].append({
            'timestamp': event.timestamp or datetime.utcnow(),
            'source': event.source,
            'category': event.category,
            'description': event.description,
            'user_id': event.user_id,
            'ip_address': event.ip_address,
            'metadata': event.metadata or {}
        })
        
        logger.warning(
            "Security event tracked",
            event_type=event.event_type,
            severity=event.severity,
            source=event.source,
            category=event.category,
            user_id=event.user_id,
            ip_address=event.ip_address
        )
        
        return {"status": "success", "message": "Security event tracked"}
        
    except Exception as e:
        logger.error("Failed to track security event", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track security event")


@router.post("/security-threat")
async def track_security_threat(event: SecurityThreatEvent):
    """Track security threat detection"""
    try:
        # Update Prometheus metrics
        SECURITY_THREATS.labels(
            threat_type=event.threat_type,
            confidence=f"{int(event.confidence * 100)}%",
            target=event.target
        ).inc()
        
        # Store in memory for analysis
        if 'threats' not in metrics_store['security_metrics']:
            metrics_store['security_metrics']['threats'] = {}
        
        if event.threat_type not in metrics_store['security_metrics']['threats']:
            metrics_store['security_metrics']['threats'][event.threat_type] = {
                'count': 0,
                'threats': []
            }
        
        threat_data = metrics_store['security_metrics']['threats'][event.threat_type]
        threat_data['count'] += 1
        
        threat_data['threats'].append({
            'timestamp': event.timestamp or datetime.utcnow(),
            'confidence': event.confidence,
            'target': event.target,
            'description': event.description,
            'mitigation_status': event.mitigation_status,
            'metadata': event.metadata or {}
        })
        
        logger.warning(
            "Security threat detected",
            threat_type=event.threat_type,
            confidence=event.confidence,
            target=event.target,
            mitigation_status=event.mitigation_status
        )
        
        return {"status": "success", "message": "Security threat tracked"}
        
    except Exception as e:
        logger.error("Failed to track security threat", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track security threat")


@router.post("/authentication")
async def track_authentication_event(event: AuthenticationEvent):
    """Track authentication attempts"""
    try:
        # Update Prometheus metrics
        AUTHENTICATION_ATTEMPTS.labels(
            auth_method=event.auth_method,
            result=event.result,
            user_type=event.user_type,
            ip_location=event.ip_location
        ).inc()
        
        # Store in memory for analysis
        if 'auth_events' not in metrics_store['security_metrics']:
            metrics_store['security_metrics']['auth_events'] = {}
        
        key = f"{event.auth_method}:{event.result}"
        if key not in metrics_store['security_metrics']['auth_events']:
            metrics_store['security_metrics']['auth_events'][key] = {
                'count': 0,
                'events': []
            }
        
        auth_data = metrics_store['security_metrics']['auth_events'][key]
        auth_data['count'] += 1
        
        auth_data['events'].append({
            'timestamp': event.timestamp or datetime.utcnow(),
            'user_type': event.user_type,
            'ip_location': event.ip_location,
            'user_agent': event.user_agent,
            'failure_reason': event.failure_reason
        })
        
        logger.info(
            "Authentication event tracked",
            auth_method=event.auth_method,
            result=event.result,
            user_type=event.user_type,
            ip_location=event.ip_location,
            failure_reason=event.failure_reason
        )
        
        return {"status": "success", "message": "Authentication event tracked"}
        
    except Exception as e:
        logger.error("Failed to track authentication event", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track authentication event")


@router.post("/cost-metric")
async def track_cost_metric(event: CostMetricEvent):
    """Track cost and financial metrics"""
    try:
        # Update Prometheus metrics
        COST_BY_SERVICE.labels(
            service_name=event.service_name,
            cost_type=event.cost_type,
            environment=event.environment
        ).set(event.amount)
        
        # Store in memory for analysis
        if 'cost_metrics' not in metrics_store['cost_metrics']:
            metrics_store['cost_metrics']['cost_metrics'] = {}
        
        key = f"{event.service_name}:{event.cost_type}:{event.environment}"
        if key not in metrics_store['cost_metrics']['cost_metrics']:
            metrics_store['cost_metrics']['cost_metrics'][key] = {
                'total_cost': 0.0,
                'cost_history': [],
                'usage_metrics': {}
            }
        
        cost_data = metrics_store['cost_metrics']['cost_metrics'][key]
        cost_data['total_cost'] += event.amount
        cost_data['cost_history'].append({
            'timestamp': event.timestamp or datetime.utcnow(),
            'amount': event.amount,
            'currency': event.currency,
            'billing_period': event.billing_period,
            'usage_metrics': event.usage_metrics or {}
        })
        
        # Update usage metrics
        if event.usage_metrics:
            for metric_name, metric_value in event.usage_metrics.items():
                if metric_name not in cost_data['usage_metrics']:
                    cost_data['usage_metrics'][metric_name] = []
                cost_data['usage_metrics'][metric_name].append(metric_value)
        
        logger.info(
            "Cost metric tracked",
            service_name=event.service_name,
            cost_type=event.cost_type,
            environment=event.environment,
            amount=event.amount,
            currency=event.currency
        )
        
        return {"status": "success", "message": "Cost metric tracked"}
        
    except Exception as e:
        logger.error("Failed to track cost metric", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track cost metric")


@router.post("/compliance-violation")
async def track_compliance_violation(event: ComplianceViolationEvent):
    """Track compliance violations"""
    try:
        # Update Prometheus metrics
        COMPLIANCE_VIOLATIONS.labels(
            standard=event.standard,
            violation_type=event.violation_type,
            severity=event.severity,
            department=event.department
        ).inc()
        
        # Store in memory for analysis
        if 'violations' not in metrics_store['compliance_metrics']:
            metrics_store['compliance_metrics']['violations'] = {}
        
        key = f"{event.standard}:{event.violation_type}"
        if key not in metrics_store['compliance_metrics']['violations']:
            metrics_store['compliance_metrics']['violations'][key] = {
                'count': 0,
                'violations': []
            }
        
        compliance_data = metrics_store['compliance_metrics']['violations'][key]
        compliance_data['count'] += 1
        
        compliance_data['violations'].append({
            'timestamp': event.timestamp or datetime.utcnow(),
            'severity': event.severity,
            'department': event.department,
            'description': event.description,
            'remediation_status': event.remediation_status,
            'affected_data': event.affected_data,
            'metadata': event.metadata or {}
        })
        
        logger.warning(
            "Compliance violation tracked",
            standard=event.standard,
            violation_type=event.violation_type,
            severity=event.severity,
            department=event.department,
            remediation_status=event.remediation_status
        )
        
        return {"status": "success", "message": "Compliance violation tracked"}
        
    except Exception as e:
        logger.error("Failed to track compliance violation", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track compliance violation")


@router.post("/audit-event")
async def track_audit_event(event: AuditEvent):
    """Track audit trail events"""
    try:
        # Update Prometheus metrics
        AUDIT_EVENTS.labels(
            event_type=event.event_type,
            user_role=event.user_role,
            resource_type=event.resource_type,
            action_result=event.action_result
        ).inc()
        
        # Store in memory for analysis
        if 'audit_events' not in metrics_store['compliance_metrics']:
            metrics_store['compliance_metrics']['audit_events'] = []
        
        audit_data = {
            'timestamp': event.timestamp or datetime.utcnow(),
            'event_type': event.event_type,
            'user_role': event.user_role,
            'resource_type': event.resource_type,
            'action': event.action,
            'action_result': event.action_result,
            'resource_id': event.resource_id,
            'user_id': event.user_id,
            'ip_address': event.ip_address,
            'metadata': event.metadata or {}
        }
        
        metrics_store['compliance_metrics']['audit_events'].append(audit_data)
        
        logger.info(
            "Audit event tracked",
            event_type=event.event_type,
            user_role=event.user_role,
            resource_type=event.resource_type,
            action=event.action,
            action_result=event.action_result,
            user_id=event.user_id
        )
        
        return {"status": "success", "message": "Audit event tracked"}
        
    except Exception as e:
        logger.error("Failed to track audit event", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track audit event")


@router.post("/application-health")
async def track_application_health(event: ApplicationHealthEvent):
    """Track custom application health metrics"""
    try:
        # Update Prometheus metrics
        APPLICATION_HEALTH_SCORE.labels(
            app_name=event.app_name,
            environment=event.environment,
            health_category=event.health_category
        ).set(event.score)
        
        # Store in memory for analysis
        if 'health_scores' not in metrics_store['application_health_metrics']:
            metrics_store['application_health_metrics']['health_scores'] = {}
        
        key = f"{event.app_name}:{event.environment}:{event.health_category}"
        if key not in metrics_store['application_health_metrics']['health_scores']:
            metrics_store['application_health_metrics']['health_scores'][key] = {
                'scores': [],
                'factors': {}
            }
        
        health_data = metrics_store['application_health_metrics']['health_scores'][key]
        health_data['scores'].append({
            'timestamp': event.timestamp or datetime.utcnow(),
            'score': event.score,
            'factors': event.factors or {}
        })
        
        # Update factor tracking
        if event.factors:
            for factor_name, factor_value in event.factors.items():
                if factor_name not in health_data['factors']:
                    health_data['factors'][factor_name] = []
                health_data['factors'][factor_name].append({
                    'timestamp': event.timestamp or datetime.utcnow(),
                    'value': factor_value
                })
        
        logger.info(
            "Application health tracked",
            app_name=event.app_name,
            environment=event.environment,
            health_category=event.health_category,
            score=event.score
        )
        
        return {"status": "success", "message": "Application health tracked"}
        
    except Exception as e:
        logger.error("Failed to track application health", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track application health")


@router.post("/anomaly-detection")
async def track_anomaly_detection(event: AnomalyDetectionEvent):
    """Track anomaly detection events"""
    try:
        # Update Prometheus metrics
        ANOMALY_DETECTION_EVENTS.labels(
            anomaly_type=event.anomaly_type,
            severity=event.severity,
            metric_name=event.metric_name,
            detection_method=event.detection_method
        ).inc()
        
        # Store in memory for analysis
        if 'anomalies' not in metrics_store['analytics_metrics']:
            metrics_store['analytics_metrics']['anomalies'] = {}
        
        if event.anomaly_type not in metrics_store['analytics_metrics']['anomalies']:
            metrics_store['analytics_metrics']['anomalies'][event.anomaly_type] = {
                'count': 0,
                'anomalies': []
            }
        
        anomaly_data = metrics_store['analytics_metrics']['anomalies'][event.anomaly_type]
        anomaly_data['count'] += 1
        
        anomaly_data['anomalies'].append({
            'timestamp': event.timestamp or datetime.utcnow(),
            'severity': event.severity,
            'metric_name': event.metric_name,
            'detection_method': event.detection_method,
            'confidence': event.confidence,
            'baseline_value': event.baseline_value,
            'actual_value': event.actual_value,
            'description': event.description
        })
        
        logger.info(
            "Anomaly detected",
            anomaly_type=event.anomaly_type,
            severity=event.severity,
            metric_name=event.metric_name,
            confidence=event.confidence,
            detection_method=event.detection_method
        )
        
        return {"status": "success", "message": "Anomaly detection tracked"}
        
    except Exception as e:
        logger.error("Failed to track anomaly detection", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track anomaly detection")


@router.get("/metrics", response_model=CustomMetricsResponse)
async def get_custom_metrics(
    category: Optional[str] = Query(None, description="Filter by category: business, security, cost, compliance, health, analytics"),
    hours: int = Query(24, description="Hours of data to retrieve")
):
    """Get comprehensive custom metrics"""
    try:
        # Business metrics
        business_metrics = {}
        business_data = metrics_store.get('custom_business_metrics', {})
        
        # Business events summary
        business_events = business_data.get('business_events', {})
        for key, data in business_events.items():
            parts = key.split(':')
            business_metrics[key] = {
                'event_type': parts[0] if parts else 'unknown',
                'product': parts[1] if len(parts) > 1 else 'unknown',
                'user_segment': parts[2] if len(parts) > 2 else 'unknown',
                'count': data.get('count', 0),
                'total_value': data.get('total_value', 0.0),
                'average_value': data.get('total_value', 0) / max(data.get('count', 1), 1)
            }
        
        # Security metrics
        security_metrics = {}
        security_data = metrics_store.get('security_metrics', {})
        
        # Security events summary
        security_events = security_data.get('security_events', {})
        for key, data in security_events.items():
            parts = key.split(':')
            security_metrics[key] = {
                'event_type': parts[0] if parts else 'unknown',
                'severity': parts[1] if len(parts) > 1 else 'unknown',
                'count': data.get('count', 0)
            }
        
        # Threat summary
        threats = security_data.get('threats', {})
        security_metrics['threat_summary'] = {
            threat_type: threat_data.get('count', 0)
            for threat_type, threat_data in threats.items()
        }
        
        # Cost metrics
        cost_metrics = {}
        cost_data = metrics_store.get('cost_metrics', {})
        
        cost_metrics_data = cost_data.get('cost_metrics', {})
        for key, data in cost_metrics_data.items():
            parts = key.split(':')
            cost_metrics[key] = {
                'service_name': parts[0] if parts else 'unknown',
                'cost_type': parts[1] if len(parts) > 1 else 'unknown',
                'environment': parts[2] if len(parts) > 2 else 'unknown',
                'total_cost': data.get('total_cost', 0.0),
                'cost_history_count': len(data.get('cost_history', []))
            }
        
        # Compliance metrics
        compliance_metrics = {}
        compliance_data = metrics_store.get('compliance_metrics', {})
        
        # Violations summary
        violations = compliance_data.get('violations', {})
        for key, data in violations.items():
            parts = key.split(':')
            compliance_metrics[key] = {
                'standard': parts[0] if parts else 'unknown',
                'violation_type': parts[1] if len(parts) > 1 else 'unknown',
                'count': data.get('count', 0)
            }
        
        compliance_metrics['audit_events_count'] = len(compliance_data.get('audit_events', []))
        
        # Application health metrics
        application_health = {}
        health_data = metrics_store.get('application_health_metrics', {})
        
        health_scores = health_data.get('health_scores', {})
        for key, data in health_scores.items():
            parts = key.split(':')
            scores = data.get('scores', [])
            application_health[key] = {
                'app_name': parts[0] if parts else 'unknown',
                'environment': parts[1] if len(parts) > 1 else 'unknown',
                'health_category': parts[2] if len(parts) > 2 else 'unknown',
                'latest_score': scores[-1]['score'] if scores else 0,
                'average_score': sum(s['score'] for s in scores) / len(scores) if scores else 0,
                'score_count': len(scores)
            }
        
        # Analytics metrics
        analytics_metrics = {}
        analytics_data = metrics_store.get('analytics_metrics', {})
        
        anomalies = analytics_data.get('anomalies', {})
        for anomaly_type, data in anomalies.items():
            analytics_metrics[f"anomaly_{anomaly_type}"] = {
                'count': data.get('count', 0),
                'recent_anomalies': len(data.get('anomalies', []))
            }
        
        return CustomMetricsResponse(
            business_metrics=business_metrics,
            security_metrics=security_metrics,
            cost_metrics=cost_metrics,
            compliance_metrics=compliance_metrics,
            application_health=application_health,
            analytics_metrics=analytics_metrics,
            last_updated=metrics_store['last_updated']
        )
        
    except Exception as e:
        logger.error("Failed to get custom metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve custom metrics")


@router.get("/security-dashboard")
async def get_security_dashboard():
    """Get security monitoring dashboard data"""
    try:
        security_data = metrics_store.get('security_metrics', {})
        
        # Security overview
        total_security_events = sum(
            data.get('count', 0) 
            for data in security_data.get('security_events', {}).values()
        )
        
        total_threats = sum(
            data.get('count', 0) 
            for data in security_data.get('threats', {}).values()
        )
        
        # Recent security events
        recent_events = []
        for event_data in security_data.get('security_events', {}).values():
            events = event_data.get('events', [])
            recent_events.extend(events[-5:])  # Last 5 events per type
        
        # Sort by timestamp and get latest 20
        recent_events.sort(key=lambda x: x['timestamp'], reverse=True)
        recent_events = recent_events[:20]
        
        # Threat breakdown
        threat_breakdown = {}
        for threat_type, data in security_data.get('threats', {}).items():
            threat_breakdown[threat_type] = {
                'count': data.get('count', 0),
                'latest_threats': data.get('threats', [])[-3:]  # Last 3 threats
            }
        
        # Authentication summary
        auth_summary = {}
        for key, data in security_data.get('auth_events', {}).values():
            parts = key.split(':')
            auth_method = parts[0] if parts else 'unknown'
            result = parts[1] if len(parts) > 1 else 'unknown'
            
            if auth_method not in auth_summary:
                auth_summary[auth_method] = {'success': 0, 'failure': 0}
            
            if result == 'success':
                auth_summary[auth_method]['success'] += data.get('count', 0)
            else:
                auth_summary[auth_method]['failure'] += data.get('count', 0)
        
        return {
            'security_overview': {
                'total_security_events': total_security_events,
                'total_threats_detected': total_threats,
                'active_threats': len([
                    t for threats in security_data.get('threats', {}).values()
                    for t in threats.get('threats', [])
                    if t.get('mitigation_status') != 'resolved'
                ])
            },
            'recent_events': recent_events,
            'threat_breakdown': threat_breakdown,
            'authentication_summary': auth_summary,
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get security dashboard", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve security dashboard")


@router.get("/cost-analysis")
async def get_cost_analysis(
    service: Optional[str] = Query(None, description="Filter by service name"),
    hours: int = Query(24, description="Hours of data to analyze")
):
    """Get cost analysis and optimization insights"""
    try:
        cost_data = metrics_store.get('cost_metrics', {})
        cost_metrics = cost_data.get('cost_metrics', {})
        
        # Cost breakdown by service
        cost_by_service = {}
        for key, data in cost_metrics.items():
            parts = key.split(':')
            service_name = parts[0] if parts else 'unknown'
            
            if service and service_name != service:
                continue
            
            if service_name not in cost_by_service:
                cost_by_service[service_name] = {
                    'total_cost': 0.0,
                    'cost_types': {},
                    'environments': {}
                }
            
            cost_type = parts[1] if len(parts) > 1 else 'unknown'
            environment = parts[2] if len(parts) > 2 else 'unknown'
            
            cost_by_service[service_name]['total_cost'] += data.get('total_cost', 0.0)
            
            if cost_type not in cost_by_service[service_name]['cost_types']:
                cost_by_service[service_name]['cost_types'][cost_type] = 0.0
            cost_by_service[service_name]['cost_types'][cost_type] += data.get('total_cost', 0.0)
            
            if environment not in cost_by_service[service_name]['environments']:
                cost_by_service[service_name]['environments'][environment] = 0.0
            cost_by_service[service_name]['environments'][environment] += data.get('total_cost', 0.0)
        
        # Cost trends
        cost_trends = {}
        for key, data in cost_metrics.items():
            cost_history = data.get('cost_history', [])
            if cost_history:
                # Calculate trend (simple linear approximation)
                if len(cost_history) >= 2:
                    first_amount = cost_history[0]['amount']
                    last_amount = cost_history[-1]['amount']
                    trend = ((last_amount - first_amount) / first_amount) * 100 if first_amount > 0 else 0
                    cost_trends[key] = {
                        'trend_percent': round(trend, 2),
                        'latest_amount': last_amount,
                        'history_count': len(cost_history)
                    }
        
        # Usage efficiency analysis
        usage_efficiency = {}
        for key, data in cost_metrics.items():
            usage_metrics = data.get('usage_metrics', {})
            if usage_metrics:
                efficiency_score = 0.0
                for metric_name, values in usage_metrics.items():
                    if values:
                        # Simple efficiency calculation (could be more sophisticated)
                        avg_usage = sum(values) / len(values)
                        efficiency_score += min(avg_usage / 100, 1.0)  # Normalize to 0-1
                
                if len(usage_metrics) > 0:
                    efficiency_score = (efficiency_score / len(usage_metrics)) * 100
                    usage_efficiency[key] = {
                        'efficiency_score': round(efficiency_score, 2),
                        'usage_metrics_count': len(usage_metrics)
                    }
        
        return {
            'cost_by_service': cost_by_service,
            'cost_trends': cost_trends,
            'usage_efficiency': usage_efficiency,
            'total_services': len(cost_by_service),
            'analysis_period_hours': hours,
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get cost analysis", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve cost analysis")
