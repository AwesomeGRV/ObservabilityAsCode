"""
Custom exception handlers for the API
"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Union
import structlog

from .schemas import ErrorResponse, ErrorDetail

logger = structlog.get_logger(__name__)


class ObservabilityException(Exception):
    """Base exception for observability API"""
    
    def __init__(
        self,
        message: str,
        error_code: str = "OBS_ERROR",
        status_code: int = 500,
        details: list = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or []
        super().__init__(self.message)


class ApplicationNotFoundError(ObservabilityException):
    """Raised when application is not found"""
    
    def __init__(self, application_id: str):
        super().__init__(
            message=f"Application {application_id} not found",
            error_code="APP_NOT_FOUND",
            status_code=404
        )


class AlertNotFoundError(ObservabilityException):
    """Raised when alert is not found"""
    
    def __init__(self, alert_id: str):
        super().__init__(
            message=f"Alert {alert_id} not found",
            error_code="ALERT_NOT_FOUND",
            status_code=404
        )


class DashboardNotFoundError(ObservabilityException):
    """Raised when dashboard is not found"""
    
    def __init__(self, dashboard_id: str):
        super().__init__(
            message=f"Dashboard {dashboard_id} not found",
            error_code="DASHBOARD_NOT_FOUND",
            status_code=404
        )


class DeploymentError(ObservabilityException):
    """Raised when deployment fails"""
    
    def __init__(self, message: str, details: list = None):
        super().__init__(
            message=f"Deployment failed: {message}",
            error_code="DEPLOYMENT_ERROR",
            status_code=500,
            details=details
        )


class ComplianceError(ObservabilityException):
    """Raised when compliance check fails"""
    
    def __init__(self, message: str):
        super().__init__(
            message=f"Compliance check failed: {message}",
            error_code="COMPLIANCE_ERROR",
            status_code=400
        )


class AuthenticationError(ObservabilityException):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            status_code=401
        )


class AuthorizationError(ObservabilityException):
    """Raised when authorization fails"""
    
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="AUTHZ_ERROR",
            status_code=403
        )


class ValidationError(ObservabilityException):
    """Raised when validation fails"""
    
    def __init__(self, message: str, details: list = None):
        super().__init__(
            message=f"Validation error: {message}",
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details
        )


class DatabaseError(ObservabilityException):
    """Raised when database operation fails"""
    
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            message=message,
            error_code="DB_ERROR",
            status_code=500
        )


class NewRelicAPIError(ObservabilityException):
    """Raised when New Relic API call fails"""
    
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(
            message=f"New Relic API error: {message}",
            error_code="NR_API_ERROR",
            status_code=status_code
        )


async def observability_exception_handler(request: Request, exc: ObservabilityException):
    """Handle custom observability exceptions"""
    logger.error(
        "Observability exception occurred",
        error_code=exc.error_code,
        message=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
        method=request.method
    )
    
    error_details = [
        ErrorDetail(loc=["error"], msg=detail, type="custom_error")
        for detail in exc.details
    ] if exc.details else []
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.error_code,
            message=exc.message,
            details=error_details if error_details else None
        ).dict()
    )


async def http_exception_handler(request: Request, exc: Union[HTTPException, StarletteHTTPException]):
    """Handle HTTP exceptions"""
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTP_ERROR",
            message=exc.detail,
            details=[
                ErrorDetail(loc=["error"], msg=exc.detail, type="http_error")
            ]
        ).dict()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation exceptions"""
    logger.warning(
        "Validation exception occurred",
        errors=exc.errors(),
        path=request.url.path,
        method=request.method
    )
    
    error_details = []
    for error in exc.errors():
        error_details.append(
            ErrorDetail(
                loc=error["loc"],
                msg=error["msg"],
                type=error["type"]
            )
        )
    
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="VALIDATION_ERROR",
            message="Request validation failed",
            details=error_details
        ).dict()
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(
        "Unhandled exception occurred",
        exception=str(exc),
        exception_type=type(exc).__name__,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="INTERNAL_ERROR",
            message="An internal error occurred",
            details=[
                ErrorDetail(
                    loc=["server"],
                    msg="An unexpected error occurred. Please try again later.",
                    type="internal_error"
                )
            ]
        ).dict()
    )
