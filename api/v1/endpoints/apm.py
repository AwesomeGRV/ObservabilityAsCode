"""
APM (Application Performance Management) with OpenTelemetry
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
import structlog
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from ...monitoring import metrics_store

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/apm", tags=["apm"])

# Initialize OpenTelemetry
def setup_opentelemetry():
    """Setup OpenTelemetry tracing and metrics"""
    
    # Tracing
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    
    otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)
    
    # Metrics
    metric_reader = PeriodicExportingMetricReader(
        exporter=OTLPMetricExporter(endpoint="http://localhost:4317", insecure=True),
        export_interval_millis=30000,
    )
    
    metrics.set_meter_provider(MeterProvider(metric_readers=[metric_reader]))
    meter = metrics.get_meter(__name__)
    
    # Auto-instrumentation
    FastAPIInstrumentor.instrument()
    SQLAlchemyInstrumentor.instrument()
    RedisInstrumentor.instrument()
    
    return tracer, meter

tracer, meter = setup_opentelemetry()

# Create metrics
request_counter = meter.create_counter(
    "apm_requests_total",
    description="Total number of requests"
)

request_duration = meter.create_histogram(
    "apm_request_duration_seconds",
    description="Request duration in seconds"
)

error_counter = meter.create_counter(
    "apm_errors_total",
    description="Total number of errors"
)

class SpanEvent(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    operation_name: str
    start_time: datetime
    end_time: datetime
    duration: float
    status: str
    tags: Dict[str, Any] = {}
    logs: List[Dict[str, Any]] = []
    service_name: str
    resource_attributes: Dict[str, Any] = {}

class MetricEvent(BaseModel):
    metric_name: str
    metric_type: str  # counter, gauge, histogram
    value: float
    attributes: Dict[str, Any] = {}
    timestamp: Optional[datetime] = None
    unit: Optional[str] = None

class PerformanceProfile(BaseModel):
    service_name: str
    endpoint: str
    method: str
    response_time: float
    cpu_usage: float
    memory_usage: float
    database_queries: int
    cache_hits: int
    cache_misses: int
    error_count: int
    timestamp: Optional[datetime] = None

class ErrorAnalysis(BaseModel):
    error_id: str
    error_type: str
    error_message: str
    stack_trace: str
    service_name: str
    endpoint: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    context: Dict[str, Any] = {}
    timestamp: Optional[datetime] = None

@router.post("/span")
async def create_span(event: SpanEvent):
    """Create and track OpenTelemetry span"""
    try:
        with tracer.start_as_current_span(event.operation_name) as span:
            span.set_attribute("service.name", event.service_name)
            span.set_attribute("span.kind", "server")
            
            for key, value in event.tags.items():
                span.set_attribute(key, str(value))
            
            if event.status == "error":
                span.set_status(trace.Status(trace.StatusCode.ERROR))
            
            for log in event.logs:
                span.add_event(
                    log.get("name", "event"),
                    attributes=log.get("attributes", {}),
                    timestamp=log.get("timestamp")
                )
        
        # Store in metrics store
        if 'spans' not in metrics_store.get('apm_metrics', {}):
            metrics_store.setdefault('apm_metrics', {})['spans'] = []
        
        metrics_store['apm_metrics']['spans'].append({
            'trace_id': event.trace_id,
            'span_id': event.span_id,
            'parent_span_id': event.parent_span_id,
            'operation_name': event.operation_name,
            'duration': event.duration,
            'status': event.status,
            'service_name': event.service_name,
            'timestamp': event.timestamp or datetime.utcnow(),
            'tags': event.tags,
            'logs': event.logs
        })
        
        return {"status": "success", "span_id": event.span_id}
        
    except Exception as e:
        logger.error("Failed to create span", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create span")

@router.post("/metric")
async def record_metric(event: MetricEvent):
    """Record custom metric"""
    try:
        if event.metric_type == "counter":
            counter = meter.create_counter(event.metric_name, description=event.metric_name)
            counter.add(event.value, attributes=event.attributes)
        elif event.metric_type == "gauge":
            gauge = meter.create_up_down_counter(event.metric_name, description=event.metric_name)
            gauge.add(event.value, attributes=event.attributes)
        elif event.metric_type == "histogram":
            histogram = meter.create_histogram(event.metric_name, description=event.metric_name)
            histogram.record(event.value, attributes=event.attributes)
        
        # Store in metrics store
        if 'custom_metrics' not in metrics_store.get('apm_metrics', {}):
            metrics_store.setdefault('apm_metrics', {})['custom_metrics'] = []
        
        metrics_store['apm_metrics']['custom_metrics'].append({
            'metric_name': event.metric_name,
            'metric_type': event.metric_type,
            'value': event.value,
            'attributes': event.attributes,
            'timestamp': event.timestamp or datetime.utcnow(),
            'unit': event.unit
        })
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error("Failed to record metric", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to record metric")

@router.post("/performance-profile")
async def record_performance_profile(profile: PerformanceProfile):
    """Record application performance profile"""
    try:
        # Record metrics
        request_counter.add(1, attributes={
            "service": profile.service_name,
            "endpoint": profile.endpoint,
            "method": profile.method
        })
        
        request_duration.record(profile.response_time, attributes={
            "service": profile.service_name,
            "endpoint": profile.endpoint,
            "method": profile.method
        })
        
        if profile.error_count > 0:
            error_counter.add(profile.error_count, attributes={
                "service": profile.service_name,
                "endpoint": profile.endpoint,
                "method": profile.method
            })
        
        # Store profile
        if 'performance_profiles' not in metrics_store.get('apm_metrics', {}):
            metrics_store.setdefault('apm_metrics', {})['performance_profiles'] = []
        
        metrics_store['apm_metrics']['performance_profiles'].append({
            'service_name': profile.service_name,
            'endpoint': profile.endpoint,
            'method': profile.method,
            'response_time': profile.response_time,
            'cpu_usage': profile.cpu_usage,
            'memory_usage': profile.memory_usage,
            'database_queries': profile.database_queries,
            'cache_hits': profile.cache_hits,
            'cache_misses': profile.cache_misses,
            'error_count': profile.error_count,
            'timestamp': profile.timestamp or datetime.utcnow()
        })
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error("Failed to record performance profile", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to record performance profile")

@router.post("/error-analysis")
async def analyze_error(error: ErrorAnalysis):
    """Analyze and record error"""
    try:
        # Record error metric
        error_counter.add(1, attributes={
            "service": error.service_name,
            "endpoint": error.endpoint,
            "error_type": error.error_type
        })
        
        # Store error analysis
        if 'error_analysis' not in metrics_store.get('apm_metrics', {}):
            metrics_store.setdefault('apm_metrics', {})['error_analysis'] = []
        
        metrics_store['apm_metrics']['error_analysis'].append({
            'error_id': error.error_id,
            'error_type': error.error_type,
            'error_message': error.error_message,
            'stack_trace': error.stack_trace,
            'service_name': error.service_name,
            'endpoint': error.endpoint,
            'user_id': error.user_id,
            'session_id': error.session_id,
            'request_id': error.request_id,
            'context': error.context,
            'timestamp': error.timestamp or datetime.utcnow()
        })
        
        return {"status": "success"}
        
    except Exception as e:
        logger.error("Failed to analyze error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to analyze error")

@router.get("/traces")
async def get_traces(
    service_name: Optional[str] = Query(None),
    hours: int = Query(1),
    limit: int = Query(100)
):
    """Get traces with filtering"""
    try:
        traces = metrics_store.get('apm_metrics', {}).get('spans', [])
        
        # Filter by time
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        filtered_traces = [
            trace for trace in traces
            if trace.get('timestamp', datetime.utcnow()) > cutoff_time
        ]
        
        # Filter by service
        if service_name:
            filtered_traces = [
                trace for trace in filtered_traces
                if trace.get('service_name') == service_name
            ]
        
        # Group by trace_id
        trace_groups = {}
        for trace in filtered_traces:
            trace_id = trace.get('trace_id')
            if trace_id not in trace_groups:
                trace_groups[trace_id] = []
            trace_groups[trace_id].append(trace)
        
        # Sort and limit
        result = []
        for trace_id, spans in trace_groups.items():
            result.append({
                'trace_id': trace_id,
                'spans': spans,
                'duration': max(span['duration'] for span in spans),
                'service_name': spans[0].get('service_name'),
                'status': 'error' if any(span['status'] == 'error' for span in spans) else 'success'
            })
        
        result.sort(key=lambda x: x['duration'], reverse=True)
        
        return {"traces": result[:limit], "total": len(result)}
        
    except Exception as e:
        logger.error("Failed to get traces", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve traces")

@router.get("/performance-summary")
async def get_performance_summary(
    service_name: Optional[str] = Query(None),
    hours: int = Query(24)
):
    """Get performance summary"""
    try:
        profiles = metrics_store.get('apm_metrics', {}).get('performance_profiles', [])
        
        # Filter by time
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        filtered_profiles = [
            profile for profile in profiles
            if profile.get('timestamp', datetime.utcnow()) > cutoff_time
        ]
        
        # Filter by service
        if service_name:
            filtered_profiles = [
                profile for profile in filtered_profiles
                if profile.get('service_name') == service_name
            ]
        
        if not filtered_profiles:
            return {"message": "No data found"}
        
        # Calculate summary
        summary = {
            'total_requests': len(filtered_profiles),
            'avg_response_time': sum(p['response_time'] for p in filtered_profiles) / len(filtered_profiles),
            'p95_response_time': sorted(p['response_time'] for p in filtered_profiles)[int(len(filtered_profiles) * 0.95)],
            'p99_response_time': sorted(p['response_time'] for p in filtered_profiles)[int(len(filtered_profiles) * 0.99)],
            'avg_cpu_usage': sum(p['cpu_usage'] for p in filtered_profiles) / len(filtered_profiles),
            'avg_memory_usage': sum(p['memory_usage'] for p in filtered_profiles) / len(filtered_profiles),
            'total_errors': sum(p['error_count'] for p in filtered_profiles),
            'error_rate': sum(p['error_count'] for p in filtered_profiles) / len(filtered_profiles) * 100,
            'cache_hit_rate': sum(p['cache_hits'] for p in filtered_profiles) / max(sum(p['cache_hits'] + p['cache_misses'] for p in filtered_profiles), 1) * 100
        }
        
        return summary
        
    except Exception as e:
        logger.error("Failed to get performance summary", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve performance summary")
