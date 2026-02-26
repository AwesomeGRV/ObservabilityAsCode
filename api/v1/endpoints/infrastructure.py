"""
Infrastructure monitoring endpoints for 3-tier architecture (Kubernetes, containers, nodes)
"""

import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel
import structlog

from ...monitoring import (
    update_container_metrics,
    CONTAINER_CPU_USAGE,
    CONTAINER_MEMORY_USAGE,
    CONTAINER_NETWORK_IO,
    POD_RESTART_COUNT,
    NODE_RESOURCE_USAGE,
    metrics_store
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/infrastructure", tags=["infrastructure"])


class ContainerMetricsEvent(BaseModel):
    container_name: str
    pod_name: str
    namespace: str
    cpu_usage: float  # percentage
    memory_usage: float  # bytes
    network_io: Dict[str, int]  # {'in': bytes, 'out': bytes}
    timestamp: Optional[datetime] = None


class PodRestartEvent(BaseModel):
    pod_name: str
    namespace: str
    container_name: str
    restart_count: int
    reason: Optional[str] = ""
    timestamp: Optional[datetime] = None


class NodeMetricsEvent(BaseModel):
    node_name: str
    cpu_usage: float  # percentage
    memory_usage: float  # percentage
    disk_usage: float  # percentage
    network_usage: float  # percentage
    pod_count: int
    timestamp: Optional[datetime] = None


class InfrastructureMetricsResponse(BaseModel):
    containers: Dict[str, Dict[str, Any]]
    pods: Dict[str, Dict[str, Any]]
    nodes: Dict[str, Dict[str, Any]]
    cluster_summary: Dict[str, Any]
    last_updated: datetime


@router.post("/container-metrics")
async def track_container_metrics(event: ContainerMetricsEvent):
    """Track container resource usage metrics"""
    try:
        # Update container metrics
        update_container_metrics(
            container_name=event.container_name,
            pod_name=event.pod_name,
            namespace=event.namespace,
            cpu_usage=event.cpu_usage,
            memory_usage=event.memory_usage,
            network_io=event.network_io
        )
        
        logger.info(
            "Container metrics tracked",
            container=event.container_name,
            pod=event.pod_name,
            namespace=event.namespace,
            cpu_usage=event.cpu_usage,
            memory_usage=event.memory_usage
        )
        
        return {"status": "success", "message": "Container metrics tracked"}
        
    except Exception as e:
        logger.error("Failed to track container metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track container metrics")


@router.post("/pod-restart")
async def track_pod_restart(event: PodRestartEvent):
    """Track pod restart events"""
    try:
        # Update pod restart metrics
        POD_RESTART_COUNT.labels(
            pod_name=event.pod_name,
            namespace=event.namespace,
            container_name=event.container_name
        ).inc()
        
        # Store in memory for analysis
        if 'pod_restarts' not in metrics_store['container_metrics']:
            metrics_store['container_metrics']['pod_restarts'] = {}
        
        key = f"{event.namespace}/{event.pod_name}/{event.container_name}"
        if key not in metrics_store['container_metrics']['pod_restarts']:
            metrics_store['container_metrics']['pod_restarts'][key] = {
                'restart_count': 0,
                'restarts': []
            }
        
        pod_data = metrics_store['container_metrics']['pod_restarts'][key]
        pod_data['restart_count'] += 1
        pod_data['restarts'].append({
            'timestamp': event.timestamp or datetime.utcnow(),
            'reason': event.reason or ""
        })
        
        logger.warning(
            "Pod restart tracked",
            pod=event.pod_name,
            namespace=event.namespace,
            container=event.container_name,
            restart_count=pod_data['restart_count'],
            reason=event.reason
        )
        
        return {"status": "success", "message": "Pod restart tracked"}
        
    except Exception as e:
        logger.error("Failed to track pod restart", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track pod restart")


@router.post("/node-metrics")
async def track_node_metrics(event: NodeMetricsEvent):
    """Track node resource usage metrics"""
    try:
        # Update node metrics for different resource types
        NODE_RESOURCE_USAGE.labels(
            node_name=event.node_name,
            resource_type='cpu'
        ).set(event.cpu_usage)
        
        NODE_RESOURCE_USAGE.labels(
            node_name=event.node_name,
            resource_type='memory'
        ).set(event.memory_usage)
        
        NODE_RESOURCE_USAGE.labels(
            node_name=event.node_name,
            resource_type='disk'
        ).set(event.disk_usage)
        
        NODE_RESOURCE_USAGE.labels(
            node_name=event.node_name,
            resource_type='network'
        ).set(event.network_usage)
        
        # Store in memory for analysis
        if 'node_metrics' not in metrics_store['container_metrics']:
            metrics_store['container_metrics']['node_metrics'] = {}
        
        if event.node_name not in metrics_store['container_metrics']['node_metrics']:
            metrics_store['container_metrics']['node_metrics'][event.node_name] = {
                'cpu_usage': [],
                'memory_usage': [],
                'disk_usage': [],
                'network_usage': [],
                'pod_counts': [],
                'last_updated': datetime.utcnow()
            }
        
        node_data = metrics_store['container_metrics']['node_metrics'][event.node_name]
        node_data['cpu_usage'].append(event.cpu_usage)
        node_data['memory_usage'].append(event.memory_usage)
        node_data['disk_usage'].append(event.disk_usage)
        node_data['network_usage'].append(event.network_usage)
        node_data['pod_counts'].append(event.pod_count)
        node_data['last_updated'] = datetime.utcnow()
        
        logger.info(
            "Node metrics tracked",
            node=event.node_name,
            cpu_usage=event.cpu_usage,
            memory_usage=event.memory_usage,
            pod_count=event.pod_count
        )
        
        return {"status": "success", "message": "Node metrics tracked"}
        
    except Exception as e:
        logger.error("Failed to track node metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to track node metrics")


@router.get("/metrics", response_model=InfrastructureMetricsResponse)
async def get_infrastructure_metrics(
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
    node: Optional[str] = Query(None, description="Filter by node"),
    hours: int = Query(24, description="Hours of data to retrieve")
):
    """Get comprehensive infrastructure metrics"""
    try:
        container_data = metrics_store.get('container_metrics', {})
        
        # Container metrics
        containers = {}
        for key, data in container_data.items():
            if key in ['pod_restarts', 'node_metrics']:
                continue
                
            parts = key.split('/')
            if len(parts) >= 3:
                ns = parts[0]
                pod = parts[1]
                container = parts[2]
                
                if namespace and ns != namespace:
                    continue
                
                cpu_usage = data.get('cpu_usage', [])
                memory_usage = data.get('memory_usage', [])
                
                containers[key] = {
                    'namespace': ns,
                    'pod': pod,
                    'container': container,
                    'current_cpu_usage': cpu_usage[-1] if cpu_usage else 0,
                    'average_cpu_usage': sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0,
                    'current_memory_usage': memory_usage[-1] if memory_usage else 0,
                    'average_memory_usage': sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                    'network_io': data.get('network_io', {}),
                    'last_updated': data.get('last_updated')
                }
        
        # Pod metrics (restarts)
        pods = {}
        pod_restarts = container_data.get('pod_restarts', {})
        for key, data in pod_restarts.items():
            parts = key.split('/')
            if len(parts) >= 3:
                ns = parts[0]
                pod = parts[1]
                container = parts[2]
                
                if namespace and ns != namespace:
                    continue
                
                pods[key] = {
                    'namespace': ns,
                    'pod': pod,
                    'container': container,
                    'restart_count': data.get('restart_count', 0),
                    'recent_restarts': data.get('restarts', [])[-5:],  # Last 5 restarts
                    'last_restart': data.get('restarts', [])[-1] if data.get('restarts') else None
                }
        
        # Node metrics
        nodes = {}
        node_metrics = container_data.get('node_metrics', {})
        for node_name, data in node_metrics.items():
            if node and node_name != node:
                continue
                
            cpu_usage = data.get('cpu_usage', [])
            memory_usage = data.get('memory_usage', [])
            disk_usage = data.get('disk_usage', [])
            network_usage = data.get('network_usage', [])
            pod_counts = data.get('pod_counts', [])
            
            nodes[node_name] = {
                'current_cpu_usage': cpu_usage[-1] if cpu_usage else 0,
                'average_cpu_usage': sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0,
                'current_memory_usage': memory_usage[-1] if memory_usage else 0,
                'average_memory_usage': sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                'current_disk_usage': disk_usage[-1] if disk_usage else 0,
                'average_disk_usage': sum(disk_usage) / len(disk_usage) if disk_usage else 0,
                'current_network_usage': network_usage[-1] if network_usage else 0,
                'average_network_usage': sum(network_usage) / len(network_usage) if network_usage else 0,
                'current_pod_count': pod_counts[-1] if pod_counts else 0,
                'average_pod_count': sum(pod_counts) / len(pod_counts) if pod_counts else 0,
                'last_updated': data.get('last_updated')
            }
        
        # Cluster summary
        cluster_summary = {
            'total_containers': len(containers),
            'total_pods': len(pods),
            'total_nodes': len(nodes),
            'pods_with_restarts': len([p for p in pods.values() if p['restart_count'] > 0]),
            'high_cpu_nodes': len([n for n in nodes.values() if n['current_cpu_usage'] > 80]),
            'high_memory_nodes': len([n for n in nodes.values() if n['current_memory_usage'] > 80])
        }
        
        return InfrastructureMetricsResponse(
            containers=containers,
            pods=pods,
            nodes=nodes,
            cluster_summary=cluster_summary,
            last_updated=metrics_store['last_updated']
        )
        
    except Exception as e:
        logger.error("Failed to get infrastructure metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve infrastructure metrics")


@router.get("/cluster-health")
async def get_cluster_health():
    """Get overall cluster health status"""
    try:
        container_data = metrics_store.get('container_metrics', {})
        
        # Calculate cluster health metrics
        total_containers = 0
        healthy_containers = 0
        total_nodes = 0
        healthy_nodes = 0
        
        # Analyze container health
        for key, data in container_data.items():
            if key in ['pod_restarts', 'node_metrics']:
                continue
                
            total_containers += 1
            cpu_usage = data.get('cpu_usage', [])
            memory_usage = data.get('memory_usage', [])
            
            # Consider container healthy if CPU < 90% and Memory < 90%
            current_cpu = cpu_usage[-1] if cpu_usage else 0
            current_memory = memory_usage[-1] if memory_usage else 0
            
            if current_cpu < 90 and current_memory < 90:
                healthy_containers += 1
        
        # Analyze node health
        node_metrics = container_data.get('node_metrics', {})
        for node_name, data in node_metrics.items():
            total_nodes += 1
            cpu_usage = data.get('cpu_usage', [])
            memory_usage = data.get('memory_usage', [])
            
            current_cpu = cpu_usage[-1] if cpu_usage else 0
            current_memory = memory_usage[-1] if memory_usage else 0
            
            if current_cpu < 85 and current_memory < 85:
                healthy_nodes += 1
        
        # Calculate restart metrics
        total_restarts = 0
        pods_with_restarts = 0
        pod_restarts = container_data.get('pod_restarts', {})
        
        for data in pod_restarts.values():
            restart_count = data.get('restart_count', 0)
            if restart_count > 0:
                pods_with_restarts += 1
                total_restarts += restart_count
        
        # Determine overall health
        container_health_rate = (healthy_containers / max(total_containers, 1)) * 100
        node_health_rate = (healthy_nodes / max(total_nodes, 1)) * 100
        
        overall_status = "healthy"
        if container_health_rate < 80 or node_health_rate < 80:
            overall_status = "critical"
        elif container_health_rate < 90 or node_health_rate < 90:
            overall_status = "warning"
        
        return {
            'overall_status': overall_status,
            'container_health': {
                'total': total_containers,
                'healthy': healthy_containers,
                'health_rate_percent': round(container_health_rate, 2)
            },
            'node_health': {
                'total': total_nodes,
                'healthy': healthy_nodes,
                'health_rate_percent': round(node_health_rate, 2)
            },
            'restart_metrics': {
                'total_restarts': total_restarts,
                'pods_with_restarts': pods_with_restarts
            },
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get cluster health", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve cluster health")


@router.get("/resource-usage")
async def get_resource_usage(
    resource_type: Optional[str] = Query(None, description="Filter by resource type: cpu, memory, disk, network"),
    hours: int = Query(24, description="Hours of data to retrieve")
):
    """Get resource usage trends and analysis"""
    try:
        container_data = metrics_store.get('container_metrics', {})
        
        resource_trends = {
            'cpu': [],
            'memory': [],
            'disk': [],
            'network': []
        }
        
        # Container resource trends
        for key, data in container_data.items():
            if key in ['pod_restarts', 'node_metrics']:
                continue
                
            parts = key.split('/')
            if len(parts) >= 3:
                container_name = parts[2]
                
                if not resource_type or resource_type == 'cpu':
                    cpu_usage = data.get('cpu_usage', [])
                    if cpu_usage:
                        resource_trends['cpu'].append({
                            'container': container_name,
                            'current': cpu_usage[-1],
                            'average': sum(cpu_usage) / len(cpu_usage),
                            'max': max(cpu_usage),
                            'min': min(cpu_usage)
                        })
                
                if not resource_type or resource_type == 'memory':
                    memory_usage = data.get('memory_usage', [])
                    if memory_usage:
                        resource_trends['memory'].append({
                            'container': container_name,
                            'current': memory_usage[-1],
                            'average': sum(memory_usage) / len(memory_usage),
                            'max': max(memory_usage),
                            'min': min(memory_usage)
                        })
        
        # Node resource trends
        node_metrics = container_data.get('node_metrics', {})
        for node_name, data in node_metrics.items():
            if not resource_type or resource_type == 'cpu':
                cpu_usage = data.get('cpu_usage', [])
                if cpu_usage:
                    resource_trends['cpu'].append({
                        'node': node_name,
                        'current': cpu_usage[-1],
                        'average': sum(cpu_usage) / len(cpu_usage),
                        'max': max(cpu_usage),
                        'min': min(cpu_usage)
                    })
            
            if not resource_type or resource_type == 'memory':
                memory_usage = data.get('memory_usage', [])
                if memory_usage:
                    resource_trends['memory'].append({
                        'node': node_name,
                        'current': memory_usage[-1],
                        'average': sum(memory_usage) / len(memory_usage),
                        'max': max(memory_usage),
                        'min': min(memory_usage)
                    })
            
            if not resource_type or resource_type == 'disk':
                disk_usage = data.get('disk_usage', [])
                if disk_usage:
                    resource_trends['disk'].append({
                        'node': node_name,
                        'current': disk_usage[-1],
                        'average': sum(disk_usage) / len(disk_usage),
                        'max': max(disk_usage),
                        'min': min(disk_usage)
                    })
            
            if not resource_type or resource_type == 'network':
                network_usage = data.get('network_usage', [])
                if network_usage:
                    resource_trends['network'].append({
                        'node': node_name,
                        'current': network_usage[-1],
                        'average': sum(network_usage) / len(network_usage),
                        'max': max(network_usage),
                        'min': min(network_usage)
                    })
        
        # Sort by current usage (highest first)
        for resource_type in resource_trends:
            resource_trends[resource_type].sort(key=lambda x: x['current'], reverse=True)
        
        return {
            'resource_trends': resource_trends,
            'analysis_period_hours': hours,
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get resource usage", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve resource usage")


@router.get("/pod-restarts")
async def get_pod_restarts(
    namespace: Optional[str] = Query(None, description="Filter by namespace"),
    hours: int = Query(24, description="Hours of data to retrieve")
):
    """Get pod restart information and analysis"""
    try:
        container_data = metrics_store.get('container_metrics', {})
        pod_restarts = container_data.get('pod_restarts', {})
        
        restart_analysis = []
        
        for key, data in pod_restarts.items():
            parts = key.split('/')
            if len(parts) >= 3:
                ns = parts[0]
                pod = parts[1]
                container = parts[2]
                
                if namespace and ns != namespace:
                    continue
                
                restart_count = data.get('restart_count', 0)
                recent_restarts = data.get('restarts', [])
                
                # Filter restarts by time window
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                recent_restarts_filtered = [
                    r for r in recent_restarts 
                    if r['timestamp'] > cutoff_time
                ]
                
                if restart_count > 0:
                    restart_analysis.append({
                        'namespace': ns,
                        'pod': pod,
                        'container': container,
                        'total_restart_count': restart_count,
                        'recent_restart_count': len(recent_restarts_filtered),
                        'last_restart': recent_restarts[-1] if recent_restarts else None,
                        'restart_frequency': len(recent_restarts_filtered) / max(hours, 1),  # restarts per hour
                        'common_reasons': list(set(r['reason'] for r in recent_restarts_filtered if r['reason']))
                    })
        
        # Sort by recent restart count (highest first)
        restart_analysis.sort(key=lambda x: x['recent_restart_count'], reverse=True)
        
        return {
            'pod_restarts': restart_analysis,
            'total_pods_with_restarts': len(restart_analysis),
            'analysis_period_hours': hours,
            'last_updated': metrics_store['last_updated']
        }
        
    except Exception as e:
        logger.error("Failed to get pod restarts", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve pod restarts")
