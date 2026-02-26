"""
Frontend monitoring endpoints for 3-tier architecture
"""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
import structlog

from ...monitoring import (
    update_frontend_metrics,
    FRONTEND_PAGE_VIEWS,
    FRONTEND_PAGE_LOAD_TIME,
    FRONTEND_CORE_WEB_VITALS,
    FRONTEND_USER_INTERACTIONS,
    FRONTEND_JAVASCRIPT_ERRORS,
    metrics_store
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/frontend", tags=["frontend"])


class PageViewEvent(BaseModel):
    page: str
    load_time: float
    user_agent: str
    referrer: Optional[str] = ""
    browser: str
    device_type: str
    timestamp: Optional[datetime] = None


class CoreWebVitalEvent(BaseModel):
    metric_type: str  # LCP, FID, CLS
    value: float
    page: str
    device_type: str
    timestamp: Optional[datetime] = None


class UserInteractionEvent(BaseModel):
    interaction_type: str  # click, scroll, form_submit, etc.
    element: str
    page: str
    timestamp: Optional[datetime] = None


class JavaScriptErrorEvent(BaseModel):
    error_type: str
    error_message: str
    page: str
    browser: str
    stack_trace: Optional[str] = ""
    timestamp: Optional[datetime] = None


class FrontendMetricsResponse(BaseModel):
    page_views: Dict[str, int]
    average_load_times: Dict[str, float]
    browser_distribution: Dict[str, Dict[str, int]]
    device_distribution: Dict[str, Dict[str, int]]
    core_web_vitals: Dict[str, Dict[str, List[float]]]
    user_interactions: Dict[str, int]
    javascript_errors: Dict[str, int]
    last_updated: datetime


@router.post("/page-view")
async def track_page_view(event: PageViewEvent):
    """Track page view events"""
    try:
        # Update metrics
        update_frontend_metrics(
            page=event.page,
            load_time=event.load_time,
            user_agent=event.user_agent,
            referrer=event.referrer or "",
            browser=event.browser,
            device_type=event.device_type
        )
        
        logger.info(
            "Page view tracked",
            page=event.page,
            load_time=event.load_time,
            browser=event.browser,
            device_type=event.device_type
        )
        
        return {"status": "success", "message": "Page view tracked"}
        
    except Exception as e:
        logger.error("Failed to track page view", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track page view")


@router.post("/core-web-vitals")
async def track_core_web_vital(event: CoreWebVitalEvent):
    """Track Core Web Vitals metrics"""
    try:
        # Update Core Web Vitals metric
        FRONTEND_CORE_WEB_VITALS.labels(
            metric_type=event.metric_type,
            page=event.page,
            device_type=event.device_type
        ).observe(event.value)
        
        # Store in memory for analysis
        if 'core_web_vitals' not in metrics_store['frontend_metrics']:
            metrics_store['frontend_metrics']['core_web_vitals'] = {}
        
        key = f"{event.page}:{event.metric_type}:{event.device_type}"
        if key not in metrics_store['frontend_metrics']['core_web_vitals']:
            metrics_store['frontend_metrics']['core_web_vitals'][key] = []
        
        metrics_store['frontend_metrics']['core_web_vitals'][key].append(event.value)
        
        logger.info(
            "Core Web Vital tracked",
            metric_type=event.metric_type,
            page=event.page,
            value=event.value,
            device_type=event.device_type
        )
        
        return {"status": "success", "message": "Core Web Vital tracked"}
        
    except Exception as e:
        logger.error("Failed to track Core Web Vital", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track Core Web Vital")


@router.post("/user-interaction")
async def track_user_interaction(event: UserInteractionEvent):
    """Track user interaction events"""
    try:
        # Update user interaction metric
        FRONTEND_USER_INTERACTIONS.labels(
            interaction_type=event.interaction_type,
            element=event.element,
            page=event.page
        ).inc()
        
        logger.info(
            "User interaction tracked",
            interaction_type=event.interaction_type,
            element=event.element,
            page=event.page
        )
        
        return {"status": "success", "message": "User interaction tracked"}
        
    except Exception as e:
        logger.error("Failed to track user interaction", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track user interaction")


@router.post("/javascript-error")
async def track_javascript_error(event: JavaScriptErrorEvent):
    """Track JavaScript errors"""
    try:
        # Update JavaScript error metric
        FRONTEND_JAVASCRIPT_ERRORS.labels(
            error_type=event.error_type,
            page=event.page,
            browser=event.browser
        ).inc()
        
        logger.error(
            "JavaScript error tracked",
            error_type=event.error_type,
            error_message=event.error_message,
            page=event.page,
            browser=event.browser
        )
        
        return {"status": "success", "message": "JavaScript error tracked"}
        
    except Exception as e:
        logger.error("Failed to track JavaScript error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track JavaScript error")


@router.get("/metrics", response_model=FrontendMetricsResponse)
async def get_frontend_metrics(
    page: Optional[str] = Query(None, description="Filter by specific page"),
    hours: int = Query(24, description="Hours of data to retrieve")
):
    """Get comprehensive frontend metrics"""
    try:
        frontend_data = metrics_store.get('frontend_metrics', {})
        
        # Calculate page views
        page_views = {}
        for page_name, data in frontend_data.items():
            if page_name == 'core_web_vitals':
                continue
            if page and page_name != page:
                continue
            page_views[page_name] = data.get('page_views', 0)
        
        # Calculate average load times
        average_load_times = {}
        for page_name, data in frontend_data.items():
            if page_name == 'core_web_vitals':
                continue
            if page and page_name != page:
                continue
            load_times = data.get('load_times', [])
            if load_times:
                average_load_times[page_name] = sum(load_times) / len(load_times)
            else:
                average_load_times[page_name] = 0.0
        
        # Browser distribution
        browser_distribution = {}
        for page_name, data in frontend_data.items():
            if page_name == 'core_web_vitals':
                continue
            if page and page_name != page:
                continue
            browser_distribution[page_name] = data.get('browsers', {})
        
        # Device distribution
        device_distribution = {}
        for page_name, data in frontend_data.items():
            if page_name == 'core_web_vitals':
                continue
            if page and page_name != page:
                continue
            device_distribution[page_name] = data.get('device_types', {})
        
        # Core Web Vitals
        core_web_vitals = frontend_data.get('core_web_vitals', {})
        
        return FrontendMetricsResponse(
            page_views=page_views,
            average_load_times=average_load_times,
            browser_distribution=browser_distribution,
            device_distribution=device_distribution,
            core_web_vitals=core_web_vitals,
            user_interactions={},  # Would need separate tracking
            javascript_errors={},  # Would need separate tracking
            last_updated=metrics_store['last_updated']
        )
        
    except Exception as e:
        logger.error("Failed to get frontend metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve frontend metrics")


@router.get("/performance-summary")
async def get_performance_summary(
    page: Optional[str] = Query(None, description="Filter by specific page")
):
    """Get performance summary for frontend"""
    try:
        frontend_data = metrics_store.get('frontend_metrics', {})
        
        total_page_views = 0
        total_load_time = 0.0
        load_times_count = 0
        
        for page_name, data in frontend_data.items():
            if page_name == 'core_web_vitals':
                continue
            if page and page_name != page:
                continue
                
            total_page_views += data.get('page_views', 0)
            page_load_times = data.get('load_times', [])
            total_load_time += sum(page_load_times)
            load_times_count += len(page_load_times)
        
        average_load_time = total_load_time / max(load_times_count, 1)
        
        # Get Core Web Vitals summary
        core_web_vitals_summary = {}
        core_web_vitals_data = frontend_data.get('core_web_vitals', {})
        
        for key, values in core_web_vitals_data.items():
            if values:
                parts = key.split(':')
                metric_type = parts[1] if len(parts) > 1 else 'unknown'
                
                if metric_type not in core_web_vitals_summary:
                    core_web_vitals_summary[metric_type] = []
                core_web_vitals_summary[metric_type].extend(values)
        
        # Calculate percentiles for each metric type
        core_web_vitals_percentiles = {}
        for metric_type, values in core_web_vitals_summary.items():
            if values:
                sorted_values = sorted(values)
                n = len(sorted_values)
                core_web_vitals_percentiles[metric_type] = {
                    'p50': sorted_values[int(n * 0.5)],
                    'p75': sorted_values[int(n * 0.75)],
                    'p90': sorted_values[int(n * 0.90)],
                    'p95': sorted_values[int(n * 0.95)],
                    'count': len(values)
                }
        
        return {
            'total_page_views': total_page_views,
            'average_load_time_seconds': round(average_load_time, 3),
            'core_web_vitals': core_web_vitals_percentiles,
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get performance summary", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve performance summary")


@router.get("/real-user-monitoring")
async def get_real_user_monitoring(
    minutes: int = Query(60, description="Minutes of data to analyze")
):
    """Get real user monitoring data"""
    try:
        # This would typically integrate with RUM data from New Relic
        # For now, return synthetic data based on collected metrics
        
        frontend_data = metrics_store.get('frontend_metrics', {})
        
        # Calculate performance by geographic location (simulated)
        performance_by_location = {
            'US-East': {'avg_load_time': 1.2, 'page_views': 150},
            'US-West': {'avg_load_time': 1.5, 'page_views': 120},
            'Europe': {'avg_load_time': 2.1, 'page_views': 80},
            'Asia': {'avg_load_time': 3.2, 'page_views': 60}
        }
        
        # Calculate performance by browser
        performance_by_browser = {}
        for page_name, data in frontend_data.items():
            if page_name == 'core_web_vitals':
                continue
                
            browsers = data.get('browsers', {})
            for browser, count in browsers.items():
                if browser not in performance_by_browser:
                    performance_by_browser[browser] = {'page_views': 0, 'avg_load_time': 0}
                performance_by_browser[browser]['page_views'] += count
        
        # Calculate performance by device type
        performance_by_device = {}
        for page_name, data in frontend_data.items():
            if page_name == 'core_web_vitals':
                continue
                
            devices = data.get('device_types', {})
            for device, count in devices.items():
                if device not in performance_by_device:
                    performance_by_device[device] = {'page_views': 0}
                performance_by_device[device]['page_views'] += count
        
        return {
            'performance_by_location': performance_by_location,
            'performance_by_browser': performance_by_browser,
            'performance_by_device': performance_by_device,
            'analysis_period_minutes': minutes,
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get real user monitoring data", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve RUM data")
