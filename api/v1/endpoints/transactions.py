"""
End-to-end transaction monitoring for 3-tier architecture (user journey tracking)
"""

import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
import structlog

from ...monitoring import (
    update_transaction_metrics,
    TRANSACTION_DURATION,
    TRANSACTION_SUCCESS_RATE,
    USER_JOURNEY_STEPS,
    BUSINESS_METRICS,
    metrics_store
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/transactions", tags=["transactions"])


class TransactionEvent(BaseModel):
    transaction_id: str
    transaction_type: str  # purchase, login, signup, search, etc.
    user_id: Optional[str] = ""
    session_id: str
    service_flow: str  # frontend->api->database
    duration: float
    status: str  # success, failure, timeout
    steps: List[Dict[str, Any]]  # Individual steps in the transaction
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class UserJourneyStepEvent(BaseModel):
    journey_type: str  # checkout, onboarding, support, etc.
    step_name: str  # add_to_cart, payment_confirmation, etc.
    user_id: Optional[str] = ""
    user_segment: Optional[str] = ""  # premium, free, trial
    session_id: str
    duration: float
    status: str
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class BusinessMetricEvent(BaseModel):
    metric_name: str  # conversion_rate, revenue, user_retention, etc.
    metric_value: float
    product: Optional[str] = ""
    user_segment: Optional[str] = ""
    transaction_id: Optional[str] = ""
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[datetime] = None


class TransactionMetricsResponse(BaseModel):
    transactions: Dict[str, Dict[str, Any]]
    user_journeys: Dict[str, Dict[str, Any]]
    business_metrics: Dict[str, Dict[str, Any]]
    performance_summary: Dict[str, Any]
    last_updated: datetime


@router.post("/transaction")
async def track_transaction(event: TransactionEvent):
    """Track end-to-end transaction metrics"""
    try:
        # Update transaction metrics
        update_transaction_metrics(
            transaction_type=event.transaction_type,
            user_id=event.user_id or "anonymous",
            service_flow=event.service_flow,
            duration=event.duration,
            status=event.status
        )
        
        # Store detailed transaction data
        if 'transactions' not in metrics_store['transaction_metrics']:
            metrics_store['transaction_metrics']['transactions'] = {}
        
        transaction_data = {
            'transaction_id': event.transaction_id,
            'transaction_type': event.transaction_type,
            'user_id': event.user_id,
            'session_id': event.session_id,
            'service_flow': event.service_flow,
            'duration': event.duration,
            'status': event.status,
            'steps': event.steps,
            'metadata': event.metadata or {},
            'timestamp': event.timestamp or datetime.utcnow()
        }
        
        metrics_store['transaction_metrics']['transactions'][event.transaction_id] = transaction_data
        
        logger.info(
            "Transaction tracked",
            transaction_id=event.transaction_id,
            transaction_type=event.transaction_type,
            user_id=event.user_id,
            duration=event.duration,
            status=event.status,
            service_flow=event.service_flow
        )
        
        return {"status": "success", "message": "Transaction tracked"}
        
    except Exception as e:
        logger.error("Failed to track transaction", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track transaction")


@router.post("/user-journey-step")
async def track_user_journey_step(event: UserJourneyStepEvent):
    """Track user journey step completions"""
    try:
        # Update user journey metrics
        USER_JOURNEY_STEPS.labels(
            journey_type=event.journey_type,
            step_name=event.step_name,
            user_segment=event.user_segment or "unknown"
        ).inc()
        
        # Store journey step data
        if 'user_journeys' not in metrics_store['transaction_metrics']:
            metrics_store['transaction_metrics']['user_journeys'] = {}
        
        journey_key = f"{event.journey_type}:{event.user_id}:{event.session_id}"
        if journey_key not in metrics_store['transaction_metrics']['user_journeys']:
            metrics_store['transaction_metrics']['user_journeys'][journey_key] = {
                'journey_type': event.journey_type,
                'user_id': event.user_id,
                'session_id': event.session_id,
                'user_segment': event.user_segment,
                'steps': [],
                'start_time': event.timestamp or datetime.utcnow(),
                'last_updated': event.timestamp or datetime.utcnow()
            }
        
        journey_data = metrics_store['transaction_metrics']['user_journeys'][journey_key]
        step_data = {
            'step_name': event.step_name,
            'duration': event.duration,
            'status': event.status,
            'metadata': event.metadata or {},
            'timestamp': event.timestamp or datetime.utcnow()
        }
        
        journey_data['steps'].append(step_data)
        journey_data['last_updated'] = event.timestamp or datetime.utcnow()
        
        logger.info(
            "User journey step tracked",
            journey_type=event.journey_type,
            step_name=event.step_name,
            user_id=event.user_id,
            user_segment=event.user_segment,
            duration=event.duration,
            status=event.status
        )
        
        return {"status": "success", "message": "User journey step tracked"}
        
    except Exception as e:
        logger.error("Failed to track user journey step", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track user journey step")


@router.post("/business-metric")
async def track_business_metric(event: BusinessMetricEvent):
    """Track business metrics"""
    try:
        # Update business metrics
        BUSINESS_METRICS.labels(
            metric_name=event.metric_name,
            product=event.product or "unknown",
            user_segment=event.user_segment or "unknown"
        ).inc()
        
        # Store business metric data
        if 'business_metrics' not in metrics_store['transaction_metrics']:
            metrics_store['transaction_metrics']['business_metrics'] = {}
        
        metric_key = f"{event.metric_name}:{event.product}:{event.user_segment}"
        if metric_key not in metrics_store['transaction_metrics']['business_metrics']:
            metrics_store['transaction_metrics']['business_metrics'][metric_key] = {
                'metric_name': event.metric_name,
                'product': event.product,
                'user_segment': event.user_segment,
                'values': [],
                'total_value': 0.0,
                'count': 0
            }
        
        metric_data = metrics_store['transaction_metrics']['business_metrics'][metric_key]
        metric_data['values'].append(event.metric_value)
        metric_data['total_value'] += event.metric_value
        metric_data['count'] += 1
        
        logger.info(
            "Business metric tracked",
            metric_name=event.metric_name,
            metric_value=event.metric_value,
            product=event.product,
            user_segment=event.user_segment,
            transaction_id=event.transaction_id
        )
        
        return {"status": "success", "message": "Business metric tracked"}
        
    except Exception as e:
        logger.error("Failed to track business metric", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track business metric")


@router.get("/metrics", response_model=TransactionMetricsResponse)
async def get_transaction_metrics(
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    user_segment: Optional[str] = Query(None, description="Filter by user segment"),
    hours: int = Query(24, description="Hours of data to retrieve")
):
    """Get comprehensive transaction metrics"""
    try:
        transaction_data = metrics_store.get('transaction_metrics', {})
        
        # Transaction metrics
        transactions = {}
        transactions_store = transaction_data.get('transactions', {})
        
        for trans_id, trans_data in transactions_store.items():
            if transaction_type and trans_data.get('transaction_type') != transaction_type:
                continue
            
            transactions[trans_id] = {
                'transaction_type': trans_data.get('transaction_type'),
                'user_id': trans_data.get('user_id'),
                'service_flow': trans_data.get('service_flow'),
                'duration': trans_data.get('duration'),
                'status': trans_data.get('status'),
                'timestamp': trans_data.get('timestamp'),
                'step_count': len(trans_data.get('steps', []))
            }
        
        # User journey metrics
        user_journeys = {}
        journeys_store = transaction_data.get('user_journeys', {})
        
        for journey_key, journey_data in journeys_store.items():
            if user_segment and journey_data.get('user_segment') != user_segment:
                continue
            
            user_journeys[journey_key] = {
                'journey_type': journey_data.get('journey_type'),
                'user_id': journey_data.get('user_id'),
                'user_segment': journey_data.get('user_segment'),
                'step_count': len(journey_data.get('steps', [])),
                'completed_steps': len([s for s in journey_data.get('steps', []) if s.get('status') == 'success']),
                'start_time': journey_data.get('start_time'),
                'last_updated': journey_data.get('last_updated'),
                'total_duration': sum(s.get('duration', 0) for s in journey_data.get('steps', []))
            }
        
        # Business metrics
        business_metrics = {}
        business_store = transaction_data.get('business_metrics', {})
        
        for metric_key, metric_data in business_store.items():
            parts = metric_key.split(':')
            metric_name = parts[0] if parts else 'unknown'
            product = parts[1] if len(parts) > 1 else 'unknown'
            segment = parts[2] if len(parts) > 2 else 'unknown'
            
            if user_segment and segment != user_segment:
                continue
            
            values = metric_data.get('values', [])
            business_metrics[metric_key] = {
                'metric_name': metric_name,
                'product': product,
                'user_segment': segment,
                'count': metric_data.get('count', 0),
                'total_value': metric_data.get('total_value', 0),
                'average_value': metric_data.get('total_value', 0) / max(metric_data.get('count', 1), 1),
                'latest_value': values[-1] if values else 0,
                'min_value': min(values) if values else 0,
                'max_value': max(values) if values else 0
            }
        
        # Performance summary
        performance_summary = {
            'total_transactions': len(transactions),
            'successful_transactions': len([t for t in transactions.values() if t.get('status') == 'success']),
            'failed_transactions': len([t for t in transactions.values() if t.get('status') == 'failed']),
            'average_transaction_duration': 0,
            'total_user_journeys': len(user_journeys),
            'completed_journeys': len([j for j in user_journeys.values() if j.get('completed_steps') == j.get('step_count')]),
            'business_metrics_count': len(business_metrics)
        }
        
        # Calculate average transaction duration
        if transactions:
            total_duration = sum(t.get('duration', 0) for t in transactions.values())
            performance_summary['average_transaction_duration'] = total_duration / len(transactions)
        
        return TransactionMetricsResponse(
            transactions=transactions,
            user_journeys=user_journeys,
            business_metrics=business_metrics,
            performance_summary=performance_summary,
            last_updated=metrics_store['last_updated']
        )
        
    except Exception as e:
        logger.error("Failed to get transaction metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve transaction metrics")


@router.get("/performance-analysis")
async def get_performance_analysis(
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type"),
    hours: int = Query(24, description="Hours of data to analyze")
):
    """Get detailed performance analysis for transactions"""
    try:
        transaction_data = metrics_store.get('transaction_metrics', {})
        transactions_store = transaction_data.get('transactions', {})
        
        # Filter transactions by time window
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        filtered_transactions = {}
        
        for trans_id, trans_data in transactions_store.items():
            trans_time = trans_data.get('timestamp', datetime.utcnow())
            if trans_time > cutoff_time:
                if transaction_type and trans_data.get('transaction_type') != transaction_type:
                    continue
                filtered_transactions[trans_id] = trans_data
        
        # Performance analysis
        analysis = {
            'transaction_count': len(filtered_transactions),
            'success_rate': 0,
            'average_duration': 0,
            'duration_percentiles': {},
            'transaction_types': {},
            'service_flows': {},
            'error_patterns': {},
            'performance_trends': []
        }
        
        if filtered_transactions:
            # Calculate success rate
            successful = len([t for t in filtered_transactions.values() if t.get('status') == 'success'])
            analysis['success_rate'] = (successful / len(filtered_transactions)) * 100
            
            # Calculate duration metrics
            durations = [t.get('duration', 0) for t in filtered_transactions.values()]
            analysis['average_duration'] = sum(durations) / len(durations)
            
            # Calculate percentiles
            sorted_durations = sorted(durations)
            n = len(sorted_durations)
            analysis['duration_percentiles'] = {
                'p50': sorted_durations[int(n * 0.5)],
                'p75': sorted_durations[int(n * 0.75)],
                'p90': sorted_durations[int(n * 0.90)],
                'p95': sorted_durations[int(n * 0.95)],
                'p99': sorted_durations[int(n * 0.99)]
            }
            
            # Analyze by transaction type
            for trans_data in filtered_transactions.values():
                trans_type = trans_data.get('transaction_type', 'unknown')
                if trans_type not in analysis['transaction_types']:
                    analysis['transaction_types'][trans_type] = {
                        'count': 0,
                        'success_count': 0,
                        'total_duration': 0
                    }
                
                analysis['transaction_types'][trans_type]['count'] += 1
                analysis['transaction_types'][trans_type]['total_duration'] += trans_data.get('duration', 0)
                
                if trans_data.get('status') == 'success':
                    analysis['transaction_types'][trans_type]['success_count'] += 1
            
            # Calculate success rates by transaction type
            for trans_type, data in analysis['transaction_types'].items():
                data['success_rate'] = (data['success_count'] / data['count']) * 100
                data['average_duration'] = data['total_duration'] / data['count']
            
            # Analyze by service flow
            for trans_data in filtered_transactions.values():
                flow = trans_data.get('service_flow', 'unknown')
                if flow not in analysis['service_flows']:
                    analysis['service_flows'][flow] = {
                        'count': 0,
                        'success_count': 0,
                        'total_duration': 0
                    }
                
                analysis['service_flows'][flow]['count'] += 1
                analysis['service_flows'][flow]['total_duration'] += trans_data.get('duration', 0)
                
                if trans_data.get('status') == 'success':
                    analysis['service_flows'][flow]['success_count'] += 1
            
            # Calculate success rates by service flow
            for flow, data in analysis['service_flows'].items():
                data['success_rate'] = (data['success_count'] / data['count']) * 100
                data['average_duration'] = data['total_duration'] / data['count']
            
            # Analyze error patterns
            failed_transactions = [t for t in filtered_transactions.values() if t.get('status') != 'success']
            for trans_data in failed_transactions:
                error_type = trans_data.get('metadata', {}).get('error_type', 'unknown')
                if error_type not in analysis['error_patterns']:
                    analysis['error_patterns'][error_type] = 0
                analysis['error_patterns'][error_type] += 1
        
        return {
            'performance_analysis': analysis,
            'analysis_period_hours': hours,
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get performance analysis", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve performance analysis")


@router.get("/user-journey-analysis")
async def get_user_journey_analysis(
    journey_type: Optional[str] = Query(None, description="Filter by journey type"),
    user_segment: Optional[str] = Query(None, description="Filter by user segment"),
    hours: int = Query(24, description="Hours of data to analyze")
):
    """Get user journey analysis and funnel metrics"""
    try:
        transaction_data = metrics_store.get('transaction_metrics', {})
        journeys_store = transaction_data.get('user_journeys', {})
        
        # Filter journeys by time window
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        filtered_journeys = {}
        
        for journey_key, journey_data in journeys_store.items():
            journey_time = journey_data.get('last_updated', datetime.utcnow())
            if journey_time > cutoff_time:
                if journey_type and journey_data.get('journey_type') != journey_type:
                    continue
                if user_segment and journey_data.get('user_segment') != user_segment:
                    continue
                filtered_journeys[journey_key] = journey_data
        
        # Journey analysis
        analysis = {
            'total_journeys': len(filtered_journeys),
            'completed_journeys': 0,
            'abandoned_journeys': 0,
            'completion_rate': 0,
            'journey_types': {},
            'step_completion_rates': {},
            'average_journey_duration': 0,
            'funnel_analysis': {}
        }
        
        total_duration = 0
        step_counts = {}
        
        for journey_data in filtered_journeys.values():
            steps = journey_data.get('steps', [])
            completed_steps = len([s for s in steps if s.get('status') == 'success'])
            total_steps = len(steps)
            
            if completed_steps == total_steps and total_steps > 0:
                analysis['completed_journeys'] += 1
            else:
                analysis['abandoned_journeys'] += 1
            
            total_duration += journey_data.get('total_duration', 0)
            
            # Analyze by journey type
            j_type = journey_data.get('journey_type', 'unknown')
            if j_type not in analysis['journey_types']:
                analysis['journey_types'][j_type] = {
                    'total': 0,
                    'completed': 0,
                    'total_duration': 0
                }
            
            analysis['journey_types'][j_type]['total'] += 1
            analysis['journey_types'][j_type]['total_duration'] += journey_data.get('total_duration', 0)
            
            if completed_steps == total_steps and total_steps > 0:
                analysis['journey_types'][j_type]['completed'] += 1
            
            # Track step completion
            for step in steps:
                step_name = step.get('step_name', 'unknown')
                if step_name not in step_counts:
                    step_counts[step_name] = {'total': 0, 'completed': 0}
                
                step_counts[step_name]['total'] += 1
                if step.get('status') == 'success':
                    step_counts[step_name]['completed'] += 1
        
        # Calculate completion rates
        if analysis['total_journeys'] > 0:
            analysis['completion_rate'] = (analysis['completed_journeys'] / analysis['total_journeys']) * 100
            analysis['average_journey_duration'] = total_duration / analysis['total_journeys']
        
        # Calculate step completion rates
        for step_name, counts in step_counts.items():
            analysis['step_completion_rates'][step_name] = {
                'total_attempts': counts['total'],
                'successful_completions': counts['completed'],
                'completion_rate': (counts['completed'] / counts['total']) * 100 if counts['total'] > 0 else 0
            }
        
        # Calculate completion rates by journey type
        for j_type, data in analysis['journey_types'].items():
            data['completion_rate'] = (data['completed'] / data['total']) * 100 if data['total'] > 0 else 0
            data['average_duration'] = data['total_duration'] / data['total'] if data['total'] > 0 else 0
        
        # Funnel analysis (for common journey types)
        if journey_type or 'checkout' in [j.get('journey_type', '') for j in filtered_journeys.values()]:
            funnel_steps = {}
            
            for journey_data in filtered_journeys.values():
                if journey_type and journey_data.get('journey_type') != journey_type:
                    continue
                
                steps = journey_data.get('steps', [])
                for i, step in enumerate(steps):
                    step_name = step.get('step_name', f'step_{i}')
                    if step_name not in funnel_steps:
                        funnel_steps[step_name] = {'reached': 0, 'completed': 0}
                    
                    funnel_steps[step_name]['reached'] += 1
                    if step.get('status') == 'success':
                        funnel_steps[step_name]['completed'] += 1
            
            # Calculate funnel conversion rates
            for step_name, counts in funnel_steps.items():
                analysis['funnel_analysis'][step_name] = {
                    'users_reached': counts['reached'],
                    'users_completed': counts['completed'],
                    'conversion_rate': (counts['completed'] / counts['reached']) * 100 if counts['reached'] > 0 else 0
                }
        
        return {
            'journey_analysis': analysis,
            'analysis_period_hours': hours,
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get user journey analysis", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve user journey analysis")


@router.get("/business-metrics")
async def get_business_metrics(
    metric_name: Optional[str] = Query(None, description="Filter by metric name"),
    product: Optional[str] = Query(None, description="Filter by product"),
    user_segment: Optional[str] = Query(None, description="Filter by user segment"),
    hours: int = Query(24, description="Hours of data to retrieve")
):
    """Get business metrics with filtering options"""
    try:
        transaction_data = metrics_store.get('transaction_metrics', {})
        business_store = transaction_data.get('business_metrics', {})
        
        filtered_metrics = {}
        
        for metric_key, metric_data in business_store.items():
            parts = metric_key.split(':')
            m_name = parts[0] if parts else 'unknown'
            m_product = parts[1] if len(parts) > 1 else 'unknown'
            m_segment = parts[2] if len(parts) > 2 else 'unknown'
            
            if metric_name and m_name != metric_name:
                continue
            if product and m_product != product:
                continue
            if user_segment and m_segment != user_segment:
                continue
            
            values = metric_data.get('values', [])
            # Filter by time window if timestamps were stored
            # For now, return all values
            
            filtered_metrics[metric_key] = {
                'metric_name': m_name,
                'product': m_product,
                'user_segment': m_segment,
                'values': values,
                'count': len(values),
                'total_value': sum(values),
                'average_value': sum(values) / len(values) if values else 0,
                'latest_value': values[-1] if values else 0,
                'min_value': min(values) if values else 0,
                'max_value': max(values) if values else 0
            }
        
        # Aggregate metrics by name
        metrics_by_name = {}
        for metric_key, data in filtered_metrics.items():
            m_name = data['metric_name']
            if m_name not in metrics_by_name:
                metrics_by_name[m_name] = {
                    'total_count': 0,
                    'total_value': 0,
                    'products': {},
                    'user_segments': {}
                }
            
            metrics_by_name[m_name]['total_count'] += data['count']
            metrics_by_name[m_name]['total_value'] += data['total_value']
            
            product = data['product']
            if product not in metrics_by_name[m_name]['products']:
                metrics_by_name[m_name]['products'][product] = {'count': 0, 'total_value': 0}
            metrics_by_name[m_name]['products'][product]['count'] += data['count']
            metrics_by_name[m_name]['products'][product]['total_value'] += data['total_value']
            
            segment = data['user_segment']
            if segment not in metrics_by_name[m_name]['user_segments']:
                metrics_by_name[m_name]['user_segments'][segment] = {'count': 0, 'total_value': 0}
            metrics_by_name[m_name]['user_segments'][segment]['count'] += data['count']
            metrics_by_name[m_name]['user_segments'][segment]['total_value'] += data['total_value']
        
        # Calculate averages for aggregated metrics
        for m_name, data in metrics_by_name.items():
            data['average_value'] = data['total_value'] / data['total_count'] if data['total_count'] > 0 else 0
            
            for product, p_data in data['products'].items():
                p_data['average_value'] = p_data['total_value'] / p_data['count'] if p_data['count'] > 0 else 0
            
            for segment, s_data in data['user_segments'].items():
                s_data['average_value'] = s_data['total_value'] / s_data['count'] if s_data['count'] > 0 else 0
        
        return {
            'business_metrics': filtered_metrics,
            'metrics_by_name': metrics_by_name,
            'total_metrics': len(filtered_metrics),
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get business metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve business metrics")
