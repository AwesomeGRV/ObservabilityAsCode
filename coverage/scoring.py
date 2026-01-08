"""
Coverage Scoring Algorithm for Observability as Code
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CoverageLevel(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


@dataclass
class CoverageMetrics:
    """Coverage metrics for an application"""
    app_name: str
    total_score: float
    coverage_level: CoverageLevel
    alert_coverage: float
    dashboard_coverage: float
    entity_coverage: float
    missing_alerts: List[str]
    missing_dashboards: List[str]
    issues: List[str]


class CoverageScorer:
    """Calculates observability coverage scores"""
    
    # Standard alert types that should be present
    STANDARD_ALERTS = [
        "cpu_usage",
        "memory_usage", 
        "disk_usage",
        "response_time",
        "error_rate",
        "pod_health"
    ]
    
    # Standard dashboard types that should be present
    STANDARD_DASHBOARDS = [
        "infrastructure",
        "application_performance",
        "error_analysis",
        "business_metrics"
    ]
    
    # Entity types that should be monitored
    STANDARD_ENTITIES = [
        "application",
        "infrastructure",
        "kubernetes",
        "database",
        "external_service"
    ]
    
    def __init__(self):
        self.weights = {
            "alert_coverage": 0.35,
            "dashboard_coverage": 0.35,
            "entity_coverage": 0.30
        }
    
    def calculate_coverage(self, app_data: Dict) -> CoverageMetrics:
        """Calculate overall coverage score for an application"""
        app_name = app_data.get("name", "unknown")
        
        # Calculate individual coverage scores
        alert_score, missing_alerts = self._calculate_alert_coverage(app_data)
        dashboard_score, missing_dashboards = self._calculate_dashboard_coverage(app_data)
        entity_score, entity_issues = self._calculate_entity_coverage(app_data)
        
        # Calculate weighted total score
        total_score = (
            alert_score * self.weights["alert_coverage"] +
            dashboard_score * self.weights["dashboard_coverage"] +
            entity_score * self.weights["entity_coverage"]
        )
        
        # Determine coverage level
        coverage_level = self._get_coverage_level(total_score)
        
        # Collect all issues
        issues = []
        if missing_alerts:
            issues.append(f"Missing alerts: {', '.join(missing_alerts)}")
        if missing_dashboards:
            issues.append(f"Missing dashboards: {', '.join(missing_dashboards)}")
        issues.extend(entity_issues)
        
        return CoverageMetrics(
            app_name=app_name,
            total_score=round(total_score, 2),
            coverage_level=coverage_level,
            alert_coverage=round(alert_score, 2),
            dashboard_coverage=round(dashboard_score, 2),
            entity_coverage=round(entity_score, 2),
            missing_alerts=missing_alerts,
            missing_dashboards=missing_dashboards,
            issues=issues
        )
    
    def _calculate_alert_coverage(self, app_data: Dict) -> Tuple[float, List[str]]:
        """Calculate alert coverage score"""
        existing_alerts = app_data.get("alerts", [])
        existing_alert_types = [alert.get("type", "").lower() for alert in existing_alerts]
        
        missing_alerts = []
        covered_count = 0
        
        for standard_alert in self.STANDARD_ALERTS:
            if any(standard_alert in alert_type for alert_type in existing_alert_types):
                covered_count += 1
            else:
                missing_alerts.append(standard_alert)
        
        if not self.STANDARD_ALERTS:
            return 0.0, missing_alerts
        
        score = (covered_count / len(self.STANDARD_ALERTS)) * 100
        return score, missing_alerts
    
    def _calculate_dashboard_coverage(self, app_data: Dict) -> Tuple[float, List[str]]:
        """Calculate dashboard coverage score"""
        existing_dashboards = app_data.get("dashboards", [])
        existing_dashboard_types = [dash.get("type", "").lower() for dash in existing_dashboards]
        
        missing_dashboards = []
        covered_count = 0
        
        for standard_dashboard in self.STANDARD_DASHBOARDS:
            if any(standard_dashboard in dash_type for dash_type in existing_dashboard_types):
                covered_count += 1
            else:
                missing_dashboards.append(standard_dashboard)
        
        if not self.STANDARD_DASHBOARDS:
            return 0.0, missing_dashboards
        
        score = (covered_count / len(self.STANDARD_DASHBOARDS)) * 100
        return score, missing_dashboards
    
    def _calculate_entity_coverage(self, app_data: Dict) -> Tuple[float, List[str]]:
        """Calculate entity coverage score"""
        entities = app_data.get("entities", [])
        entity_types = [entity.get("type", "").lower() for entity in entities]
        
        missing_entities = []
        covered_count = 0
        issues = []
        
        for standard_entity in self.STANDARD_ENTITIES:
            if any(standard_entity in entity_type for entity_type in entity_types):
                covered_count += 1
            else:
                missing_entities.append(standard_entity)
                issues.append(f"Missing entity type: {standard_entity}")
        
        # Check for critical issues
        if "application" not in entity_types:
            issues.append("CRITICAL: Application entity not found")
        if not any("infrastructure" in entity_type for entity_type in entity_types):
            issues.append("WARNING: Infrastructure monitoring not found")
        
        if not self.STANDARD_ENTITIES:
            return 0.0, issues
        
        score = (covered_count / len(self.STANDARD_ENTITIES)) * 100
        return score, issues
    
    def _get_coverage_level(self, score: float) -> CoverageLevel:
        """Determine coverage level based on score"""
        if score >= 90:
            return CoverageLevel.EXCELLENT
        elif score >= 75:
            return CoverageLevel.GOOD
        elif score >= 60:
            return CoverageLevel.FAIR
        elif score >= 40:
            return CoverageLevel.POOR
        else:
            return CoverageLevel.CRITICAL
    
    def generate_coverage_report(self, coverage_metrics: List[CoverageMetrics]) -> Dict:
        """Generate a comprehensive coverage report"""
        total_apps = len(coverage_metrics)
        if total_apps == 0:
            return {"error": "No applications to analyze"}
        
        # Calculate summary statistics
        scores = [metric.total_score for metric in coverage_metrics]
        avg_score = sum(scores) / total_apps
        
        # Count coverage levels
        level_counts = {level.value: 0 for level in CoverageLevel}
        for metric in coverage_metrics:
            level_counts[metric.coverage_level.value] += 1
        
        # Find applications needing attention
        critical_apps = [m for m in coverage_metrics if m.coverage_level == CoverageLevel.CRITICAL]
        poor_apps = [m for m in coverage_metrics if m.coverage_level == CoverageLevel.POOR]
        
        # Common missing items
        all_missing_alerts = []
        all_missing_dashboards = []
        for metric in coverage_metrics:
            all_missing_alerts.extend(metric.missing_alerts)
            all_missing_dashboards.extend(metric.missing_dashboards)
        
        common_missing_alerts = self._get_most_common(all_missing_alerts)
        common_missing_dashboards = self._get_most_common(all_missing_dashboards)
        
        return {
            "summary": {
                "total_applications": total_apps,
                "average_coverage_score": round(avg_score, 2),
                "coverage_levels": level_counts,
                "applications_needing_attention": len(critical_apps) + len(poor_apps)
            },
            "applications": [
                {
                    "name": metric.app_name,
                    "score": metric.total_score,
                    "level": metric.coverage_level.value,
                    "alert_coverage": metric.alert_coverage,
                    "dashboard_coverage": metric.dashboard_coverage,
                    "entity_coverage": metric.entity_coverage,
                    "issues": metric.issues
                }
                for metric in coverage_metrics
            ],
            "recommendations": {
                "critical_applications": [app.app_name for app in critical_apps],
                "poor_applications": [app.app_name for app in poor_apps],
                "common_missing_alerts": common_missing_alerts,
                "common_missing_dashboards": common_missing_dashboards,
                "priority_actions": self._generate_priority_actions(coverage_metrics)
            }
        }
    
    def _get_most_common(self, items: List[str]) -> List[str]:
        """Get most common items from a list"""
        from collections import Counter
        if not items:
            return []
        
        counter = Counter(items)
        return [item for item, count in counter.most_common(5)]
    
    def _generate_priority_actions(self, coverage_metrics: List[CoverageMetrics]) -> List[str]:
        """Generate priority actions based on coverage analysis"""
        actions = []
        
        # Check for common patterns
        all_missing_alerts = []
        all_missing_dashboards = []
        
        for metric in coverage_metrics:
            all_missing_alerts.extend(metric.missing_alerts)
            all_missing_dashboards.extend(metric.missing_dashboards)
        
        # Generate specific actions
        if "cpu_usage" in all_missing_alerts:
            actions.append("Implement CPU usage alerts across all applications")
        
        if "memory_usage" in all_missing_alerts:
            actions.append("Implement memory usage alerts across all applications")
        
        if "error_rate" in all_missing_alerts:
            actions.append("Implement error rate alerts for better application health monitoring")
        
        if "infrastructure" in all_missing_dashboards:
            actions.append("Create infrastructure monitoring dashboards")
        
        if "application_performance" in all_missing_dashboards:
            actions.append("Create application performance dashboards")
        
        # Add general recommendations
        critical_count = len([m for m in coverage_metrics if m.coverage_level == CoverageLevel.CRITICAL])
        if critical_count > 0:
            actions.append(f"URGENT: Address critical coverage gaps in {critical_count} applications")
        
        return actions
