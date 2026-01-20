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

# In-memory metrics storage
metrics_store = {
    'requests_per_minute': {},
    'error_rates': {},
    'response_times': {},
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
        
        return {
            'requests_last_5_minutes': recent_requests,
            'errors_last_5_minutes': recent_errors,
            'error_rate_percent': round(error_rate, 2),
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
