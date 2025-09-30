"""
Tests for traffic generator.
"""

import pytest

from gong.traffic.generator import DummyTrafficGenerator


@pytest.fixture
def traffic_generator():
    """Create a traffic generator for testing."""
    return DummyTrafficGenerator()


@pytest.mark.asyncio
async def test_start_constant_traffic(traffic_generator):
    """Test starting constant traffic pattern."""
    pattern = {
        "type": "constant",
        "params": {"users": 10, "duration": "30s", "target_host": "test-service"},
    }

    job_id = await traffic_generator.start_traffic("sim-test", pattern)

    assert job_id is not None
    assert job_id in traffic_generator.active_jobs
    assert traffic_generator.active_jobs[job_id]["status"] == "running"


@pytest.mark.asyncio
async def test_start_ramp_traffic(traffic_generator):
    """Test starting ramp traffic pattern."""
    pattern = {
        "type": "ramp",
        "params": {
            "start_users": 1,
            "end_users": 100,
            "duration": "10m",
            "target_host": "test-service",
        },
    }

    job_id = await traffic_generator.start_traffic("sim-test", pattern)

    assert job_id is not None
    assert traffic_generator.active_jobs[job_id]["pattern"]["type"] == "ramp"


@pytest.mark.asyncio
async def test_start_spike_traffic(traffic_generator):
    """Test starting spike traffic pattern."""
    pattern = {
        "type": "spike",
        "params": {"users": 500, "duration": "5m", "target_host": "test-service"},
    }

    job_id = await traffic_generator.start_traffic("sim-test", pattern)

    assert job_id is not None
    assert traffic_generator.active_jobs[job_id]["pattern"]["type"] == "spike"


@pytest.mark.asyncio
async def test_stop_traffic(traffic_generator):
    """Test stopping traffic generation."""
    pattern = {"type": "constant", "params": {"users": 10, "duration": "30s"}}

    job_id = await traffic_generator.start_traffic("sim-test", pattern)
    await traffic_generator.stop_traffic(job_id)

    assert traffic_generator.active_jobs[job_id]["status"] == "stopped"


@pytest.mark.asyncio
async def test_stop_nonexistent_traffic(traffic_generator):
    """Test stopping non-existent traffic job."""
    # Should not raise an exception
    await traffic_generator.stop_traffic("nonexistent-job-id")
