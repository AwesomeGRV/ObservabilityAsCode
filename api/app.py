"""
Enhanced FastAPI application for Observability as Code API
"""

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
import structlog
import os

from .database import get_db, init_db, check_db_connection
from .models import Application, Alert, Dashboard, Deployment, User, APIKey
from .schemas import HealthCheck
from .auth import verify_api_key
from .exceptions import (
    observability_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    general_exception_handler
)
from .monitoring import get_health_status, get_prometheus_metrics
from .v1.api import api_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Observability as Code API",
    description="Enhanced API for managing New Relic observability configurations",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add exception handlers
app.add_exception_handler(ObservabilityException, observability_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include API v1 router
app.include_router(api_router, prefix="/api/v1")

# Global instances
nerdgraph_client = None  # Initialize with proper credentials

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Comprehensive health check endpoint"""
    return get_health_status()

@app.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint"""
    metrics_data = get_prometheus_metrics()
    return Response(
        content=metrics_data,
        media_type="text/plain"
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Observability as Code API",
        "version": "2.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Observability as Code API")
    
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database", error=str(e))
        raise
    
    # Initialize New Relic client if credentials are available
    nr_account_id = os.getenv("NEW_RELIC_ACCOUNT_ID")
    nr_api_key = os.getenv("NEW_RELIC_API_KEY")
    
    if nr_account_id and nr_api_key:
        global nerdgraph_client
        from nerdgraph.nerdgraph_client import NERDGraphClient
        nerdgraph_client = NERDGraphClient(nr_account_id, nr_api_key)
        logger.info("New Relic client initialized")
    else:
        logger.warning("New Relic credentials not configured")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Observability as Code API")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=os.getenv("DEBUG", "false").lower() == "true",
        workers=1 if os.getenv("DEBUG", "false").lower() == "true" else 4
    )
