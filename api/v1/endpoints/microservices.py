"""
Microservices monitoring endpoints for 3-tier architecture (service mesh, distributed tracing)
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
import structlog

from ...monitoring import (
    update_microservices_metrics,
    SERVICE_MESH_REQUESTS,
    SERVICE_MESH_DURATION,
    DISTRIBUTED_TRACES,
    SERVICE_DEPENDENCY_LATENCY,
    CIRCUIT_BREAKER_STATE,
    metrics_store
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/microservices", tags=["microservices"])


class ServiceMeshRequestEvent(BaseModel):
    source_service: str
    destination_service: str
    method: str
    endpoint: str
    status: str
    duration: float
    request_id: Optional[str] = ""
    timestamp: Optional[datetime] = None


class DistributedTraceEvent(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = ""
    service: str
    operation: str
    start_time: datetime
    end_time: datetime
    status: str
    tags: Optional[Dict[str, str]] = {}
    logs: Optional[List[Dict[str, Any]]] = []


class ServiceDependencyLatencyEvent(BaseModel):
    service: str
    dependency: str
    operation: str
    latency: float
    success: bool
    error_type: Optional[str] = ""
    timestamp: Optional[datetime] = None


class CircuitBreakerStateEvent(BaseModel):
    service: str
    dependency: str
    state: str  # CLOSED, OPEN, HALF_OPEN
    failure_count: int
    success_count: int
    last_failure_time: Optional[datetime] = None
    timestamp: Optional[datetime] = None


class MicroservicesMetricsResponse(BaseModel):
    service_mesh: Dict[str, Dict[str, Any]]
    distributed_traces: Dict[str, Dict[str, Any]]
    service_dependencies: Dict[str, Dict[str, Any]]
    circuit_breakers: Dict[str, Dict[str, Any]]
    last_updated: datetime


@router.post("/service-mesh-request")
async def track_service_mesh_request(event: ServiceMeshRequestEvent):
    """Track service mesh request metrics"""
    try:
        # Update service mesh metrics
        update_microservices_metrics(
            source_service=event.source_service,
            destination_service=event.destination_service,
            method=event.method,
            status=event.status,
            duration=event.duration
        )
        
        logger.info(
            "Service mesh request tracked",
            source=event.source_service,
            destination=event.destination_service,
            method=event.method,
            status=event.status,
            duration=event.duration,
            request_id=event.request_id
        )
        
        return {"status": "success", "message": "Service mesh request tracked"}
        
    except Exception as e:
        logger.error("Failed to track service mesh request", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track service mesh request")


@router.post("/distributed-trace")
async def track_distributed_trace(event: DistributedTraceEvent):
    """Track distributed trace spans"""
    try:
        # Update distributed trace metrics
        DISTRIBUTED_TRACES.labels(
            trace_id=event.trace_id,
            service=event.service,
            operation=event.operation,
            status=event.status
        ).inc()
        
        # Store trace data for analysis
        if 'distributed_traces' not in metrics_store['microservices_metrics']:
            metrics_store['microservices_metrics']['distributed_traces'] = {}
        
        if event.trace_id not in metrics_store['microservices_metrics']['distributed_traces']:
            metrics_store['microservices_metrics']['distributed_traces'][event.trace_id] = {
                'spans': [],
                'services': set(),
                'operations': set(),
                'start_time': event.start_time,
                'end_time': event.end_time,
                'total_duration': 0,
                'status': event.status
            }
        
        trace_data = metrics_store['microservices_metrics']['distributed_traces'][event.trace_id]
        
        # Calculate span duration
        span_duration = (event.end_time - event.start_time).total_seconds()
        
        span_data = {
            'span_id': event.span_id,
            'parent_span_id': event.parent_span_id,
            'service': event.service,
            'operation': event.operation,
            'start_time': event.start_time,
            'end_time': event.end_time,
            'duration': span_duration,
            'status': event.status,
            'tags': event.tags or {},
            'logs': event.logs or []
        }
        
        trace_data['spans'].append(span_data)
        trace_data['services'].add(event.service)
        trace_data['operations'].add(event.operation)
        
        # Update trace timing
        if event.start_time < trace_data['start_time']:
            trace_data['start_time'] = event.start_time
        if event.end_time > trace_data['end_time']:
            trace_data['end_time'] = event.end_time
        
        trace_data['total_duration'] = (trace_data['end_time'] - trace_data['start_time']).total_seconds()
        
        # Update trace status if any span failed
        if event.status != 'success':
            trace_data['status'] = 'failed'
        
        logger.info(
            "Distributed trace tracked",
            trace_id=event.trace_id,
            span_id=event.span_id,
            service=event.service,
            operation=event.operation,
            duration=span_duration,
            status=event.status
        )
        
        return {"status": "success", "message": "Distributed trace tracked"}
        
    except Exception as e:
        logger.error("Failed to track distributed trace", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track distributed trace")


@router.post("/service-dependency-latency")
async def track_service_dependency_latency(event: ServiceDependencyLatencyEvent):
    """Track service dependency latency metrics"""
    try:
        # Update service dependency latency metrics
        SERVICE_DEPENDENCY_LATENCY.labels(
            service=event.service,
            dependency=event.dependency,
            operation=event.operation
        ).observe(event.latency)
        
        # Store in memory for analysis
        if 'dependency_latency' not in metrics_store['microservices_metrics']:
            metrics_store['microservices_metrics']['dependency_latency'] = {}
        
        key = f"{event.service}->{event.dependency}"
        if key not in metrics_store['microservices_metrics']['dependency_latency']:
            metrics_store['microservices_metrics']['dependency_latency'][key] = {
                'latencies': [],
                'success_count': 0,
                'failure_count': 0,
                'operations': {}
            }
        
        dep_data = metrics_store['microservices_metrics']['dependency_latency'][key]
        dep_data['latencies'].append(event.latency)
        
        if event.success:
            dep_data['success_count'] += 1
        else:
            dep_data['failure_count'] += 1
        
        if event.operation not in dep_data['operations']:
            dep_data['operations'][event.operation] = {
                'latencies': [],
                'success_count': 0,
                'failure_count': 0
            }
        
        op_data = dep_data['operations'][event.operation]
        op_data['latencies'].append(event.latency)
        
        if event.success:
            op_data['success_count'] += 1
        else:
            op_data['failure_count'] += 1
        
        logger.info(
            "Service dependency latency tracked",
            service=event.service,
            dependency=event.dependency,
            operation=event.operation,
            latency=event.latency,
            success=event.success
        )
        
        return {"status": "success", "message": "Service dependency latency tracked"}
        
    except Exception as e:
        logger.error("Failed to track service dependency latency", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track service dependency latency")


@router.post("/circuit-breaker-state")
async def track_circuit_breaker_state(event: CircuitBreakerStateEvent):
    """Track circuit breaker state changes"""
    try:
        # Convert state to numeric value for Prometheus
        state_map = {'CLOSED': 0, 'OPEN': 1, 'HALF_OPEN': 2}
        state_value = state_map.get(event.state.upper(), 0)
        
        # Update circuit breaker state metrics
        CIRCUIT_BREAKER_STATE.labels(
            service=event.service,
            dependency=event.dependency
        ).set(state_value)
        
        # Store in memory for analysis
        if 'circuit_breakers' not in metrics_store['microservices_metrics']:
            metrics_store['microservices_metrics']['circuit_breakers'] = {}
        
        key = f"{event.service}->{event.dependency}"
        if key not in metrics_store['microservices_metrics']['circuit_breakers']:
            metrics_store['microservices_metrics']['circuit_breakers'][key] = {
                'current_state': event.state,
                'state_history': [],
                'failure_count': 0,
                'success_count': 0,
                'total_state_changes': 0
            }
        
        cb_data = metrics_store['microservices_metrics']['circuit_breakers'][key]
        
        # Track state changes
        if cb_data['current_state'] != event.state:
            cb_data['total_state_changes'] += 1
            cb_data['state_history'].append({
                'from_state': cb_data['current_state'],
                'to_state': event.state,
                'timestamp': event.timestamp or datetime.utcnow(),
                'failure_count': event.failure_count,
                'success_count': event.success_count
            })
        
        cb_data['current_state'] = event.state
        cb_data['failure_count'] = event.failure_count
        cb_data['success_count'] = event.success_count
        
        logger.info(
            "Circuit breaker state tracked",
            service=event.service,
            dependency=event.dependency,
            state=event.state,
            failure_count=event.failure_count,
            success_count=event.success_count
        )
        
        return {"status": "success", "message": "Circuit breaker state tracked"}
        
    except Exception as e:
        logger.error("Failed to track circuit breaker state", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track circuit breaker state")


@router.get("/metrics", response_model=MicroservicesMetricsResponse)
async def get_microservices_metrics(
    service: Optional[str] = Query(None, description="Filter by specific service"),
    hours: int = Query(24, description="Hours of data to retrieve")
):
    """Get comprehensive microservices metrics"""
    try:
        microservices_data = metrics_store.get('microservices_metrics', {})
        
        # Service mesh metrics
        service_mesh = {}
        for key, data in microservices_data.items():
            if key in ['distributed_traces', 'dependency_latency', 'circuit_breakers']:
                continue
                
            parts = key.split('->')
            if len(parts) >= 2:
                source = parts[0]
                destination = parts[1]
                
                if service and (source != service and destination != service):
                    continue
                
                response_times = data.get('response_times', [])
                service_mesh[key] = {
                    'source_service': source,
                    'destination_service': destination,
                    'requests': data.get('requests', 0),
                    'error_count': data.get('error_count', 0),
                    'average_response_time': sum(response_times) / len(response_times) if response_times else 0,
                    'error_rate': (data.get('error_count', 0) / max(data.get('requests', 1), 1)) * 100,
                    'methods': data.get('methods', {})
                }
        
        # Distributed traces
        distributed_traces = {}
        traces_data = microservices_data.get('distributed_traces', {})
        
        for trace_id, trace_data in traces_data.items():
            if service and service not in trace_data['services']:
                continue
            
            spans = trace_data.get('spans', [])
            services = list(trace_data.get('services', set()))
            operations = list(trace_data.get('operations', set()))
            
            distributed_traces[trace_id] = {
                'span_count': len(spans),
                'services': services,
                'operations': operations,
                'total_duration': trace_data.get('total_duration', 0),
                'status': trace_data.get('status', 'unknown'),
                'start_time': trace_data.get('start_time'),
                'end_time': trace_data.get('end_time')
            }
        
        # Service dependencies
        service_dependencies = {}
        dep_latency = microservices_data.get('dependency_latency', {})
        
        for key, data in dep_latency.items():
            parts = key.split('->')
            if len(parts) >= 2:
                source = parts[0]
                dependency = parts[1]
                
                if service and source != service:
                    continue
                
                latencies = data.get('latencies', [])
                total_calls = data.get('success_count', 0) + data.get('failure_count', 0)
                
                service_dependencies[key] = {
                    'service': source,
                    'dependency': dependency,
                    'total_calls': total_calls,
                    'success_count': data.get('success_count', 0),
                    'failure_count': data.get('failure_count', 0),
                    'success_rate': (data.get('success_count', 0) / max(total_calls, 1)) * 100,
                    'average_latency': sum(latencies) / len(latencies) if latencies else 0,
                    'operations': data.get('operations', {})
                }
        
        # Circuit breakers
        circuit_breakers = {}
        cb_data = microservices_data.get('circuit_breakers', {})
        
        for key, data in cb_data.items():
            parts = key.split('->')
            if len(parts) >= 2:
                service_name = parts[0]
                dependency = parts[1]
                
                if service and service_name != service:
                    continue
                
                circuit_breakers[key] = {
                    'service': service_name,
                    'dependency': dependency,
                    'current_state': data.get('current_state', 'UNKNOWN'),
                    'failure_count': data.get('failure_count', 0),
                    'success_count': data.get('success_count', 0),
                    'total_state_changes': data.get('total_state_changes', 0),
                    'recent_state_changes': data.get('state_history', [])[-10:]  # Last 10 changes
                }
        
        return MicroservicesMetricsResponse(
            service_mesh=service_mesh,
            distributed_traces=distributed_traces,
            service_dependencies=service_dependencies,
            circuit_breakers=circuit_breakers,
            last_updated=metrics_store['last_updated']
        )
        
    except Exception as e:
        logger.error("Failed to get microservices metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve microservices metrics")


@router.get("/service-mesh-analysis")
async def get_service_mesh_analysis(
    hours: int = Query(24, description="Hours of data to analyze")
):
    """Get service mesh performance analysis"""
    try:
        microservices_data = metrics_store.get('microservices_metrics', {})
        
        # Analyze service mesh performance
        mesh_analysis = {
            'total_requests': 0,
            'total_errors': 0,
            'average_response_time': 0,
            'top_slow_services': [],
            'top_error_prone_services': [],
            'service_dependencies': {}
        }
        
        total_response_time = 0.0
        response_time_count = 0
        
        for key, data in microservices_data.items():
            if key in ['distributed_traces', 'dependency_latency', 'circuit_breakers']:
                continue
                
            parts = key.split('->')
            if len(parts) >= 2:
                source = parts[0]
                destination = parts[1]
                
                requests = data.get('requests', 0)
                errors = data.get('error_count', 0)
                response_times = data.get('response_times', [])
                
                mesh_analysis['total_requests'] += requests
                mesh_analysis['total_errors'] += errors
                
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
                    total_response_time += avg_response_time
                    response_time_count += 1
                    
                    mesh_analysis['top_slow_services'].append({
                        'source': source,
                        'destination': destination,
                        'average_response_time': avg_response_time,
                        'requests': requests
                    })
                
                if requests > 0:
                    error_rate = (errors / requests) * 100
                    mesh_analysis['top_error_prone_services'].append({
                        'source': source,
                        'destination': destination,
                        'error_rate': error_rate,
                        'requests': requests,
                        'errors': errors
                    })
                
                # Build dependency graph
                if source not in mesh_analysis['service_dependencies']:
                    mesh_analysis['service_dependencies'][source] = {'depends_on': [], 'called_by': []}
                if destination not in mesh_analysis['service_dependencies']:
                    mesh_analysis['service_dependencies'][destination] = {'depends_on': [], 'called_by': []}
                
                mesh_analysis['service_dependencies'][source]['depends_on'].append(destination)
                mesh_analysis['service_dependencies'][destination]['called_by'].append(source)
        
        # Calculate averages
        if response_time_count > 0:
            mesh_analysis['average_response_time'] = total_response_time / response_time_count
        
        # Sort and limit results
        mesh_analysis['top_slow_services'].sort(key=lambda x: x['average_response_time'], reverse=True)
        mesh_analysis['top_error_prone_services'].sort(key=lambda x: x['error_rate'], reverse=True)
        
        mesh_analysis['top_slow_services'] = mesh_analysis['top_slow_services'][:10]
        mesh_analysis['top_error_prone_services'] = mesh_analysis['top_error_prone_services'][:10]
        
        return {
            'mesh_analysis': mesh_analysis,
            'analysis_period_hours': hours,
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get service mesh analysis", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve service mesh analysis")


@router.get("/distributed-traces")
async def get_distributed_traces(
    trace_id: Optional[str] = Query(None, description="Filter by specific trace ID"),
    service: Optional[str] = Query(None, description="Filter by service"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, description="Maximum number of traces to return")
):
    """Get distributed traces with filtering options"""
    try:
        microservices_data = metrics_store.get('microservices_metrics', {})
        traces_data = microservices_data.get('distributed_traces', {})
        
        filtered_traces = {}
        
        for trace_id_key, trace_data in traces_data.items():
            if trace_id and trace_id_key != trace_id:
                continue
            
            if service and service not in trace_data.get('services', set()):
                continue
            
            if status and trace_data.get('status') != status:
                continue
            
            filtered_traces[trace_id_key] = {
                'span_count': len(trace_data.get('spans', [])),
                'services': list(trace_data.get('services', set())),
                'operations': list(trace_data.get('operations', set())),
                'total_duration': trace_data.get('total_duration', 0),
                'status': trace_data.get('status', 'unknown'),
                'start_time': trace_data.get('start_time'),
                'end_time': trace_data.get('end_time'),
                'spans': trace_data.get('spans', [])
            }
        
        # Sort by start time (most recent first) and limit
        sorted_traces = dict(
            sorted(
                filtered_traces.items(),
                key=lambda x: x[1]['start_time'],
                reverse=True
            )[:limit]
        )
        
        return {
            'traces': sorted_traces,
            'total_count': len(filtered_traces),
            'returned_count': len(sorted_traces),
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get distributed traces", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve distributed traces")


@router.get("/circuit-breaker-status")
async def get_circuit_breaker_status(
    service: Optional[str] = Query(None, description="Filter by specific service")
):
    """Get circuit breaker status and health"""
    try:
        microservices_data = metrics_store.get('microservices_metrics', {})
        cb_data = microservices_data.get('circuit_breakers', {})
        
        circuit_breaker_status = {
            'total_circuit_breakers': len(cb_data),
            'open_circuit_breakers': 0,
            'half_open_circuit_breakers': 0,
            'closed_circuit_breakers': 0,
            'circuit_breakers': {}
        }
        
        for key, data in cb_data.items():
            parts = key.split('->')
            if len(parts) >= 2:
                service_name = parts[0]
                dependency = parts[1]
                
                if service and service_name != service:
                    continue
                
                current_state = data.get('current_state', 'UNKNOWN')
                
                circuit_breaker_status['circuit_breakers'][key] = {
                    'service': service_name,
                    'dependency': dependency,
                    'current_state': current_state,
                    'failure_count': data.get('failure_count', 0),
                    'success_count': data.get('success_count', 0),
                    'total_state_changes': data.get('total_state_changes', 0),
                    'last_state_change': data.get('state_history', [])[-1] if data.get('state_history') else None
                }
                
                # Count by state
                if current_state.upper() == 'OPEN':
                    circuit_breaker_status['open_circuit_breakers'] += 1
                elif current_state.upper() == 'HALF_OPEN':
                    circuit_breaker_status['half_open_circuit_breakers'] += 1
                elif current_state.upper() == 'CLOSED':
                    circuit_breaker_status['closed_circuit_breakers'] += 1
        
        return {
            'circuit_breaker_status': circuit_breaker_status,
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get circuit breaker status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve circuit breaker status")
