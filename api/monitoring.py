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

# Frontend/Client-side metrics
FRONTEND_PAGE_VIEWS = Counter(
    'frontend_page_views_total',
    'Total page views',
    ['page', 'user_agent', 'referrer']
)

FRONTEND_PAGE_LOAD_TIME = Histogram(
    'frontend_page_load_duration_seconds',
    'Page load duration in seconds',
    ['page', 'browser', 'device_type']
)

FRONTEND_CORE_WEB_VITALS = Histogram(
    'frontend_core_web_vitals_seconds',
    'Core Web Vitals metrics',
    ['metric_type', 'page', 'device_type']
)

FRONTEND_USER_INTERACTIONS = Counter(
    'frontend_user_interactions_total',
    'Total user interactions',
    ['interaction_type', 'element', 'page']
)

FRONTEND_JAVASCRIPT_ERRORS = Counter(
    'frontend_javascript_errors_total',
    'JavaScript errors',
    ['error_type', 'page', 'browser']
)

# Backend Service metrics
BACKEND_API_REQUESTS = Counter(
    'backend_api_requests_total',
    'Total backend API requests',
    ['service', 'endpoint', 'method', 'status']
)

BACKEND_API_DURATION = Histogram(
    'backend_api_duration_seconds',
    'Backend API duration in seconds',
    ['service', 'endpoint', 'method']
)

BACKEND_DATABASE_QUERIES = Counter(
    'backend_database_queries_total',
    'Total database queries',
    ['service', 'operation', 'table']
)

BACKEND_DATABASE_DURATION = Histogram(
    'backend_database_duration_seconds',
    'Database query duration in seconds',
    ['service', 'operation', 'table']
)

BACKEND_CACHE_OPERATIONS = Counter(
    'backend_cache_operations_total',
    'Cache operations',
    ['service', 'operation', 'result']
)

BACKEND_SERVICE_DEPENDENCIES = Counter(
    'backend_service_dependencies_total',
    'Service dependency calls',
    ['service', 'dependency', 'operation', 'status']
)

# Infrastructure/Container metrics
CONTAINER_CPU_USAGE = Gauge(
    'container_cpu_usage_percent',
    'Container CPU usage percentage',
    ['container_name', 'pod_name', 'namespace']
)

CONTAINER_MEMORY_USAGE = Gauge(
    'container_memory_usage_bytes',
    'Container memory usage in bytes',
    ['container_name', 'pod_name', 'namespace']
)

CONTAINER_NETWORK_IO = Counter(
    'container_network_io_bytes_total',
    'Container network I/O in bytes',
    ['container_name', 'pod_name', 'namespace', 'direction']
)

POD_RESTART_COUNT = Counter(
    'pod_restart_count_total',
    'Pod restart count',
    ['pod_name', 'namespace', 'container_name']
)

NODE_RESOURCE_USAGE = Gauge(
    'node_resource_usage_percent',
    'Node resource usage percentage',
    ['node_name', 'resource_type']
)

# Microservices metrics
SERVICE_MESH_REQUESTS = Counter(
    'service_mesh_requests_total',
    'Service mesh requests',
    ['source_service', 'destination_service', 'method', 'status']
)

SERVICE_MESH_DURATION = Histogram(
    'service_mesh_duration_seconds',
    'Service mesh request duration',
    ['source_service', 'destination_service', 'method']
)

DISTRIBUTED_TRACES = Counter(
    'distributed_traces_total',
    'Distributed traces',
    ['trace_id', 'service', 'operation', 'status']
)

SERVICE_DEPENDENCY_LATENCY = Histogram(
    'service_dependency_latency_seconds',
    'Service dependency latency',
    ['service', 'dependency', 'operation']
)

CIRCUIT_BREAKER_STATE = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half-open)',
    ['service', 'dependency']
)

# End-to-End Transaction metrics
TRANSACTION_DURATION = Histogram(
    'transaction_duration_seconds',
    'End-to-end transaction duration',
    ['transaction_type', 'user_id', 'service_flow']
)

TRANSACTION_SUCCESS_RATE = Gauge(
    'transaction_success_rate_percent',
    'Transaction success rate percentage',
    ['transaction_type', 'service_flow']
)

USER_JOURNEY_STEPS = Counter(
    'user_journey_steps_total',
    'User journey step completions',
    ['journey_type', 'step_name', 'user_segment']
)

BUSINESS_METRICS = Counter(
    'business_metrics_total',
    'Business metrics',
    ['metric_name', 'product', 'user_segment']
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
    'frontend_metrics': {},
    'backend_metrics': {},
    'container_metrics': {},
    'microservices_metrics': {},
    'transaction_metrics': {},
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


def update_frontend_metrics(page: str, load_time: float, user_agent: str, referrer: str, browser: str, device_type: str):
    """Update frontend metrics"""
    try:
        # Update Prometheus metrics
        FRONTEND_PAGE_VIEWS.labels(page=page, user_agent=user_agent, referrer=referrer).inc()
        FRONTEND_PAGE_LOAD_TIME.labels(page=page, browser=browser, device_type=device_type).observe(load_time)
        
        # Update in-memory metrics
        if page not in metrics_store['frontend_metrics']:
            metrics_store['frontend_metrics'][page] = {
                'page_views': 0,
                'load_times': [],
                'browsers': {},
                'device_types': {}
            }
        
        metrics_store['frontend_metrics'][page]['page_views'] += 1
        metrics_store['frontend_metrics'][page]['load_times'].append(load_time)
        
        if browser not in metrics_store['frontend_metrics'][page]['browsers']:
            metrics_store['frontend_metrics'][page]['browsers'][browser] = 0
        metrics_store['frontend_metrics'][page]['browsers'][browser] += 1
        
        if device_type not in metrics_store['frontend_metrics'][page]['device_types']:
            metrics_store['frontend_metrics'][page]['device_types'][device_type] = 0
        metrics_store['frontend_metrics'][page]['device_types'][device_type] += 1
        
        metrics_store['last_updated'] = datetime.utcnow()
        
    except Exception as e:
        logger.error("Failed to update frontend metrics", error=str(e))


def update_backend_metrics(service: str, endpoint: str, method: str, status: str, duration: float):
    """Update backend service metrics"""
    try:
        # Update Prometheus metrics
        BACKEND_API_REQUESTS.labels(service=service, endpoint=endpoint, method=method, status=status).inc()
        BACKEND_API_DURATION.labels(service=service, endpoint=endpoint, method=method).observe(duration)
        
        # Update in-memory metrics
        if service not in metrics_store['backend_metrics']:
            metrics_store['backend_metrics'][service] = {
                'requests': 0,
                'response_times': [],
                'endpoints': {},
                'error_count': 0
            }
        
        metrics_store['backend_metrics'][service]['requests'] += 1
        metrics_store['backend_metrics'][service]['response_times'].append(duration)
        
        if endpoint not in metrics_store['backend_metrics'][service]['endpoints']:
            metrics_store['backend_metrics'][service]['endpoints'][endpoint] = {
                'count': 0,
                'total_duration': 0
            }
        
        metrics_store['backend_metrics'][service]['endpoints'][endpoint]['count'] += 1
        metrics_store['backend_metrics'][service]['endpoints'][endpoint]['total_duration'] += duration
        
        if status.startswith('4') or status.startswith('5'):
            metrics_store['backend_metrics'][service]['error_count'] += 1
        
        metrics_store['last_updated'] = datetime.utcnow()
        
    except Exception as e:
        logger.error("Failed to update backend metrics", error=str(e))


def update_container_metrics(container_name: str, pod_name: str, namespace: str, cpu_usage: float, memory_usage: float, network_io: dict):
    """Update container metrics"""
    try:
        # Update Prometheus metrics
        CONTAINER_CPU_USAGE.labels(container_name=container_name, pod_name=pod_name, namespace=namespace).set(cpu_usage)
        CONTAINER_MEMORY_USAGE.labels(container_name=container_name, pod_name=pod_name, namespace=namespace).set(memory_usage)
        
        # Update network I/O
        for direction, bytes_count in network_io.items():
            CONTAINER_NETWORK_IO.labels(
                container_name=container_name, 
                pod_name=pod_name, 
                namespace=namespace, 
                direction=direction
            ).inc(bytes_count)
        
        # Update in-memory metrics
        key = f"{namespace}/{pod_name}/{container_name}"
        if key not in metrics_store['container_metrics']:
            metrics_store['container_metrics'][key] = {
                'cpu_usage': [],
                'memory_usage': [],
                'network_io': {'in': 0, 'out': 0},
                'last_updated': datetime.utcnow()
            }
        
        metrics_store['container_metrics'][key]['cpu_usage'].append(cpu_usage)
        metrics_store['container_metrics'][key]['memory_usage'].append(memory_usage)
        metrics_store['container_metrics'][key]['network_io']['in'] += network_io.get('in', 0)
        metrics_store['container_metrics'][key]['network_io']['out'] += network_io.get('out', 0)
        metrics_store['container_metrics'][key]['last_updated'] = datetime.utcnow()
        
        metrics_store['last_updated'] = datetime.utcnow()
        
    except Exception as e:
        logger.error("Failed to update container metrics", error=str(e))


def update_microservices_metrics(source_service: str, destination_service: str, method: str, status: str, duration: float):
    """Update microservices metrics"""
    try:
        # Update Prometheus metrics
        SERVICE_MESH_REQUESTS.labels(
            source_service=source_service, 
            destination_service=destination_service, 
            method=method, 
            status=status
        ).inc()
        
        SERVICE_MESH_DURATION.labels(
            source_service=source_service, 
            destination_service=destination_service, 
            method=method
        ).observe(duration)
        
        # Update in-memory metrics
        key = f"{source_service}->{destination_service}"
        if key not in metrics_store['microservices_metrics']:
            metrics_store['microservices_metrics'][key] = {
                'requests': 0,
                'response_times': [],
                'error_count': 0,
                'methods': {}
            }
        
        metrics_store['microservices_metrics'][key]['requests'] += 1
        metrics_store['microservices_metrics'][key]['response_times'].append(duration)
        
        if method not in metrics_store['microservices_metrics'][key]['methods']:
            metrics_store['microservices_metrics'][key]['methods'][method] = 0
        metrics_store['microservices_metrics'][key]['methods'][method] += 1
        
        if status.startswith('4') or status.startswith('5'):
            metrics_store['microservices_metrics'][key]['error_count'] += 1
        
        metrics_store['last_updated'] = datetime.utcnow()
        
    except Exception as e:
        logger.error("Failed to update microservices metrics", error=str(e))


def update_transaction_metrics(transaction_type: str, user_id: str, service_flow: str, duration: float, status: str):
    """Update end-to-end transaction metrics"""
    try:
        # Update Prometheus metrics
        TRANSACTION_DURATION.labels(
            transaction_type=transaction_type, 
            user_id=user_id, 
            service_flow=service_flow
        ).observe(duration)
        
        # Update in-memory metrics
        if transaction_type not in metrics_store['transaction_metrics']:
            metrics_store['transaction_metrics'][transaction_type] = {
                'transactions': 0,
                'durations': [],
                'success_count': 0,
                'failure_count': 0,
                'service_flows': {}
            }
        
        metrics_store['transaction_metrics'][transaction_type]['transactions'] += 1
        metrics_store['transaction_metrics'][transaction_type]['durations'].append(duration)
        
        if service_flow not in metrics_store['transaction_metrics'][transaction_type]['service_flows']:
            metrics_store['transaction_metrics'][transaction_type]['service_flows'][service_flow] = 0
        metrics_store['transaction_metrics'][transaction_type]['service_flows'][service_flow] += 1
        
        if status == 'success':
            metrics_store['transaction_metrics'][transaction_type]['success_count'] += 1
        else:
            metrics_store['transaction_metrics'][transaction_type]['failure_count'] += 1
        
        metrics_store['last_updated'] = datetime.utcnow()
        
    except Exception as e:
        logger.error("Failed to update transaction metrics", error=str(e))


def get_system_metrics() -> Dict[str, Any]:
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
