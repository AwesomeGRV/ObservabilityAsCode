"""
Integration tests for the main API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data


class TestApplicationEndpoints:
    """Test application management endpoints"""
    
    def test_create_application(self, client: TestClient, auth_headers):
        """Test creating a new application"""
        app_data = {
            "name": "New Test Application",
            "environment": "development",
            "entity_id": "new-entity-456",
            "description": "A new test application",
            "team": "test-team"
        }
        
        response = client.post("/applications", json=app_data, headers=auth_headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == app_data["name"]
        assert data["environment"] == app_data["environment"]
        assert data["entity_id"] == app_data["entity_id"]
        assert "id" in data
        assert "created_at" in data
    
    def test_get_applications(self, client: TestClient, sample_application, auth_headers):
        """Test getting list of applications"""
        response = client.get("/applications", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "applications" in data
        assert "pagination" in data
        assert len(data["applications"]) >= 1
    
    def test_get_application_by_id(self, client: TestClient, sample_application, auth_headers):
        """Test getting application by ID"""
        response = client.get(f"/applications/{sample_application.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == sample_application.id
        assert data["name"] == sample_application.name
    
    def test_get_nonexistent_application(self, client: TestClient, auth_headers):
        """Test getting non-existent application"""
        response = client.get("/applications/nonexistent", headers=auth_headers)
        assert response.status_code == 404
    
    def test_update_application(self, client: TestClient, sample_application, auth_headers):
        """Test updating an application"""
        update_data = {
            "name": "Updated Application Name",
            "description": "Updated description"
        }
        
        response = client.put(
            f"/applications/{sample_application.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
    
    def test_delete_application(self, client: TestClient, sample_application, auth_headers):
        """Test deleting an application"""
        response = client.delete(f"/applications/{sample_application.id}", headers=auth_headers)
        assert response.status_code == 204
        
        # Verify deletion
        response = client.get(f"/applications/{sample_application.id}", headers=auth_headers)
        assert response.status_code == 404


class TestAlertEndpoints:
    """Test alert management endpoints"""
    
    def test_create_alert(self, client: TestClient, sample_application, auth_headers):
        """Test creating a new alert"""
        alert_data = {
            "name": "Memory Usage Alert",
            "type": "memory_usage",
            "nrql_query": "SELECT average(memoryUsedPercent) FROM SystemSample",
            "thresholds": {"critical": 85, "warning": 70},
            "severity": "warning"
        }
        
        response = client.post(
            f"/applications/{sample_application.id}/alerts",
            json=alert_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == alert_data["name"]
        assert data["type"] == alert_data["type"]
        assert data["application_id"] == sample_application.id
    
    def test_get_application_alerts(self, client: TestClient, sample_alert, auth_headers):
        """Test getting alerts for an application"""
        response = client.get(
            f"/applications/{sample_alert.application_id}/alerts",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "alerts" in data
        assert len(data["alerts"]) >= 1
    
    def test_update_alert(self, client: TestClient, sample_alert, auth_headers):
        """Test updating an alert"""
        update_data = {
            "name": "Updated Alert Name",
            "thresholds": {"critical": 90, "warning": 75}
        }
        
        response = client.put(
            f"/alerts/{sample_alert.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["thresholds"] == update_data["thresholds"]
    
    def test_delete_alert(self, client: TestClient, sample_alert, auth_headers):
        """Test deleting an alert"""
        response = client.delete(f"/alerts/{sample_alert.id}", headers=auth_headers)
        assert response.status_code == 204


class TestDashboardEndpoints:
    """Test dashboard management endpoints"""
    
    def test_create_dashboard(self, client: TestClient, sample_application, auth_headers):
        """Test creating a new dashboard"""
        dashboard_data = {
            "name": "Performance Dashboard",
            "type": "application_performance",
            "description": "Application performance metrics",
            "widgets": [
                {
                    "title": "Response Time",
                    "visualization": "line_chart",
                    "nrql": "SELECT average(duration) FROM Transaction"
                }
            ]
        }
        
        response = client.post(
            f"/applications/{sample_application.id}/dashboards",
            json=dashboard_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        
        data = response.json()
        assert data["name"] == dashboard_data["name"]
        assert data["type"] == dashboard_data["type"]
        assert data["application_id"] == sample_application.id
    
    def test_get_application_dashboards(self, client: TestClient, sample_dashboard, auth_headers):
        """Test getting dashboards for an application"""
        response = client.get(
            f"/applications/{sample_dashboard.application_id}/dashboards",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "dashboards" in data
        assert len(data["dashboards"]) >= 1


class TestCoverageEndpoints:
    """Test coverage reporting endpoints"""
    
    def test_get_coverage_report(self, client: TestClient, sample_application, auth_headers):
        """Test getting coverage report"""
        response = client.get("/coverage", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "overall_coverage" in data
        assert "applications" in data
        assert "generated_at" in data
    
    def test_get_coverage_for_application(self, client: TestClient, sample_application, auth_headers):
        """Test getting coverage for specific application"""
        response = client.get(
            f"/coverage?application_id={sample_application.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "overall_coverage" in data
        assert len(data["applications"]) == 1


class TestComplianceEndpoints:
    """Test compliance checking endpoints"""
    
    def test_get_compliance_status(self, client: TestClient, sample_application, auth_headers):
        """Test getting compliance status"""
        response = client.get("/compliance", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "overall_compliance" in data
        assert "applications" in data
        assert "standards" in data
    
    def test_get_compliance_for_application(self, client: TestClient, sample_application, auth_headers):
        """Test getting compliance for specific application"""
        response = client.get(
            f"/compliance?application_id={sample_application.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "overall_compliance" in data
        assert len(data["applications"]) == 1


class TestDeploymentEndpoints:
    """Test deployment endpoints"""
    
    def test_create_deployment(self, client: TestClient, sample_application, auth_headers):
        """Test creating a deployment"""
        deployment_data = {
            "application_ids": [sample_application.id],
            "dry_run": True,
            "components": ["alerts", "dashboards"]
        }
        
        response = client.post("/deploy", json=deployment_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "deployment_id" in data
        assert "status" in data
        assert "applications" in data
    
    def test_get_deployment_status(self, client: TestClient, auth_headers):
        """Test getting deployment status"""
        # First create a deployment
        deployment_data = {
            "application_ids": ["test-app"],
            "dry_run": True
        }
        create_response = client.post("/deploy", json=deployment_data, headers=auth_headers)
        deployment_id = create_response.json()["deployment_id"]
        
        # Then get its status
        response = client.get(f"/deployments/{deployment_id}", headers=auth_headers)
        assert response.status_code == 200


class TestAuthentication:
    """Test authentication and authorization"""
    
    def test_unauthorized_access(self, client: TestClient):
        """Test access without authentication"""
        response = client.get("/applications")
        assert response.status_code == 401
    
    def test_invalid_api_key(self, client: TestClient):
        """Test access with invalid API key"""
        headers = {"Authorization": "Bearer invalid-key"}
        response = client.get("/applications", headers=headers)
        assert response.status_code == 401
    
    def test_valid_api_key(self, client: TestClient, auth_headers):
        """Test access with valid API key"""
        response = client.get("/applications", headers=auth_headers)
        assert response.status_code == 200


class TestErrorHandling:
    """Test error handling"""
    
    def test_validation_error(self, client: TestClient, auth_headers):
        """Test validation error handling"""
        invalid_data = {
            "name": "",  # Empty name should fail validation
            "environment": "invalid_env",  # Invalid environment
            "entity_id": ""
        }
        
        response = client.post("/applications", json=invalid_data, headers=auth_headers)
        assert response.status_code == 422
        
        data = response.json()
        assert "error" in data
        assert "details" in data
    
    def test_not_found_error(self, client: TestClient, auth_headers):
        """Test 404 error handling"""
        response = client.get("/applications/nonexistent-id", headers=auth_headers)
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
        assert "message" in data
