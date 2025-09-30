"""
Pytest configuration and fixtures.
"""

import asyncio
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_service_spec():
    """Sample service specification for testing."""
    return {
        "name": "test-service",
        "replicas": 2,
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


@pytest.fixture
def sample_simulation_spec():
    """Sample simulation specification for testing."""
    return {
        "name": "test-simulation",
        "description": "Test simulation for unit tests",
        "services": [
            {
                "name": "web-service",
                "replicas": 1,
                "endpoints": [
                    {
                        "path": "/api/data",
                        "method": "GET",
                        "workflow": [
                            {
                                "name": "get_data",
                                "template": "control_flow/return_response",
                                "params": {"status_code": 200, "body": {"data": "test"}},
                            }
                        ],
                    }
                ],
            }
        ],
    }


# Markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "api: mark test as API test")


# Skip integration tests if dependencies are not available
def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle missing dependencies."""
    try:
        import importlib.util

        redis_available = importlib.util.find_spec("redis") is not None
        k8s_available = importlib.util.find_spec("kubernetes") is not None
    except ImportError:
        redis_available = False
        k8s_available = False

    skip_redis = pytest.mark.skip(reason="Redis not available")
    skip_k8s = pytest.mark.skip(reason="Kubernetes client not available")

    for item in items:
        if "redis" in item.keywords and not redis_available:
            item.add_marker(skip_redis)
        if "kubernetes" in item.keywords and not k8s_available:
            item.add_marker(skip_k8s)
