"""
Pydantic schemas for API request/response models
"""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum


class Environment(str, Enum):
    PRODUCTION = "production"
    STAGING = "staging"
    DEVELOPMENT = "development"


class AlertType(str, Enum):
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    DISK_USAGE = "disk_usage"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    POD_HEALTH = "pod_health"


class DashboardType(str, Enum):
    INFRASTRUCTURE = "infrastructure"
    APPLICATION_PERFORMANCE = "application_performance"
    ERROR_ANALYSIS = "error_analysis"
    BUSINESS_METRICS = "business_metrics"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class DeploymentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Base schemas
class BaseSchema(BaseModel):
    class Config:
        from_attributes = True


# Application schemas
class ApplicationBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    environment: Environment
    entity_id: str = Field(..., min_length=1)
    description: Optional[str] = None
    team: Optional[str] = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    environment: Optional[Environment] = None
    entity_id: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None
    team: Optional[str] = None
    status: Optional[str] = None


class Application(ApplicationBase):
    id: str
    status: str
    coverage_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class ApplicationList(BaseModel):
    applications: List[Application]
    pagination: Dict[str, Any]


# Alert schemas
class AlertBase(BaseSchema):
    name: str = Field(..., min_length=1)
    type: AlertType
    enabled: bool = True
    nrql_query: str = Field(..., min_length=1)
    thresholds: Dict[str, Any] = Field(...)
    severity: Severity = Severity.WARNING


class AlertCreate(AlertBase):
    pass


class AlertUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1)
    type: Optional[AlertType] = None
    enabled: Optional[bool] = None
    nrql_query: Optional[str] = Field(None, min_length=1)
    thresholds: Optional[Dict[str, Any]] = None
    severity: Optional[Severity] = None


class Alert(AlertBase):
    id: str
    application_id: str
    created_at: datetime
    updated_at: datetime


# Dashboard schemas
class DashboardBase(BaseSchema):
    name: str = Field(..., min_length=1)
    type: DashboardType
    description: Optional[str] = None
    widgets: List[Dict[str, Any]] = Field(..., min_items=1)


class DashboardCreate(DashboardBase):
    pass


class DashboardUpdate(BaseSchema):
    name: Optional[str] = Field(None, min_length=1)
    type: Optional[DashboardType] = None
    description: Optional[str] = None
    widgets: Optional[List[Dict[str, Any]]] = Field(None, min_items=1)


class Dashboard(DashboardBase):
    id: str
    application_id: str
    widgets_count: int
    dashboard_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Deployment schemas
class DeploymentBase(BaseSchema):
    application_ids: List[str] = Field(..., min_items=1)
    dry_run: bool = False
    force: bool = False
    components: Optional[List[str]] = Field(default=["alerts", "dashboards", "policies"])


class DeploymentCreate(DeploymentBase):
    pass


class Deployment(BaseSchema):
    id: str
    application_id: str
    status: DeploymentStatus
    components_deployed: List[str]
    deployment_type: str
    dry_run: bool
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None


class DeploymentResponse(BaseModel):
    deployment_id: str
    status: str
    applications: List[Dict[str, Any]]
    estimated_completion: datetime


# User schemas
class UserBase(BaseSchema):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseSchema):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=8)


class User(UserBase):
    id: str
    is_superuser: bool
    created_at: datetime
    last_login: Optional[datetime] = None


# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []


# API Key schemas
class APIKeyBase(BaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    permissions: Optional[List[str]] = None
    expires_at: Optional[datetime] = None


class APIKeyCreate(APIKeyBase):
    pass


class APIKey(APIKeyBase):
    id: str
    key: str
    user_id: str
    is_active: bool
    last_used: Optional[datetime] = None
    created_at: datetime


# Coverage and Compliance schemas
class CoverageMetrics(BaseSchema):
    application_name: str
    overall_score: float
    alert_coverage: float
    dashboard_coverage: float
    entity_coverage: float
    missing_alerts: List[str]
    missing_dashboards: List[str]
    recommendations: List[str]


class CoverageReport(BaseModel):
    overall_coverage: float
    application_count: int
    applications: List[CoverageMetrics]
    generated_at: datetime


class ComplianceRequirement(BaseSchema):
    name: str
    met: bool
    description: str
    severity: str = "medium"


class ComplianceStandard(BaseSchema):
    name: str
    compliant: bool
    score: float
    requirements: List[ComplianceRequirement]


class ComplianceResult(BaseSchema):
    name: str
    compliant: bool
    score: float
    violations: List[str]


class ComplianceReport(BaseModel):
    overall_compliance: float
    applications: List[ComplianceResult]
    standards: Dict[str, ComplianceStandard]
    generated_at: datetime


# Health check schemas
class HealthCheck(BaseModel):
    status: str
    timestamp: datetime
    version: str
    checks: Dict[str, Dict[str, Any]]


# Error schemas
class ErrorDetail(BaseModel):
    loc: List[Union[str, int]]
    msg: str
    type: str


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime


# Synthetic monitoring schemas
class SyntheticCheckType(str, Enum):
    PING = "ping"
    HTTP = "http"
    API = "api"
    SSL = "ssl"


class SyntheticCheckCreate(BaseModel):
    check_type: SyntheticCheckType
    target: str
    location: str = "us-east-1"
    timeout: int = 30
    interval: Optional[int] = None


class SyntheticCheckResponse(BaseModel):
    check_type: str
    target: str
    location: str
    success: bool
    response_time_seconds: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: datetime


class SyntheticMetricsResponse(BaseModel):
    synthetic_checks_last_5_minutes: int
    synthetic_success_last_5_minutes: int
    synthetic_failures_last_5_minutes: int
    synthetic_checks_last_hour: int
    synthetic_success_last_hour: int
    synthetic_failures_last_hour: int
    success_rate_5min_percent: float
    success_rate_hour_percent: float
    average_response_time_seconds: float
    last_updated: datetime


class SyntheticCheckConfig(BaseModel):
    check_type: SyntheticCheckType
    target: str
    interval: int
    locations: List[str]
    method: Optional[str] = "GET"
    headers: Optional[Dict[str, str]] = None
    expected_status_code: Optional[int] = 200


class SyntheticStatusResponse(BaseModel):
    status: str
    total_checks_configured: int
    monitoring_locations: List[str]
    check_types: List[str]
    metrics: Dict[str, Any]
    last_updated: datetime
