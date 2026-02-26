"""
Backend service monitoring endpoints for 3-tier architecture
"""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
import structlog

from ...monitoring import (
    update_backend_metrics,
    BACKEND_API_REQUESTS,
    BACKEND_API_DURATION,
    BACKEND_DATABASE_QUERIES,
    BACKEND_DATABASE_DURATION,
    BACKEND_CACHE_OPERATIONS,
    BACKEND_SERVICE_DEPENDENCIES,
    metrics_store
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/backend", tags=["backend"])


class APIRequestEvent(BaseModel):
    service: str
    endpoint: str
    method: str
    status: str
    duration: float
    timestamp: Optional[datetime] = None


class DatabaseQueryEvent(BaseModel):
    service: str
    operation: str  # SELECT, INSERT, UPDATE, DELETE
    table: str
    duration: float
    rows_affected: Optional[int] = 0
    timestamp: Optional[datetime] = None


class CacheOperationEvent(BaseModel):
    service: str
    operation: str  # GET, SET, DELETE, HIT, MISS
    cache_key: Optional[str] = ""
    result: str  # HIT, MISS, SUCCESS, ERROR
    duration: Optional[float] = 0.0
    timestamp: Optional[datetime] = None


class ServiceDependencyEvent(BaseModel):
    service: str
    dependency: str
    operation: str
    status: str
    duration: float
    error_message: Optional[str] = ""
    timestamp: Optional[datetime] = None


class BackendMetricsResponse(BaseModel):
    services: Dict[str, Dict[str, Any]]
    database_performance: Dict[str, Dict[str, Any]]
    cache_performance: Dict[str, Dict[str, Any]]
    service_dependencies: Dict[str, Dict[str, Any]]
    last_updated: datetime


@router.post("/api-request")
async def track_api_request(event: APIRequestEvent):
    """Track backend API request metrics"""
    try:
        # Update metrics
        update_backend_metrics(
            service=event.service,
            endpoint=event.endpoint,
            method=event.method,
            status=event.status,
            duration=event.duration
        )
        
        logger.info(
            "API request tracked",
            service=event.service,
            endpoint=event.endpoint,
            method=event.method,
            status=event.status,
            duration=event.duration
        )
        
        return {"status": "success", "message": "API request tracked"}
        
    except Exception as e:
        logger.error("Failed to track API request", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track API request")


@router.post("/database-query")
async def track_database_query(event: DatabaseQueryEvent):
    """Track database query metrics"""
    try:
        # Update database query metrics
        BACKEND_DATABASE_QUERIES.labels(
            service=event.service,
            operation=event.operation,
            table=event.table
        ).inc()
        
        BACKEND_DATABASE_DURATION.labels(
            service=event.service,
            operation=event.operation,
            table=event.table
        ).observe(event.duration)
        
        # Store in memory for analysis
        if 'database_metrics' not in metrics_store['backend_metrics']:
            metrics_store['backend_metrics']['database_metrics'] = {}
        
        key = f"{event.service}:{event.table}:{event.operation}"
        if key not in metrics_store['backend_metrics']['database_metrics']:
            metrics_store['backend_metrics']['database_metrics'][key] = {
                'queries': 0,
                'total_duration': 0.0,
                'rows_affected': 0,
                'slow_queries': []
            }
        
        db_metrics = metrics_store['backend_metrics']['database_metrics'][key]
        db_metrics['queries'] += 1
        db_metrics['total_duration'] += event.duration
        db_metrics['rows_affected'] += event.rows_affected or 0
        
        # Track slow queries (> 1 second)
        if event.duration > 1.0:
            db_metrics['slow_queries'].append({
                'duration': event.duration,
                'timestamp': event.timestamp or datetime.utcnow(),
                'rows_affected': event.rows_affected
            })
        
        logger.info(
            "Database query tracked",
            service=event.service,
            operation=event.operation,
            table=event.table,
            duration=event.duration,
            rows_affected=event.rows_affected
        )
        
        return {"status": "success", "message": "Database query tracked"}
        
    except Exception as e:
        logger.error("Failed to track database query", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track database query")


@router.post("/cache-operation")
async def track_cache_operation(event: CacheOperationEvent):
    """Track cache operation metrics"""
    try:
        # Update cache operation metrics
        BACKEND_CACHE_OPERATIONS.labels(
            service=event.service,
            operation=event.operation,
            result=event.result
        ).inc()
        
        # Store in memory for analysis
        if 'cache_metrics' not in metrics_store['backend_metrics']:
            metrics_store['backend_metrics']['cache_metrics'] = {}
        
        key = f"{event.service}:{event.operation}"
        if key not in metrics_store['backend_metrics']['cache_metrics']:
            metrics_store['backend_metrics']['cache_metrics'][key] = {
                'operations': 0,
                'hits': 0,
                'misses': 0,
                'errors': 0,
                'total_duration': 0.0
            }
        
        cache_metrics = metrics_store['backend_metrics']['cache_metrics'][key]
        cache_metrics['operations'] += 1
        
        if event.result == 'HIT':
            cache_metrics['hits'] += 1
        elif event.result == 'MISS':
            cache_metrics['misses'] += 1
        elif event.result == 'ERROR':
            cache_metrics['errors'] += 1
        
        if event.duration:
            cache_metrics['total_duration'] += event.duration
        
        logger.info(
            "Cache operation tracked",
            service=event.service,
            operation=event.operation,
            result=event.result,
            cache_key=event.cache_key
        )
        
        return {"status": "success", "message": "Cache operation tracked"}
        
    except Exception as e:
        logger.error("Failed to track cache operation", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track cache operation")


@router.post("/service-dependency")
async def track_service_dependency(event: ServiceDependencyEvent):
    """Track service dependency calls"""
    try:
        # Update service dependency metrics
        BACKEND_SERVICE_DEPENDENCIES.labels(
            service=event.service,
            dependency=event.dependency,
            operation=event.operation,
            status=event.status
        ).inc()
        
        # Store in memory for analysis
        if 'dependency_metrics' not in metrics_store['backend_metrics']:
            metrics_store['backend_metrics']['dependency_metrics'] = {}
        
        key = f"{event.service}->{event.dependency}"
        if key not in metrics_store['backend_metrics']['dependency_metrics']:
            metrics_store['backend_metrics']['dependency_metrics'][key] = {
                'calls': 0,
                'successes': 0,
                'failures': 0,
                'total_duration': 0.0,
                'errors': []
            }
        
        dep_metrics = metrics_store['backend_metrics']['dependency_metrics'][key]
        dep_metrics['calls'] += 1
        dep_metrics['total_duration'] += event.duration
        
        if event.status.startswith('2'):
            dep_metrics['successes'] += 1
        else:
            dep_metrics['failures'] += 1
            if event.error_message:
                dep_metrics['errors'].append({
                    'error': event.error_message,
                    'timestamp': event.timestamp or datetime.utcnow(),
                    'duration': event.duration
                })
        
        logger.info(
            "Service dependency tracked",
            service=event.service,
            dependency=event.dependency,
            operation=event.operation,
            status=event.status,
            duration=event.duration
        )
        
        return {"status": "success", "message": "Service dependency tracked"}
        
    except Exception as e:
        logger.error("Failed to track service dependency", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track service dependency")


@router.get("/metrics", response_model=BackendMetricsResponse)
async def get_backend_metrics(
    service: Optional[str] = Query(None, description="Filter by specific service"),
    hours: int = Query(24, description="Hours of data to retrieve")
):
    """Get comprehensive backend metrics"""
    try:
        backend_data = metrics_store.get('backend_metrics', {})
        
        # Service metrics
        services = {}
        for service_name, data in backend_data.items():
            if service_name in ['database_metrics', 'cache_metrics', 'dependency_metrics']:
                continue
            if service and service_name != service:
                continue
                
            response_times = data.get('response_times', [])
            services[service_name] = {
                'requests': data.get('requests', 0),
                'error_count': data.get('error_count', 0),
                'average_response_time': sum(response_times) / len(response_times) if response_times else 0,
                'endpoints': data.get('endpoints', {}),
                'error_rate': (data.get('error_count', 0) / max(data.get('requests', 1), 1)) * 100
            }
        
        # Database performance
        database_performance = {}
        db_metrics = backend_data.get('database_metrics', {})
        for key, data in db_metrics.items():
            parts = key.split(':')
            service_name = parts[0] if parts else 'unknown'
            
            if service and service_name != service:
                continue
                
            database_performance[key] = {
                'queries': data.get('queries', 0),
                'total_duration': data.get('total_duration', 0),
                'average_duration': data.get('total_duration', 0) / max(data.get('queries', 1), 1),
                'rows_affected': data.get('rows_affected', 0),
                'slow_queries': data.get('slow_queries', [])[-10:]  # Last 10 slow queries
            }
        
        # Cache performance
        cache_performance = {}
        cache_metrics = backend_data.get('cache_metrics', {})
        for key, data in cache_metrics.items():
            parts = key.split(':')
            service_name = parts[0] if parts else 'unknown'
            
            if service and service_name != service:
                continue
                
            total_ops = data.get('operations', 0)
            hits = data.get('hits', 0)
            misses = data.get('misses', 0)
            
            cache_performance[key] = {
                'operations': total_ops,
                'hits': hits,
                'misses': misses,
                'errors': data.get('errors', 0),
                'hit_rate': (hits / max(total_ops, 1)) * 100,
                'average_duration': data.get('total_duration', 0) / max(total_ops, 1)
            }
        
        # Service dependencies
        service_dependencies = {}
        dep_metrics = backend_data.get('dependency_metrics', {})
        for key, data in dep_metrics.items():
            parts = key.split('->')
            service_name = parts[0] if parts else 'unknown'
            
            if service and service_name != service:
                continue
                
            total_calls = data.get('calls', 0)
            service_dependencies[key] = {
                'calls': total_calls,
                'successes': data.get('successes', 0),
                'failures': data.get('failures', 0),
                'success_rate': (data.get('successes', 0) / max(total_calls, 1)) * 100,
                'average_duration': data.get('total_duration', 0) / max(total_calls, 1),
                'recent_errors': data.get('errors', [])[-5:]  # Last 5 errors
            }
        
        return BackendMetricsResponse(
            services=services,
            database_performance=database_performance,
            cache_performance=cache_performance,
            service_dependencies=service_dependencies,
            last_updated=metrics_store['last_updated']
        )
        
    except Exception as e:
        logger.error("Failed to get backend metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve backend metrics")


@router.get("/performance-summary")
async def get_performance_summary(
    service: Optional[str] = Query(None, description="Filter by specific service")
):
    """Get performance summary for backend services"""
    try:
        backend_data = metrics_store.get('backend_metrics', {})
        
        total_requests = 0
        total_errors = 0
        total_response_time = 0.0
        response_times_count = 0
        
        for service_name, data in backend_data.items():
            if service_name in ['database_metrics', 'cache_metrics', 'dependency_metrics']:
                continue
            if service and service_name != service:
                continue
                
            total_requests += data.get('requests', 0)
            total_errors += data.get('error_count', 0)
            
            response_times = data.get('response_times', [])
            total_response_time += sum(response_times)
            response_times_count += len(response_times)
        
        average_response_time = total_response_time / max(response_times_count, 1)
        overall_error_rate = (total_errors / max(total_requests, 1)) * 100
        
        # Database summary
        db_summary = {'total_queries': 0, 'slow_queries': 0, 'avg_duration': 0}
        db_metrics = backend_data.get('database_metrics', {})
        
        for data in db_metrics.values():
            db_summary['total_queries'] += data.get('queries', 0)
            db_summary['slow_queries'] += len(data.get('slow_queries', []))
            db_summary['avg_duration'] += data.get('total_duration', 0)
        
        if db_summary['total_queries'] > 0:
            db_summary['avg_duration'] /= db_summary['total_queries']
        
        # Cache summary
        cache_summary = {'total_operations': 0, 'hit_rate': 0}
        cache_metrics = backend_data.get('cache_metrics', {})
        
        total_cache_ops = 0
        total_cache_hits = 0
        
        for data in cache_metrics.values():
            ops = data.get('operations', 0)
            hits = data.get('hits', 0)
            total_cache_ops += ops
            total_cache_hits += hits
        
        if total_cache_ops > 0:
            cache_summary['total_operations'] = total_cache_ops
            cache_summary['hit_rate'] = (total_cache_hits / total_cache_ops) * 100
        
        return {
            'total_requests': total_requests,
            'total_errors': total_errors,
            'error_rate_percent': round(overall_error_rate, 2),
            'average_response_time_seconds': round(average_response_time, 3),
            'database': db_summary,
            'cache': cache_summary,
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get performance summary", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve performance summary")


@router.get("/slow-queries")
async def get_slow_queries(
    service: Optional[str] = Query(None, description="Filter by specific service"),
    limit: int = Query(50, description="Maximum number of slow queries to return")
):
    """Get slow database queries"""
    try:
        backend_data = metrics_store.get('backend_metrics', {})
        db_metrics = backend_data.get('database_metrics', {})
        
        all_slow_queries = []
        
        for key, data in db_metrics.items():
            parts = key.split(':')
            service_name = parts[0] if parts else 'unknown'
            table_name = parts[1] if len(parts) > 1 else 'unknown'
            operation = parts[2] if len(parts) > 2 else 'unknown'
            
            if service and service_name != service:
                continue
                
            slow_queries = data.get('slow_queries', [])
            for query in slow_queries:
                all_slow_queries.append({
                    'service': service_name,
                    'table': table_name,
                    'operation': operation,
                    'duration': query['duration'],
                    'timestamp': query['timestamp'],
                    'rows_affected': query.get('rows_affected', 0)
                })
        
        # Sort by duration (slowest first) and limit
        all_slow_queries.sort(key=lambda x: x['duration'], reverse=True)
        
        return {
            'slow_queries': all_slow_queries[:limit],
            'total_count': len(all_slow_queries),
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get slow queries", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve slow queries")
