"""
Unit tests for service generator.
"""

import pytest

from gong.core.models import ServiceDefinition, ServiceEndpoint, WorkflowStep
from gong.generator.service_generator import FastAPIServiceGenerator
from gong.templates.base import InMemoryTemplateRegistry


class TestFastAPIServiceGenerator:
    """Test FastAPIServiceGenerator class."""

    @pytest.fixture
    def registry(self):
        """Create a template registry for testing."""
        return InMemoryTemplateRegistry()

    @pytest.fixture
    def generator(self, registry):
        """Create a service generator for testing."""
        return FastAPIServiceGenerator(registry)

    @pytest.fixture
    def simple_service(self):
        """Create a simple service definition for testing."""
        return ServiceDefinition(
            name="test-service",
            endpoints=[
                ServiceEndpoint(
                    path="/health",
                    method="GET",
                    workflow=[
                        WorkflowStep(
                            name="return_health",
                            template="control_flow/return_response",
                            params={"status_code": 200, "body": {"status": "healthy"}},
                        )
                    ],
                )
            ],
        )

    async def test_generate_service_files(self, generator, simple_service):
        """Test generating service files."""
        files = await generator.generate_service(simple_service)

        # Should generate required files
        assert "src/main.py" in files
        assert "requirements.txt" in files
        assert "Dockerfile" in files
        assert "src/config.py" in files

    async def test_main_py_content(self, generator, simple_service):
        """Test main.py content generation."""
        files = await generator.generate_service(simple_service)
        main_py = files["src/main.py"]

        # Should contain FastAPI imports and setup
        assert "from fastapi import FastAPI" in main_py
        assert "app = FastAPI(" in main_py
        assert 'title="test-service"' in main_py

        # Should contain the health endpoint
        assert '@app.get("/health")' in main_py
        assert "async def handle_health(" in main_py

    async def test_requirements_txt_content(self, generator, simple_service):
        """Test requirements.txt content generation."""
        files = await generator.generate_service(simple_service)
        requirements = files["requirements.txt"]

        # Should contain basic dependencies
        assert "fastapi" in requirements
        assert "uvicorn" in requirements
        assert "httpx" in requirements
        assert "opentelemetry" in requirements

    async def test_dockerfile_content(self, generator, simple_service):
        """Test Dockerfile content generation."""
        files = await generator.generate_service(simple_service)
        dockerfile = files["Dockerfile"]

        # Should contain Python base image and setup
        assert "FROM python:" in dockerfile
        assert "COPY requirements.txt" in dockerfile
        assert "RUN pip install" in dockerfile
        assert "CMD [" in dockerfile

    async def test_config_py_content(self, generator, simple_service):
        """Test config.py content generation."""
        files = await generator.generate_service(simple_service)
        config_py = files["src/config.py"]

        # Should contain configuration class
        assert "class Config:" in config_py
        assert "DATABASE_URL" in config_py
        assert "REDIS_URL" in config_py

    async def test_complex_service_generation(self, generator, registry):
        """Test generating a more complex service."""
        service = ServiceDefinition(
            name="order-service",
            replicas=3,
            endpoints=[
                ServiceEndpoint(
                    path="/v1/orders",
                    method="POST",
                    workflow=[
                        WorkflowStep(
                            name="validate_user",
                            template="io/http_api_call",
                            params={
                                "target_service": "user-service",
                                "path": "/v1/users/{body.user_id}",
                                "method": "GET",
                            },
                            output="user_data",
                        ),
                        WorkflowStep(
                            name="create_order",
                            template="io/postgres_write",
                            params={
                                "datastore_name": "orders-db",
                                "query": "INSERT INTO orders (user_id, total) VALUES ($1, $2)",
                                "query_params": ["{body.user_id}", "{body.total}"],
                            },
                        ),
                        WorkflowStep(
                            name="return_success",
                            template="control_flow/return_response",
                            params={"status_code": 201, "body": {"message": "Order created"}},
                        ),
                    ],
                )
            ],
        )

        files = await generator.generate_service(service)
        main_py = files["src/main.py"]

        # Should contain the order endpoint
        assert '@app.post("/v1/orders")' in main_py
        assert "async def handle_v1_orders(" in main_py

        # Should contain HTTP client setup for user service call
        assert "httpx.AsyncClient" in main_py
        assert "user-service" in main_py

    async def test_service_with_dependencies(self, generator):
        """Test service generation with database dependencies."""
        from gong.core.models import DatastoreDependency

        service = ServiceDefinition(
            name="data-service",
            dependencies={
                "services": ["auth-service"],
                "datastores": [DatastoreDependency(name="main-db", type="postgres")],
            },
            endpoints=[
                ServiceEndpoint(
                    path="/data",
                    method="GET",
                    workflow=[
                        WorkflowStep(
                            name="get_data",
                            template="io/postgres_query",
                            params={
                                "datastore_name": "main-db",
                                "query": "SELECT * FROM data WHERE id = $1",
                                "query_params": ["{path.id}"],
                            },
                        )
                    ],
                )
            ],
        )

        files = await generator.generate_service(service)
        requirements = files["requirements.txt"]

        # Should include database dependencies
        assert "asyncpg" in requirements or "sqlalchemy" in requirements
