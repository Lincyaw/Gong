"""
Integration tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from gong.api.main import app


class TestAPIIntegration:
    """Test API integration scenarios."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_health_endpoint(self, client):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "timestamp" in data

    def test_list_templates_endpoint(self, client):
        """Test list templates endpoint."""
        response = client.get("/api/v1/templates")
        assert response.status_code == 200

        templates = response.json()
        assert isinstance(templates, list)
        assert len(templates) > 0
        assert "io/http_api_call" in templates

    def test_generate_config_endpoint(self, client):
        """Test generate config endpoint."""
        response = client.post("/api/v1/generate", json={"prompt": "Create a simple web service"})
        assert response.status_code == 200

        data = response.json()
        assert "generated_spec" in data

        spec = data["generated_spec"]
        assert "name" in spec
        assert "services" in spec

    def test_create_simulation_endpoint(self, client):
        """Test create simulation endpoint."""
        simulation_spec = {
            "name": "test-simulation",
            "description": "Test simulation",
            "services": [
                {
                    "name": "test-service",
                    "replicas": 1,
                    "endpoints": [
                        {
                            "path": "/health",
                            "method": "GET",
                            "workflow": [
                                {
                                    "name": "return_health",
                                    "template": "control_flow/return_response",
                                    "params": {"status_code": 200, "body": {"status": "healthy"}},
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        response = client.post("/api/v1/simulations", json=simulation_spec)
        assert response.status_code == 200

        data = response.json()
        assert "simulation_id" in data
        assert "status" in data

        simulation_id = data["simulation_id"]

        # Test get simulation
        response = client.get(f"/api/v1/simulations/{simulation_id}")
        assert response.status_code == 200

        sim_data = response.json()
        assert sim_data["name"] == "test-simulation"
        assert sim_data["status"] in ["PENDING", "BUILDING", "DEPLOYING", "RUNNING"]

    def test_simulation_not_found(self, client):
        """Test getting non-existent simulation."""
        response = client.get("/api/v1/simulations/nonexistent-id")
        assert response.status_code == 404

    def test_list_simulations_endpoint(self, client):
        """Test list simulations endpoint."""
        response = client.get("/api/v1/simulations")
        assert response.status_code == 200

        simulations = response.json()
        assert isinstance(simulations, list)

    def test_invalid_simulation_spec(self, client):
        """Test creating simulation with invalid spec."""
        invalid_spec = {
            "name": "",  # Invalid: empty name
            "services": [],
        }

        response = client.post("/api/v1/simulations", json=invalid_spec)
        assert response.status_code == 422  # Validation error

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/api/v1/templates")
        assert response.status_code == 200

        # Should have CORS headers in actual implementation
        # This is a placeholder test

    def test_api_documentation(self, client):
        """Test API documentation endpoints."""
        # Test OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

        # Test Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
