"""
Synthetic monitoring endpoints for the Observability as Code API
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import structlog
import asyncio
import aiohttp
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from ...database import get_db
from ...monitoring import (
    update_synthetic_metrics, 
    get_synthetic_metrics_summary,
    SYNTHETIC_CHECKS_TOTAL,
    SYNTHETIC_FAILURES_TOTAL,
    SYNTHETIC_RESPONSE_TIME,
    SYNTHETIC_AVAILABILITY
)
from ...schemas import SyntheticCheckCreate, SyntheticCheckResponse, SyntheticMetricsResponse

logger = structlog.get_logger(__name__)

router = APIRouter()

# Default synthetic check configurations
DEFAULT_LOCATIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
DEFAULT_CHECK_TYPES = ["ping", "http", "api", "ssl"]

# In-memory storage for synthetic check configurations
synthetic_checks_config = {
    "ping_checks": [
        {"target": "google.com", "interval": 60, "locations": DEFAULT_LOCATIONS},
        {"target": "cloudflare.com", "interval": 60, "locations": DEFAULT_LOCATIONS}
    ],
    "http_checks": [
        {"url": "https://api.github.com", "method": "GET", "interval": 300, "locations": DEFAULT_LOCATIONS},
        {"url": "https://httpbin.org/status/200", "method": "GET", "interval": 300, "locations": DEFAULT_LOCATIONS}
    ],
    "api_checks": [
        {"url": "https://jsonplaceholder.typicode.com/posts/1", "method": "GET", "interval": 300, "locations": DEFAULT_LOCATIONS}
    ]
}


@router.get("/synthetics/status", response_model=Dict[str, Any])
async def get_synthetic_status():
    """Get overall synthetic monitoring status"""
    try:
        synthetic_summary = get_synthetic_metrics_summary()
        
        return {
            "status": "active",
            "total_checks_configured": len(synthetic_checks_config["ping_checks"]) + 
                                    len(synthetic_checks_config["http_checks"]) + 
                                    len(synthetic_checks_config["api_checks"]),
            "monitoring_locations": DEFAULT_LOCATIONS,
            "check_types": DEFAULT_CHECK_TYPES,
            "metrics": synthetic_summary,
            "last_updated": datetime.utcnow()
        }
    except Exception as e:
        logger.error("Failed to get synthetic status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/synthetics/metrics", response_model=SyntheticMetricsResponse)
async def get_synthetic_metrics():
    """Get synthetic monitoring metrics"""
    try:
        metrics_summary = get_synthetic_metrics_summary()
        
        return SyntheticMetricsResponse(
            synthetic_checks_last_5_minutes=metrics_summary.get("synthetic_checks_last_5_minutes", 0),
            synthetic_success_last_5_minutes=metrics_summary.get("synthetic_success_last_5_minutes", 0),
            synthetic_failures_last_5_minutes=metrics_summary.get("synthetic_failures_last_5_minutes", 0),
            synthetic_checks_last_hour=metrics_summary.get("synthetic_checks_last_hour", 0),
            synthetic_success_last_hour=metrics_summary.get("synthetic_success_last_hour", 0),
            synthetic_failures_last_hour=metrics_summary.get("synthetic_failures_last_hour", 0),
            success_rate_5min_percent=metrics_summary.get("success_rate_5min_percent", 0),
            success_rate_hour_percent=metrics_summary.get("success_rate_hour_percent", 0),
            average_response_time_seconds=metrics_summary.get("average_response_time_seconds", 0),
            last_updated=metrics_summary.get("last_updated", datetime.utcnow())
        )
    except Exception as e:
        logger.error("Failed to get synthetic metrics", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthetics/check", response_model=SyntheticCheckResponse)
async def run_synthetic_check(
    check_type: str = Query(..., description="Type of synthetic check"),
    target: str = Query(..., description="Target URL or hostname"),
    location: str = Query("us-east-1", description="Monitoring location"),
    timeout: int = Query(30, description="Timeout in seconds")
):
    """Run a single synthetic check"""
    try:
        start_time = datetime.utcnow()
        
        if check_type == "ping":
            result = await run_ping_check(target, timeout)
        elif check_type == "http":
            result = await run_http_check(target, timeout)
        elif check_type == "ssl":
            result = await run_ssl_check(target, timeout)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported check type: {check_type}")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Update metrics
        update_synthetic_metrics(
            check_type=check_type,
            location=location,
            status="success" if result["success"] else "failed",
            duration=duration,
            error_type=result.get("error_type") if not result["success"] else None
        )
        
        return SyntheticCheckResponse(
            check_type=check_type,
            target=target,
            location=location,
            success=result["success"],
            response_time_seconds=duration,
            status_code=result.get("status_code"),
            error_message=result.get("error_message"),
            timestamp=start_time
        )
        
    except Exception as e:
        logger.error("Synthetic check failed", error=str(e), check_type=check_type, target=target)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/synthetics/batch")
async def run_batch_synthetic_checks():
    """Run all configured synthetic checks"""
    try:
        results = []
        
        # Run ping checks
        for check in synthetic_checks_config["ping_checks"]:
            for location in check["locations"]:
                try:
                    result = await run_ping_check(check["target"], 30)
                    duration = 0.1  # Simulated duration
                    update_synthetic_metrics(
                        check_type="ping",
                        location=location,
                        status="success" if result["success"] else "failed",
                        duration=duration,
                        error_type=result.get("error_type") if not result["success"] else None
                    )
                    results.append({
                        "check_type": "ping",
                        "target": check["target"],
                        "location": location,
                        "success": result["success"],
                        "response_time_seconds": duration
                    })
                except Exception as e:
                    logger.error("Batch ping check failed", error=str(e), target=check["target"])
        
        # Run HTTP checks
        for check in synthetic_checks_config["http_checks"]:
            for location in check["locations"]:
                try:
                    result = await run_http_check(check["url"], 30)
                    duration = 0.2  # Simulated duration
                    update_synthetic_metrics(
                        check_type="http",
                        location=location,
                        status="success" if result["success"] else "failed",
                        duration=duration,
                        error_type=result.get("error_type") if not result["success"] else None
                    )
                    results.append({
                        "check_type": "http",
                        "target": check["url"],
                        "location": location,
                        "success": result["success"],
                        "response_time_seconds": duration
                    })
                except Exception as e:
                    logger.error("Batch HTTP check failed", error=str(e), target=check["url"])
        
        return {
            "message": "Batch synthetic checks completed",
            "total_checks": len(results),
            "successful_checks": sum(1 for r in results if r["success"]),
            "failed_checks": sum(1 for r in results if not r["success"]),
            "results": results,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error("Batch synthetic checks failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/synthetics/config")
async def get_synthetic_config():
    """Get current synthetic check configuration"""
    return {
        "ping_checks": synthetic_checks_config["ping_checks"],
        "http_checks": synthetic_checks_config["http_checks"],
        "api_checks": synthetic_checks_config["api_checks"],
        "locations": DEFAULT_LOCATIONS,
        "check_types": DEFAULT_CHECK_TYPES
    }


@router.post("/synthetics/config")
async def update_synthetic_config(config: Dict[str, Any]):
    """Update synthetic check configuration"""
    try:
        if "ping_checks" in config:
            synthetic_checks_config["ping_checks"] = config["ping_checks"]
        if "http_checks" in config:
            synthetic_checks_config["http_checks"] = config["http_checks"]
        if "api_checks" in config:
            synthetic_checks_config["api_checks"] = config["api_checks"]
        
        logger.info("Synthetic configuration updated", config=config)
        
        return {
            "message": "Synthetic configuration updated successfully",
            "config": synthetic_checks_config
        }
        
    except Exception as e:
        logger.error("Failed to update synthetic config", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Helper functions for synthetic checks
async def run_ping_check(target: str, timeout: int) -> Dict[str, Any]:
    """Run a ping check"""
    try:
        # Simulate ping check (in real implementation, use subprocess or ping library)
        await asyncio.sleep(0.05)  # Simulate network latency
        
        return {
            "success": True,
            "response_time_ms": 50,
            "status_code": None
        }
    except Exception as e:
        return {
            "success": False,
            "error_message": str(e),
            "error_type": "network_error"
        }


async def run_http_check(url: str, timeout: int) -> Dict[str, Any]:
    """Run an HTTP check"""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            async with session.get(url) as response:
                content = await response.text()
                
                return {
                    "success": response.status < 400,
                    "status_code": response.status,
                    "response_time_ms": int(response.headers.get("X-Response-Time", 100)),
                    "content_length": len(content)
                }
    except Exception as e:
        return {
            "success": False,
            "error_message": str(e),
            "error_type": "http_error"
        }


async def run_ssl_check(hostname: str, timeout: int) -> Dict[str, Any]:
    """Run an SSL certificate check"""
    try:
        # Simulate SSL check (in real implementation, use ssl library)
        await asyncio.sleep(0.1)
        
        return {
            "success": True,
            "days_until_expiry": 90,
            "certificate_valid": True
        }
    except Exception as e:
        return {
            "success": False,
            "error_message": str(e),
            "error_type": "ssl_error"
        }
