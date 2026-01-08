"""
Test suite for coverage scoring algorithm
"""

import pytest
from coverage.scoring import CoverageScorer, CoverageLevel, CoverageMetrics


class TestCoverageScorer:
    """Test cases for coverage scoring"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.scorer = CoverageScorer()
    
    def test_perfect_coverage(self):
        """Test application with perfect coverage"""
        app_data = {
            "name": "perfect-app",
            "alerts": [
                {"type": "cpu_usage"},
                {"type": "memory_usage"},
                {"type": "disk_usage"},
                {"type": "response_time"},
                {"type": "error_rate"},
                {"type": "pod_health"}
            ],
            "dashboards": [
                {"type": "infrastructure"},
                {"type": "application_performance"},
                {"type": "error_analysis"},
                {"type": "business_metrics"}
            ],
            "entities": [
                {"type": "application"},
                {"type": "infrastructure"},
                {"type": "kubernetes"},
                {"type": "database"},
                {"type": "external_service"}
            ]
        }
        
        result = self.scorer.calculate_coverage(app_data)
        
        assert result.total_score == 100.0
        assert result.coverage_level == CoverageLevel.EXCELLENT
        assert len(result.missing_alerts) == 0
        assert len(result.missing_dashboards) == 0
        assert len(result.issues) == 0
    
    def test_no_coverage(self):
        """Test application with no coverage"""
        app_data = {
            "name": "no-coverage-app",
            "alerts": [],
            "dashboards": [],
            "entities": []
        }
        
        result = self.scorer.calculate_coverage(app_data)
        
        assert result.total_score == 0.0
        assert result.coverage_level == CoverageLevel.CRITICAL
        assert len(result.missing_alerts) == 6
        assert len(result.missing_dashboards) == 4
        assert len(result.issues) > 0
    
    def test_partial_coverage(self):
        """Test application with partial coverage"""
        app_data = {
            "name": "partial-app",
            "alerts": [
                {"type": "cpu_usage"},
                {"type": "memory_usage"}
            ],
            "dashboards": [
                {"type": "infrastructure"}
            ],
            "entities": [
                {"type": "application"},
                {"type": "infrastructure"}
            ]
        }
        
        result = self.scorer.calculate_coverage(app_data)
        
        assert 0 < result.total_score < 100
        assert len(result.missing_alerts) == 4
        assert len(result.missing_dashboards) == 3
        assert result.coverage_level in [CoverageLevel.POOR, CoverageLevel.FAIR]
    
    def test_coverage_report_generation(self):
        """Test coverage report generation"""
        metrics = [
            CoverageMetrics(
                app_name="app1",
                total_score=95.0,
                coverage_level=CoverageLevel.EXCELLENT,
                alert_coverage=100.0,
                dashboard_coverage=100.0,
                entity_coverage=85.0,
                missing_alerts=[],
                missing_dashboards=[],
                issues=[]
            ),
            CoverageMetrics(
                app_name="app2",
                total_score=45.0,
                coverage_level=CoverageLevel.POOR,
                alert_coverage=50.0,
                dashboard_coverage=40.0,
                entity_coverage=45.0,
                missing_alerts=["cpu_usage", "memory_usage"],
                missing_dashboards=["infrastructure"],
                issues=["Missing entity type: database"]
            )
        ]
        
        report = self.scorer.generate_coverage_report(metrics)
        
        assert report["summary"]["total_applications"] == 2
        assert report["summary"]["average_coverage_score"] == 70.0
        assert len(report["applications"]) == 2
        assert "recommendations" in report
        assert "priority_actions" in report["recommendations"]


if __name__ == "__main__":
    pytest.main([__file__])
