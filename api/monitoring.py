"""
Monitoring and metrics collection for the API
"""

import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any
from functools import wraps
from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
import structlog

logger = structlog.get_logger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Number of active connections'
)

CPU_USAGE = Gauge(
    'cpu_usage_percent',
    'CPU usage percentage'
)

MEMORY_USAGE = Gauge(
    'memory_usage_percent',
    'Memory usage percentage'
)

DATABASE_CONNECTIONS = Gauge(
    'database_connections_active',
    'Active database connections'
)

API_ERRORS = Counter(
    'api_errors_total',
    'Total API errors',
    ['error_type', 'endpoint']
)

# Synthetic monitoring metrics
SYNTHETIC_CHECKS_TOTAL = Counter(
    'synthetic_checks_total',
    'Total synthetic monitoring checks',
    ['check_type', 'location', 'status']
)

SYNTHETIC_CHECK_DURATION = Histogram(
    'synthetic_check_duration_seconds',
    'Synthetic check duration in seconds',
    ['check_type', 'location']
)

SYNTHETIC_FAILURES_TOTAL = Counter(
    'synthetic_failures_total',
    'Total synthetic check failures',
    ['check_type', 'location', 'error_type']
)

SYNTHETIC_RESPONSE_TIME = Gauge(
    'synthetic_response_time_seconds',
    'Latest synthetic check response time',
    ['check_type', 'location']
)

SYNTHETIC_AVAILABILITY = Gauge(
    'synthetic_availability_percent',
    'Synthetic check availability percentage',
    ['check_type', 'location']
)

# In-memory metrics storage
metrics_store = {
    'requests_per_minute': {},
    'error_rates': {},
    'response_times': {},
    'synthetic_checks': {},
    'synthetic_failures': {},
    'synthetic_response_times': {},
    'last_updated': datetime.utcnow()
}


def track_requests(func):
    """Decorator to track API requests"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            # Extract request information if available
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            
            method = request.method if request else 'unknown'
            endpoint = request.url.path if request else 'unknown'
            
            # Execute the function
            result = await func(*args, **kwargs)
            
            # Record metrics
            duration = time.time() - start_time
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code='200').inc()
            
            # Update in-memory metrics
            update_request_metrics(endpoint, duration)
            
            return result
            
        except Exception as e:
            # Record error metrics
            duration = time.time() - start_time
            error_type = type(e).__name__
            
            if request:
                method = request.method
                endpoint = request.url.path
                REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code='500').inc()
                REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
            
            API_ERRORS.labels(error_type=error_type, endpoint=endpoint).inc()
            update_error_metrics(endpoint, error_type)
            
            logger.error(
                "API request failed",
                error=str(e),
                error_type=error_type,
                duration=duration
            )
            
            raise
    
    return wrapper


def update_request_metrics(endpoint: str, duration: float):
    """Update request metrics in memory"""
    now = datetime.utcnow()
    minute_key = now.strftime('%Y-%m-%d %H:%M')
    
    if minute_key not in metrics_store['requests_per_minute']:
        metrics_store['requests_per_minute'][minute_key] = {}
    
    if endpoint not in metrics_store['requests_per_minute'][minute_key]:
        metrics_store['requests_per_minute'][minute_key][endpoint] = {
            'count': 0,
            'total_duration': 0.0
        }
    
    metrics_store['requests_per_minute'][minute_key][endpoint]['count'] += 1
    metrics_store['requests_per_minute'][minute_key][endpoint]['total_duration'] += duration
    
    # Keep only last 60 minutes of data
    cutoff_time = now - timedelta(minutes=60)
    metrics_store['requests_per_minute'] = {
        k: v for k, v in metrics_store['requests_per_minute'].items()
        if datetime.strptime(k, '%Y-%m-%d %H:%M') > cutoff_time
    }


def update_error_metrics(endpoint: str, error_type: str):
    """Update error metrics in memory"""
    now = datetime.utcnow()
    minute_key = now.strftime('%Y-%m-%d %H:%M')
    
    if minute_key not in metrics_store['error_rates']:
        metrics_store['error_rates'][minute_key] = {}
    
    key = f"{endpoint}:{error_type}"
    if key not in metrics_store['error_rates'][minute_key]:
        metrics_store['error_rates'][minute_key][key] = 0
    
    metrics_store['error_rates'][minute_key][key] += 1
    
    # Keep only last 60 minutes of data
    cutoff_time = now - timedelta(minutes=60)
    metrics_store['error_rates'] = {
        k: v for k, v in metrics_store['error_rates'].items()
        if datetime.strptime(k, '%Y-%m-%d %H:%M') > cutoff_time
    }


def update_synthetic_metrics(check_type: str, location: str, status: str, 
                           duration: float, error_type: str = None):
    """Update synthetic monitoring metrics"""
    now = datetime.utcnow()
    minute_key = now.strftime('%Y-%m-%d %H:%M')
    
    # Update Prometheus metrics
    SYNTHETIC_CHECKS_TOTAL.labels(
        check_type=check_type, 
        location=location, 
        status=status
    ).inc()
    
    SYNTHETIC_CHECK_DURATION.labels(
        check_type=check_type, 
        location=location
    ).observe(duration)
    
    SYNTHETIC_RESPONSE_TIME.labels(
        check_type=check_type, 
        location=location
    ).set(duration)
    
    # Update failure metrics if failed
    if status == 'failed' and error_type:
        SYNTHETIC_FAILURES_TOTAL.labels(
            check_type=check_type, 
            location=location, 
            error_type=error_type
        ).inc()
    
    # Update in-memory metrics
    if minute_key not in metrics_store['synthetic_checks']:
        metrics_store['synthetic_checks'][minute_key] = {}
    
    key = f"{check_type}:{location}"
    if key not in metrics_store['synthetic_checks'][minute_key]:
        metrics_store['synthetic_checks'][minute_key][key] = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'total_duration': 0.0
        }
    
    metrics_store['synthetic_checks'][minute_key][key]['total'] += 1
    metrics_store['synthetic_checks'][minute_key][key]['total_duration'] += duration
    
    if status == 'success':
        metrics_store['synthetic_checks'][minute_key][key]['success'] += 1
    else:
        metrics_store['synthetic_checks'][minute_key][key]['failed'] += 1
    
    # Calculate and update availability
    total_checks = metrics_store['synthetic_checks'][minute_key][key]['total']
    success_checks = metrics_store['synthetic_checks'][minute_key][key]['success']
    availability = (success_checks / total_checks) * 100 if total_checks > 0 else 0
    
    SYNTHETIC_AVAILABILITY.labels(
        check_type=check_type, 
        location=location
    ).set(availability)
    
    # Keep only last 60 minutes of data
    cutoff_time = now - timedelta(minutes=60)
    for store_key in ['synthetic_checks', 'synthetic_failures', 'synthetic_response_times']:
        metrics_store[store_key] = {
            k: v for k, v in metrics_store[store_key].items()
            if datetime.strptime(k, '%Y-%m-%d %H:%M') > cutoff_time
        }


def get_synthetic_metrics_summary() -> Dict[str, Any]:
    """Get summary of synthetic monitoring metrics"""
    try:
        now = datetime.utcnow()
        last_5_minutes = now - timedelta(minutes=5)
        last_hour = now - timedelta(hours=1)
        
        # Calculate synthetic check metrics for last 5 minutes
        recent_checks = 0
        recent_success = 0
        recent_failed = 0
        recent_duration = 0.0
        
        for minute_key, checks in metrics_store['synthetic_checks'].items():
            minute_time = datetime.strptime(minute_key, '%Y-%m-%d %H:%M')
            if minute_time > last_5_minutes:
                for check_data in checks.values():
                    recent_checks += check_data['total']
                    recent_success += check_data['success']
                    recent_failed += check_data['failed']
                    recent_duration += check_data['total_duration']
        
        # Calculate hourly metrics
        hourly_checks = 0
        hourly_success = 0
        hourly_failed = 0
        
        for minute_key, checks in metrics_store['synthetic_checks'].items():
            minute_time = datetime.strptime(minute_key, '%Y-%m-%d %H:%M')
            if minute_time > last_hour:
                for check_data in checks.values():
                    hourly_checks += check_data['total']
                    hourly_success += check_data['success']
                    hourly_failed += check_data['failed']
        
        # Calculate averages and percentages
        avg_response_time = recent_duration / max(recent_checks, 1)
        success_rate_5min = (recent_success / max(recent_checks, 1)) * 100
        success_rate_hour = (hourly_success / max(hourly_checks, 1)) * 100
        
        return {
            'synthetic_checks_last_5_minutes': recent_checks,
            'synthetic_success_last_5_minutes': recent_success,
            'synthetic_failures_last_5_minutes': recent_failed,
            'synthetic_checks_last_hour': hourly_checks,
            'synthetic_success_last_hour': hourly_success,
            'synthetic_failures_last_hour': hourly_failed,
            'success_rate_5min_percent': round(success_rate_5min, 2),
            'success_rate_hour_percent': round(success_rate_hour, 2),
            'average_response_time_seconds': round(avg_response_time, 3),
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to generate synthetic metrics summary", error=str(e))
        return {
            'error': str(e),
            'last_updated': metrics_store['last_updated']
        }


def update_system_metrics():
    """Update system-level metrics"""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        CPU_USAGE.set(cpu_percent)
        
        # Memory usage
        memory = psutil.virtual_memory()
        MEMORY_USAGE.set(memory.percent)
        
        # Active connections (simplified)
        ACTIVE_CONNECTIONS.set(len(psutil.net_connections()))
        
        logger.debug(
            "System metrics updated",
            cpu_usage=cpu_percent,
            memory_usage=memory.percent
        )
        
    except Exception as e:
        logger.error("Failed to update system metrics", error=str(e))


def get_health_status() -> Dict[str, Any]:
    """Get comprehensive health status"""
    try:
        health_checks = {
            'database': check_database_health(),
            'memory': check_memory_health(),
            'disk': check_disk_health(),
            'cpu': check_cpu_health()
        }
        
        overall_status = 'healthy'
        for check_name, check_result in health_checks.items():
            if check_result['status'] != 'healthy':
                overall_status = 'unhealthy'
                break
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow(),
            'checks': health_checks
        }
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            'status': 'unhealthy',
            'timestamp': datetime.utcnow(),
            'error': str(e)
        }


def check_database_health() -> Dict[str, Any]:
    """Check database health"""
    try:
        from .database import check_db_connection
        is_healthy = check_db_connection()
        
        return {
            'status': 'healthy' if is_healthy else 'unhealthy',
            'message': 'Database connection successful' if is_healthy else 'Database connection failed'
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'Database health check failed: {str(e)}'
        }


def check_memory_health() -> Dict[str, Any]:
    """Check memory health"""
    try:
        memory = psutil.virtual_memory()
        usage_percent = memory.percent
        
        status = 'healthy'
        if usage_percent > 90:
            status = 'critical'
        elif usage_percent > 80:
            status = 'warning'
        
        return {
            'status': status,
            'usage_percent': usage_percent,
            'available_gb': memory.available / (1024**3),
            'total_gb': memory.total / (1024**3)
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'Memory health check failed: {str(e)}'
        }


def check_disk_health() -> Dict[str, Any]:
    """Check disk health"""
    try:
        disk = psutil.disk_usage('/')
        usage_percent = (disk.used / disk.total) * 100
        
        status = 'healthy'
        if usage_percent > 90:
            status = 'critical'
        elif usage_percent > 80:
            status = 'warning'
        
        return {
            'status': status,
            'usage_percent': usage_percent,
            'free_gb': disk.free / (1024**3),
            'total_gb': disk.total / (1024**3)
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'Disk health check failed: {str(e)}'
        }


def check_cpu_health() -> Dict[str, Any]:
    """Check CPU health"""
    try:
        cpu_percent = psutil.cpu_percent(interval=1)
        
        status = 'healthy'
        if cpu_percent > 90:
            status = 'critical'
        elif cpu_percent > 80:
            status = 'warning'
        
        return {
            'status': status,
            'usage_percent': cpu_percent,
            'core_count': psutil.cpu_count()
        }
    except Exception as e:
        return {
            'status': 'unhealthy',
            'message': f'CPU health check failed: {str(e)}'
        }


def get_metrics_summary() -> Dict[str, Any]:
    """Get summary of collected metrics"""
    try:
        now = datetime.utcnow()
        last_5_minutes = now - timedelta(minutes=5)
        
        # Calculate requests per minute for last 5 minutes
        recent_requests = 0
        for minute_key, endpoints in metrics_store['requests_per_minute'].items():
            minute_time = datetime.strptime(minute_key, '%Y-%m-%d %H:%M')
            if minute_time > last_5_minutes:
                for endpoint_data in endpoints.values():
                    recent_requests += endpoint_data['count']
        
        # Calculate error rate for last 5 minutes
        recent_errors = 0
        for minute_key, errors in metrics_store['error_rates'].items():
            minute_time = datetime.strptime(minute_key, '%Y-%m-%d %H:%M')
            if minute_time > last_5_minutes:
                recent_errors += sum(errors.values())
        
        error_rate = (recent_errors / max(recent_requests, 1)) * 100
        
        # Get synthetic metrics summary
        synthetic_summary = get_synthetic_metrics_summary()
        
        return {
            'requests_last_5_minutes': recent_requests,
            'errors_last_5_minutes': recent_errors,
            'error_rate_percent': round(error_rate, 2),
            'synthetic_monitoring': synthetic_summary,
            'system_metrics': {
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
            },
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to generate metrics summary", error=str(e))
        return {
            'error': str(e),
            'last_updated': metrics_store['last_updated']
        }


def get_prometheus_metrics() -> str:
    """Get Prometheus metrics"""
    try:
        update_system_metrics()
        return generate_latest()
    except Exception as e:
        logger.error("Failed to generate Prometheus metrics", error=str(e))
        return ""
